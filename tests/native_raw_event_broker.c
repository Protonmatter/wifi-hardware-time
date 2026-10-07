#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "../research/export_contract/raw_event_broker.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#endif
#include <windows.h>
#else
#include <pthread.h>
#include <time.h>
#endif

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "CHECK failed line %d: %s\n", __LINE__, #x); abort(); } } while (0)
#define EVENTS 1200u
typedef struct thread {
#ifdef _WIN32
    HANDLE handle;
#else
    pthread_t handle;
#endif
    void (*fn)(void *); void *arg;
} thread;
#ifdef _WIN32
static DWORD WINAPI entry(LPVOID p) { thread *t = (thread *)p; t->fn(t->arg); return 0; }
#else
static void *entry(void *p) { thread *t = (thread *)p; t->fn(t->arg); return NULL; }
#endif
static void start(thread *t, void (*fn)(void *), void *arg) {
    t->fn = fn; t->arg = arg;
#ifdef _WIN32
    t->handle = CreateThread(NULL, 0, entry, t, 0, NULL); CHECK(t->handle != NULL);
#else
    CHECK(pthread_create(&t->handle, NULL, entry, t) == 0);
#endif
}
static void join(thread *t) {
#ifdef _WIN32
    CHECK(WaitForSingleObject(t->handle, 10000) == WAIT_OBJECT_0); CHECK(CloseHandle(t->handle));
#else
    CHECK(pthread_join(t->handle, NULL) == 0);
#endif
}
static void pause_ms(void) {
#ifdef _WIN32
    Sleep(1);
#else
    struct timespec t = {0, 1000000}; (void)nanosleep(&t, NULL);
#endif
}
static uint64_t get64(const uint8_t *p) {
    uint64_t value = 0; unsigned i;
    for (i = 0; i < 8; ++i) value |= (uint64_t)p[i] << (i * 8);
    return value;
}
static uint32_t get32(const uint8_t *p) {
    uint32_t value = 0; unsigned i;
    for (i = 0; i < 4; ++i) value |= (uint32_t)p[i] << (i * 8);
    return value;
}
static rb_broker *make(void) { rb_broker *b = rb_create(11, 7, 9, RB_FIXTURE); CHECK(b); return b; }
static void cleanup(rb_broker **b) { CHECK(rb_close(*b) == RB_OK); CHECK(rb_destroy(b) == RB_OK); CHECK(!*b); }
static enum rb_status read_one(rb_broker *b, uint8_t *out, size_t cap, uint32_t timeout,
    size_t *written, size_t *required) {
    uint64_t id; enum rb_status status = rb_begin_read(b, &id);
    if (status != RB_OK) return status;
    return rb_read(b, id, out, cap, timeout, written, required);
}
static void wait_readers(rb_broker *b, uint32_t n) {
    unsigned i; rb_health health;
    for (i = 0; i < 3000; ++i) {
        CHECK(rb_get_health(b, &health) == RB_OK);
        if (health.active_reads == n) return;
        pause_ms();
    }
    CHECK(0);
}
typedef struct read_job {
    rb_broker *b; uint64_t ticket; enum rb_status result;
    uint8_t out[RB_RESPONSE_MAX]; size_t written, required;
} read_job;
static void blocking_read(void *p) {
    read_job *j = (read_job *)p;
    j->result = rb_read(j->b, j->ticket, j->out, sizeof(j->out), 5000, &j->written, &j->required);
}

static void basics(void) {
    rb_broker *b = make(); uint8_t source[10], out[RB_RESPONSE_MAX];
    size_t written, required; rb_health health; uint64_t ticket;
    memset(source, 0x7a, sizeof(source)); memset(out, 0xcc, sizeof(out));
    CHECK(rb_publish(b, 6, source, 10, 2, 6, RB_SIMULATED_POINT_A) == RB_STALE);
    CHECK(rb_publish(b, 7, source, 10, SIZE_MAX, 6, RB_SIMULATED_POINT_A) == RB_INVALID);
    CHECK(rb_publish(b, 7, source, 10, 6, 5, RB_SIMULATED_POINT_A) == RB_INVALID);
    CHECK(rb_publish(b, 7, source, 10, 2, 6, RB_REPLAY_POINT_UNKNOWN) == RB_INVALID);
    CHECK(rb_publish(b, 7, source, 10, 2, 6, RB_SIMULATED_POINT_A) == RB_OK);
    memset(source, 0, sizeof(source));
    CHECK(read_one(b, out, RB_HEADER_BYTES + 5, 0, &written, &required) == RB_SMALL_BUFFER);
    CHECK(!written && required == RB_HEADER_BYTES + 6 && out[0] == 0xcc);
    CHECK(rb_get_health(b, &health) == RB_OK && health.queued == 1);
    CHECK(rb_begin_read(b, &ticket) == RB_OK);
    CHECK(rb_read(b, ticket, out, sizeof(out), 0, &written, &required) == RB_OK);
    CHECK(written == RB_HEADER_BYTES + 6 && required == written);
    CHECK(memcmp(out, "WHTR", 4) == 0 && out[4] == 1 && out[5] == 0 && out[6] == 96 && out[7] == 0);
    CHECK(get32(out + 8) == written && get32(out + 12) == 6 && get32(out + 20) == 0);
    CHECK(get64(out + 24) == 11 && get64(out + 32) == 7 && get64(out + 40) == 9);
    CHECK(get64(out + 48) == 1 && get64(out + 64) == 4 && get64(out + 80) == ticket);
    CHECK(get32(out + 76) == 0 && get64(out + 88) == 0);
    CHECK(out[96] == 0x7a && out[101] == 0x7a);
    CHECK(rb_cancel(b, ticket) == RB_NOT_FOUND);
    CHECK(read_one(b, out, sizeof(out), 0, &written, &required) == RB_EMPTY && !written);
    CHECK(read_one(b, out, sizeof(out), 15, &written, &required) == RB_TIMEOUT && !written);
    CHECK(rb_get_health(b, &health) == RB_OK && health.timeouts == 1);
    CHECK(rb_destroy(&b) == RB_BUSY && b);
    cleanup(&b);
}
static void pressure_and_invalidation(void) {
    rb_broker *b = make(); unsigned i; uint64_t tickets[RB_REQUESTS], extra;
    uint8_t value = 42, out[RB_RESPONSE_MAX]; size_t written, required; rb_health h;
    for (i = 0; i < RB_REQUESTS; ++i) CHECK(rb_begin_read(b, &tickets[i]) == RB_OK);
    CHECK(rb_begin_read(b, &extra) == RB_BUSY && !extra);
    for (i = 0; i < RB_REQUESTS; ++i) CHECK(rb_release_read(b, tickets[i]) == RB_OK);
    for (i = 0; i < RB_CAPACITY; ++i) CHECK(rb_publish(b, 7, &value, 1, 0, 1, RB_SIMULATED_POINT_A) == RB_OK);
    CHECK(rb_publish(b, 7, &value, 1, 0, 1, RB_SIMULATED_POINT_A) == RB_FULL);
    for (i = 0; i < RB_CAPACITY; ++i) CHECK(read_one(b, out, sizeof(out), 0, &written, &required) == RB_OK);
    CHECK(rb_publish(b, 7, &value, 1, 0, 1, RB_SIMULATED_POINT_B) == RB_OK);
    CHECK(read_one(b, out, sizeof(out), 0, &written, &required) == RB_OK);
    CHECK(get64(out + 48) == RB_CAPACITY + 2 && get64(out + 56) == 1);
    for (i = 0; i < 3; ++i) CHECK(rb_publish(b, 7, &value, 1, 0, 1, RB_SIMULATED_POINT_A) == RB_OK);
    CHECK(rb_begin_read(b, &extra) == RB_OK);
    CHECK(rb_invalidate(b, 5, RB_SOURCE_LOSS) == RB_OK);
    CHECK(rb_invalidate(b, 5, RB_SOURCE_LOSS) == RB_CLOSED);
    CHECK(rb_close(b) == RB_OK);
    CHECK(rb_get_health(b, &h) == RB_OK && h.source_losses_reported == 5 && h.dropped_close == 3);
    CHECK(h.close_reason == RB_SOURCE_LOSS && !h.pending_requests && !h.queued);
    CHECK(h.published == h.delivered + h.dropped_close);
    CHECK(rb_publish(b, 7, &value, 1, 0, 1, RB_SIMULATED_POINT_A) == RB_CLOSED);
    CHECK(rb_read(b, extra, out, sizeof(out), 0, &written, &required) == RB_CLOSED);
    CHECK(rb_cancel(b, extra) == RB_CLOSED);
    cleanup(&b);
}
static void cancellation_and_close(void) {
    rb_broker *b = make(); read_job j = {0}; thread t;
    uint8_t value = 8, out[RB_RESPONSE_MAX]; size_t written, required;
    j.b = b; CHECK(rb_begin_read(b, &j.ticket) == RB_OK);
    CHECK(rb_cancel(b, j.ticket) == RB_OK);
    CHECK(rb_publish(b, 7, &value, 1, 0, 1, RB_SIMULATED_POINT_A) == RB_OK);
    blocking_read(&j); CHECK(j.result == RB_CANCELLED && !j.written);
    CHECK(read_one(b, out, sizeof(out), 0, &written, &required) == RB_OK);
    CHECK(rb_begin_read(b, &j.ticket) == RB_OK); start(&t, blocking_read, &j); wait_readers(b, 1);
    CHECK(rb_release_read(b, j.ticket) == RB_BUSY);
    CHECK(rb_read(b, j.ticket, out, sizeof(out), 0, &written, &required) == RB_BUSY);
    CHECK(rb_cancel(b, j.ticket) == RB_OK); join(&t); CHECK(j.result == RB_CANCELLED);
    CHECK(rb_begin_read(b, &j.ticket) == RB_OK); start(&t, blocking_read, &j); wait_readers(b, 1);
    CHECK(rb_close(b) == RB_OK); join(&t); CHECK(j.result == RB_CLOSED && !j.written);
    cleanup(&b);
}
typedef struct race_job { rb_broker *b; uint64_t ticket; enum rb_status status; } race_job;
static void race_cancel(void *p) { race_job *j = (race_job *)p; j->status = rb_cancel(j->b, j->ticket); }
static void race_publish(void *p) {
    race_job *j = (race_job *)p; uint8_t value = 99;
    j->status = rb_publish(j->b, 7, &value, 1, 0, 1, RB_SIMULATED_POINT_A);
}
static void race_close(void *p) { race_job *j = (race_job *)p; j->status = rb_close(j->b); }
static void cancellation_races(void) {
    unsigned i;
    for (i = 0; i < 80; ++i) {
        rb_broker *b = make(); read_job r = {0}; race_job c = {0}, p = {0}; thread rt, ct, pt;
        uint8_t out[RB_RESPONSE_MAX]; size_t written, required;
        r.b = b; CHECK(rb_begin_read(b, &r.ticket) == RB_OK);
        c.b = b; c.ticket = r.ticket; p.b = b;
        start(&rt, blocking_read, &r); wait_readers(b, 1);
        start(&pt, race_publish, &p); start(&ct, race_cancel, &c);
        join(&pt); join(&ct); join(&rt); CHECK(p.status == RB_OK);
        if (r.result == RB_OK) CHECK(c.status == RB_NOT_FOUND);
        else {
            CHECK(r.result == RB_CANCELLED && c.status == RB_OK);
            CHECK(read_one(b, out, sizeof(out), 0, &written, &required) == RB_OK && out[96] == 99);
        }
        cleanup(&b);
    }
}
static void close_publication_races(void) {
    unsigned i;
    for (i = 0; i < 40; ++i) {
        rb_broker *b = make(); read_job r = {0}; race_job p = {0}, close = {0};
        thread rt, pt, ct; rb_health h;
        r.b = b; p.b = b; close.b = b;
        CHECK(rb_begin_read(b, &r.ticket) == RB_OK);
        start(&rt, blocking_read, &r); wait_readers(b, 1);
        start(&pt, race_publish, &p); start(&ct, race_close, &close);
        join(&pt); join(&ct); join(&rt);
        CHECK(close.status == RB_OK && (p.status == RB_OK || p.status == RB_CLOSED));
        CHECK(r.result == RB_OK || r.result == RB_CLOSED);
        if (r.result == RB_OK) CHECK(p.status == RB_OK && r.out[96] == 99);
        CHECK(rb_get_health(b, &h) == RB_OK);
        CHECK(h.published == h.delivered + h.dropped_close && !h.queued && !h.active_reads);
        cleanup(&b);
    }
}
typedef struct stress_reader { rb_broker *b; unsigned seen[EVENTS + 1]; uint64_t total; } stress_reader;
static void reader_loop(void *p) {
    stress_reader *r = (stress_reader *)p; uint8_t out[RB_RESPONSE_MAX]; size_t written, required;
    for (;;) {
        enum rb_status status = read_one(r->b, out, sizeof(out), 100, &written, &required);
        uint64_t ordinal; unsigned i;
        if (status == RB_CLOSED) return;
        if (status == RB_TIMEOUT) continue;
        CHECK(status == RB_OK && written == RB_RESPONSE_MAX);
        ordinal = get64(out + 48); CHECK(ordinal && ordinal <= EVENTS);
        CHECK(!r->seen[ordinal]); r->seen[ordinal] = 1; ++r->total;
        for (i = 0; i < RB_PAYLOAD_MAX; ++i)
            CHECK(out[RB_HEADER_BYTES + i] == (uint8_t)((ordinal * 17u + i * 3u) & 255u));
        CHECK(get32(out + 20) == 0 && get64(out + 80) != 0);
    }
}
static void publisher_loop(void *p) {
    rb_broker *b = (rb_broker *)p; uint8_t payload[RB_PAYLOAD_MAX]; unsigned n, i;
    for (n = 1; n <= EVENTS; ++n) {
        enum rb_status status;
        for (i = 0; i < RB_PAYLOAD_MAX; ++i) payload[i] = (uint8_t)((n * 17u + i * 3u) & 255u);
        status = rb_publish(b, 7, payload, sizeof(payload), 0, sizeof(payload), RB_SIMULATED_POINT_B);
        CHECK(status == RB_OK || status == RB_FULL);
        memset(payload, 0xa5, sizeof(payload)); /* Source reuse immediately after publish. */
        if (status == RB_FULL) pause_ms();
    }
}
static void concurrent_readers(unsigned count) {
    rb_broker *b = make(); stress_reader readers[4] = {0}; thread ts[4], writer;
    rb_health h; unsigned i, n, attempts; uint64_t total = 0;
    for (i = 0; i < count; ++i) { readers[i].b = b; start(&ts[i], reader_loop, &readers[i]); }
    wait_readers(b, count); start(&writer, publisher_loop, b); join(&writer);
    for (attempts = 0; attempts < 3000; ++attempts) {
        CHECK(rb_get_health(b, &h) == RB_OK);
        if (h.delivered == h.published) break;
        pause_ms();
    }
    CHECK(attempts < 3000); CHECK(rb_close(b) == RB_OK);
    for (i = 0; i < count; ++i) { join(&ts[i]); total += readers[i].total; }
    for (n = 1; n <= EVENTS; ++n) {
        unsigned seen = 0; for (i = 0; i < count; ++i) seen += readers[i].seen[n]; CHECK(seen <= 1);
    }
    CHECK(rb_get_health(b, &h) == RB_OK && h.delivered == total);
    CHECK(h.published + h.dropped_full == EVENTS && h.published == h.delivered);
    CHECK(!h.queued && !h.pending_requests && !h.active_reads && !h.rejected);
    printf("readers=%u delivered=%llu overflow_drops=%llu\n", count,
           (unsigned long long)h.delivered, (unsigned long long)h.dropped_full);
    cleanup(&b);
}
int main(void) {
    CHECK(!rb_create(0, 1, 1, RB_FIXTURE)); CHECK(!rb_create(1, 1, 1, 99));
    basics(); pressure_and_invalidation(); cancellation_and_close(); cancellation_races(); close_publication_races();
    concurrent_readers(1); concurrent_readers(4);
    puts("all raw broker software checks passed; no hardware source connected");
    return 0;
}
