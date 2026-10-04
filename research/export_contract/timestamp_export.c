#include "timestamp_export.h"
#include <string.h>

static void add(uint64_t *counter, uint64_t n)
{
    *counter = UINT64_MAX - *counter < n ? UINT64_MAX : *counter + n;
}

static int valid(const te_record *r)
{
    uint32_t i;
    if (r->schema != 1 || r->size != sizeof(*r) ||
        (r->profile != TE_AUTONOMOUS && r->profile != TE_SOLICITED) ||
        r->provenance != TE_SYNTHETIC || r->unit != TE_TICKS ||
        (r->reference != TE_SIMULATED_RX_START && r->reference != TE_SIMULATED_TX_START) ||
        r->meaningful_bits == 0 || r->meaningful_bits > 64 ||
        r->timestamp_valid != 1 || r->complete != 1 || r->live_clock_eligible != 0 ||
        r->payload_size > TE_PAYLOAD || r->reserved || r->reserved2 ||
        !r->rate_hz || !r->source_scope || !r->session || !r->epoch ||
        !r->generation || !r->event_id || !r->peer_id) return 0;
    if (r->meaningful_bits < 64 && (r->timestamp >> r->meaningful_bits)) return 0;
    if (r->profile == TE_AUTONOMOUS && (r->request_token || r->token_binding)) return 0;
    if (r->profile == TE_SOLICITED && (!r->request_token || r->token_binding != TE_BACKEND_TOKEN)) return 0;
    for (i = r->payload_size; i < TE_PAYLOAD; ++i) if (r->payload[i]) return 0;
    return 1;
}

enum te_status te_init(te_state *s, const te_record *r)
{
    if (!s || !r || !valid(r)) return TE_INVALID;
    memset(s, 0, sizeof(*s));
    s->identity = *r;
    return TE_OK;
}

static int matches(const te_record *a, const te_record *b)
{
    return a->profile == b->profile && a->unit == b->unit && a->reference == b->reference &&
        a->meaningful_bits == b->meaningful_bits && a->rate_hz == b->rate_hz &&
        a->source_scope == b->source_scope && a->clock_id == b->clock_id &&
        a->session == b->session && a->epoch == b->epoch && a->generation == b->generation &&
        a->peer_id == b->peer_id && a->link_id == b->link_id;
}

enum te_status te_publish(te_state *s, const void *record, size_t size)
{
    te_record owned = {0};
    enum te_status result = TE_OK;
    if (!s) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (s->quarantined) result = TE_QUARANTINED;
    else if (!record || size != sizeof(owned)) result = TE_INVALID;
    else {
        /* Caller stabilizes the complete source; publication retains only this copy. */
        memcpy(&owned, record, sizeof(owned));
        if (!valid(&owned)) result = TE_INVALID;
        else if (!matches(&s->identity, &owned)) result = TE_MISMATCH;
        else if (owned.event_id <= s->last_event) result = TE_STALE;
        else if (owned.profile == TE_SOLICITED && (!s->active ||
            owned.event_id != s->expected_event || owned.request_token != s->expected_token)) result = TE_MISMATCH;
    }
    if (result != TE_OK) { add(&s->rejects, 1); return result; }
    /* An admitted event is consumed even when capacity forces a drop. */
    s->last_event = owned.event_id;
    s->active = 0;
    if (s->count == TE_CAPACITY) { add(&s->losses, 1); return TE_FULL; }
    s->queue[(s->head + s->count) % TE_CAPACITY] = owned;
    ++s->count; /* Commit point under the caller's serialization. */
    return TE_OK;
}

enum te_status te_read(te_state *s, void *output, size_t capacity, size_t *written)
{
    if (!written) return TE_INVALID;
    *written = 0;
    if (!s || !output) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (capacity < sizeof(te_record)) return TE_SMALL_BUFFER;
    if (!s->count) return TE_EMPTY;
    memcpy(output, &s->queue[s->head], sizeof(te_record));
    memset(&s->queue[s->head], 0, sizeof(te_record));
    s->head = (s->head + 1) % TE_CAPACITY;
    --s->count;
    *written = sizeof(te_record);
    return TE_OK;
}

enum te_status te_begin(te_state *s, uint64_t event, uint64_t token, uint32_t binding)
{
    if (!s || !event || !token || binding != TE_BACKEND_TOKEN) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (s->identity.profile != TE_SOLICITED) return TE_INVALID;
    if (s->quarantined) return TE_QUARANTINED;
    if (s->active) return TE_BUSY;
    if (event <= s->last_event || token <= s->last_token) return TE_STALE;
    s->expected_event = event; s->expected_token = token;
    s->last_token = token; s->active = 1;
    return TE_OK;
}

enum te_status te_abort(te_state *s, uint32_t reason)
{
    if (!s || (reason != TE_TIMEOUT && reason != TE_CANCELLED)) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (s->identity.profile != TE_SOLICITED || !s->active) return TE_INVALID;
    s->active = 0; s->quarantined = 1;
    return TE_OK;
}

static void flush(te_state *s)
{
    add(&s->losses, s->count);
    memset(s->queue, 0, sizeof(s->queue));
    s->head = 0; s->count = 0;
}

enum te_status te_new_generation(te_state *s, uint64_t epoch, uint64_t generation, uint32_t binding)
{
    if (!s || binding != TE_BACKEND_GENERATION) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (epoch <= s->identity.epoch || generation <= s->identity.generation) return TE_STALE;
    /* Synthetic backend declaration only: never evidence of firmware drain. */
    flush(s);
    s->identity.epoch = epoch; s->identity.generation = generation;
    s->last_event = 0; s->last_token = 0; s->expected_event = 0; s->expected_token = 0;
    s->active = 0; s->quarantined = 0;
    return TE_OK;
}

void te_close(te_state *s)
{
    if (!s) return;
    flush(s);
    s->active = 0; s->closed = 1;
}

enum te_status te_snapshot(const te_state *s, void *output, size_t capacity)
{
    te_health health = {0};
    if (!s || !output) return TE_INVALID;
    if (capacity < sizeof(health)) return TE_SMALL_BUFFER;
    health.schema = 1; health.size = sizeof(health);
    health.quarantined = s->quarantined; health.closed = s->closed;
    health.losses = s->losses; health.rejects = s->rejects;
    health.session = s->identity.session; health.epoch = s->identity.epoch;
    health.generation = s->identity.generation; health.queued = s->count;
    memcpy(output, &health, sizeof(health));
    return TE_OK;
}
