#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "raw_event_broker.h"
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#endif
#include <windows.h>
#else
#include <errno.h>
#include <pthread.h>
#include <time.h>
#endif

typedef struct rb_slot { size_t bytes; uint8_t data[RB_RESPONSE_MAX]; } rb_slot;
typedef struct rb_request { uint64_t id; int used, waiting, cancelled; } rb_request;
struct rb_broker {
#ifdef _WIN32
    SRWLOCK lock;
    CONDITION_VARIABLE changed;
#else
    pthread_mutex_t lock;
    pthread_cond_t changed;
#endif
    rb_slot queue[RB_CAPACITY];
    rb_request requests[RB_REQUESTS];
    rb_health health;
    uint64_t session, generation, source_scope, next_sequence, next_ticket;
    uint32_t origin, head;
};

static void lock_b(rb_broker *b) {
#ifdef _WIN32
    AcquireSRWLockExclusive(&b->lock);
#else
    (void)pthread_mutex_lock(&b->lock);
#endif
}
static void unlock_b(rb_broker *b) {
#ifdef _WIN32
    ReleaseSRWLockExclusive(&b->lock);
#else
    (void)pthread_mutex_unlock(&b->lock);
#endif
}
static void wake_all(rb_broker *b) {
#ifdef _WIN32
    WakeAllConditionVariable(&b->changed);
#else
    (void)pthread_cond_broadcast(&b->changed);
#endif
}
static uint64_t now_ms(void) {
#ifdef _WIN32
    return GetTickCount64();
#else
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0) return UINT64_MAX;
    return (uint64_t)t.tv_sec * 1000u + (uint64_t)t.tv_nsec / 1000000u;
#endif
}
/* Returns zero for wake OR deadline; caller rechecks all state under the lock. */
static int wait_until(rb_broker *b, uint64_t deadline) {
#ifdef _WIN32
    uint64_t now = now_ms();
    DWORD remaining = (DWORD)(deadline > now ? deadline - now : 0);
    if (SleepConditionVariableSRW(&b->changed, &b->lock, remaining, 0)) return 0;
    return GetLastError() == ERROR_TIMEOUT ? 0 : -1;
#else
    struct timespec end;
    int status;
    end.tv_sec = (time_t)(deadline / 1000u);
    end.tv_nsec = (long)((deadline % 1000u) * 1000000u);
    status = pthread_cond_timedwait(&b->changed, &b->lock, &end);
    return status == 0 || status == ETIMEDOUT ? 0 : -1;
#endif
}
static void add_count(uint64_t *value, uint64_t n) {
    *value = UINT64_MAX - *value < n ? UINT64_MAX : *value + n;
}
static void put32(uint8_t *p, uint32_t value) {
    unsigned i;
    for (i = 0; i < 4; ++i) p[i] = (uint8_t)(value >> (i * 8));
}
static void put64(uint8_t *p, uint64_t value) {
    unsigned i;
    for (i = 0; i < 8; ++i) p[i] = (uint8_t)(value >> (i * 8));
}
static rb_request *find_request(rb_broker *b, uint64_t id) {
    unsigned i;
    for (i = 0; i < RB_REQUESTS; ++i)
        if (b->requests[i].used && b->requests[i].id == id) return &b->requests[i];
    return NULL;
}
static void retire(rb_broker *b, rb_request *r) {
    memset(r, 0, sizeof(*r));
    --b->health.pending_requests;
}
static void close_locked(rb_broker *b, uint32_t reason) {
    unsigned i;
    if (b->health.closed) return;
    b->health.closed = 1;
    b->health.close_reason = reason;
    add_count(&b->health.dropped_close, b->health.queued);
    memset(b->queue, 0, sizeof(b->queue));
    b->health.queued = 0;
    b->head = 0;
    for (i = 0; i < RB_REQUESTS; ++i)
        if (b->requests[i].used && !b->requests[i].waiting) retire(b, &b->requests[i]);
    wake_all(b);
}

rb_broker *rb_create(uint64_t session, uint64_t generation,
    uint64_t source_scope, uint32_t origin) {
    rb_broker *b;
    if (!session || !generation || !source_scope ||
        (origin != RB_FIXTURE && origin != RB_REPLAY_UNQUALIFIED)) return NULL;
    b = (rb_broker *)calloc(1, sizeof(*b));
    if (!b) return NULL;
#ifdef _WIN32
    InitializeSRWLock(&b->lock);
    InitializeConditionVariable(&b->changed);
#else
    {
        pthread_condattr_t attr;
        int status;
        if (pthread_mutex_init(&b->lock, NULL) != 0) { free(b); return NULL; }
        if (pthread_condattr_init(&attr) != 0) {
            (void)pthread_mutex_destroy(&b->lock); free(b); return NULL;
        }
        status = pthread_condattr_setclock(&attr, CLOCK_MONOTONIC);
        if (status == 0) status = pthread_cond_init(&b->changed, &attr);
        (void)pthread_condattr_destroy(&attr);
        if (status != 0) { (void)pthread_mutex_destroy(&b->lock); free(b); return NULL; }
    }
#endif
    b->session = session; b->generation = generation; b->source_scope = source_scope;
    b->origin = origin;
    return b;
}

enum rb_status rb_publish(rb_broker *b, uint64_t generation, const void *source,
    size_t capacity, size_t offset, size_t received, uint32_t copy_point) {
    rb_slot *slot;
    enum rb_status status = RB_OK;
    if (!b) return RB_INVALID;
    lock_b(b);
    if (b->health.closed) status = RB_CLOSED;
    else if (generation != b->generation) status = RB_STALE;
    else if (!source || !received || received > RB_PAYLOAD_MAX || offset > capacity ||
             received > capacity - offset ||
             (b->origin == RB_FIXTURE && copy_point != RB_SIMULATED_POINT_A && copy_point != RB_SIMULATED_POINT_B) ||
             (b->origin == RB_REPLAY_UNQUALIFIED && copy_point != RB_REPLAY_POINT_UNKNOWN)) status = RB_INVALID;
    else if (b->next_sequence == UINT64_MAX) status = RB_LIMIT;
    if (status != RB_OK) {
        add_count(&b->health.rejected, 1); unlock_b(b); return status;
    }
    ++b->next_sequence; /* Overflow drops consume an ordinal: gaps stay visible. */
    if (b->health.queued == RB_CAPACITY) {
        add_count(&b->health.dropped_full, 1); unlock_b(b); return RB_FULL;
    }
    slot = &b->queue[(b->head + b->health.queued) % RB_CAPACITY];
    memset(slot, 0, sizeof(*slot));
    slot->bytes = RB_HEADER_BYTES + received;
    memcpy(slot->data, "WHTR", 4);
    slot->data[4] = 1; slot->data[6] = RB_HEADER_BYTES;
    put32(slot->data + 8, (uint32_t)slot->bytes);
    put32(slot->data + 12, (uint32_t)received);
    put32(slot->data + 16, b->origin);
    /* +20 capabilities stays zero: no timing or live-source qualification. */
    put64(slot->data + 24, b->session);
    put64(slot->data + 32, b->generation);
    put64(slot->data + 40, b->source_scope);
    put64(slot->data + 48, b->next_sequence);
    put64(slot->data + 56, b->health.dropped_full);
    put64(slot->data + 64, b->health.rejected);
    put32(slot->data + 72, copy_point);
    memcpy(slot->data + RB_HEADER_BYTES, (const uint8_t *)source + offset, received);
    ++b->health.queued; /* Publication only after header AND payload are complete. */
    add_count(&b->health.published, 1);
    wake_all(b);
    unlock_b(b);
    return RB_OK;
}

enum rb_status rb_begin_read(rb_broker *b, uint64_t *ticket) {
    unsigned i;
    if (!b || !ticket) return RB_INVALID;
    *ticket = 0;
    lock_b(b);
    if (b->health.closed) { unlock_b(b); return RB_CLOSED; }
    if (b->next_ticket == UINT64_MAX) { unlock_b(b); return RB_LIMIT; }
    for (i = 0; i < RB_REQUESTS; ++i) {
        if (!b->requests[i].used) {
            rb_request *r = &b->requests[i];
            memset(r, 0, sizeof(*r));
            r->used = 1; r->id = ++b->next_ticket;
            *ticket = r->id; ++b->health.pending_requests;
            unlock_b(b); return RB_OK;
        }
    }
    unlock_b(b); return RB_BUSY;
}

enum rb_status rb_read(rb_broker *b, uint64_t ticket, void *output, size_t capacity,
    uint32_t timeout_ms, size_t *written, size_t *required) {
    rb_request *r;
    rb_slot *slot;
    enum rb_status status;
    uint64_t deadline, current;
    if (!written || !required || written == required) return RB_INVALID;
    *written = 0; *required = 0;
    if (!b || !ticket || !output || timeout_ms > RB_TIMEOUT_MAX_MS) return RB_INVALID;
    current = now_ms();
    if (current == UINT64_MAX || current > UINT64_MAX - timeout_ms) return RB_INTERNAL;
    deadline = current + timeout_ms;
    lock_b(b);
    r = find_request(b, ticket);
    if (!r) { status = b->health.closed ? RB_CLOSED : RB_NOT_FOUND; unlock_b(b); return status; }
    if (r->waiting) { unlock_b(b); return RB_BUSY; }
    r->waiting = 1; ++b->health.active_reads;
    for (;;) {
        if (r->cancelled) { status = RB_CANCELLED; add_count(&b->health.cancellations, 1); break; }
        if (b->health.closed) { status = RB_CLOSED; break; }
        current = now_ms();
        if (current == UINT64_MAX) { status = RB_INTERNAL; break; }
        if (timeout_ms && current >= deadline) { status = RB_TIMEOUT; add_count(&b->health.timeouts, 1); break; }
        if (b->health.queued) {
            slot = &b->queue[b->head];
            *required = slot->bytes;
            if (capacity < slot->bytes) { status = RB_SMALL_BUFFER; break; }
            memcpy(output, slot->data, slot->bytes);
            put64((uint8_t *)output + 80, ticket); /* Application response association. */
            *written = slot->bytes;
            memset(slot, 0, sizeof(*slot));
            b->head = (b->head + 1) % RB_CAPACITY; --b->health.queued;
            add_count(&b->health.delivered, 1); status = RB_OK; break;
        }
        if (!timeout_ms) { status = RB_EMPTY; break; }
        if (wait_until(b, deadline) != 0) { status = RB_INTERNAL; break; }
    }
    --b->health.active_reads; retire(b, r);
    unlock_b(b);
    return status;
}

enum rb_status rb_cancel(rb_broker *b, uint64_t ticket) {
    rb_request *r;
    if (!b || !ticket) return RB_INVALID;
    lock_b(b);
    if (b->health.closed) { unlock_b(b); return RB_CLOSED; }
    r = find_request(b, ticket);
    if (!r) { unlock_b(b); return RB_NOT_FOUND; }
    r->cancelled = 1; wake_all(b);
    unlock_b(b); return RB_OK;
}
enum rb_status rb_release_read(rb_broker *b, uint64_t ticket) {
    rb_request *r;
    if (!b || !ticket) return RB_INVALID;
    lock_b(b);
    r = find_request(b, ticket);
    if (!r) { unlock_b(b); return RB_NOT_FOUND; }
    if (r->waiting) { unlock_b(b); return RB_BUSY; }
    retire(b, r); unlock_b(b); return RB_OK;
}
enum rb_status rb_get_health(rb_broker *b, rb_health *out) {
    if (!b || !out) return RB_INVALID;
    lock_b(b); *out = b->health; unlock_b(b); return RB_OK;
}
enum rb_status rb_close(rb_broker *b) {
    if (!b) return RB_INVALID;
    lock_b(b); close_locked(b, RB_OWNER_CLOSE); unlock_b(b); return RB_OK;
}
enum rb_status rb_invalidate(rb_broker *b, uint64_t source_losses, uint32_t reason) {
    if (!b || (reason != RB_SOURCE_LOSS && reason != RB_CONTINUITY_UNKNOWN)) return RB_INVALID;
    lock_b(b);
    if (b->health.closed) { unlock_b(b); return RB_CLOSED; }
    add_count(&b->health.source_losses_reported, source_losses);
    close_locked(b, reason); unlock_b(b); return RB_OK;
}
enum rb_status rb_destroy(rb_broker **owner) {
    rb_broker *b;
    if (!owner || !*owner) return RB_INVALID;
    b = *owner; lock_b(b);
    if (!b->health.closed || b->health.active_reads || b->health.pending_requests) {
        unlock_b(b); return RB_BUSY;
    }
    unlock_b(b);
#ifndef _WIN32
    (void)pthread_cond_destroy(&b->changed);
    (void)pthread_mutex_destroy(&b->lock);
#endif
    memset(b, 0, sizeof(*b)); free(b); *owner = NULL; return RB_OK;
}
