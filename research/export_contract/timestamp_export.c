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

/* Diagnostic event records: software qualification is separate from hardware. */
static uint32_t event_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
        ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int event_meta_valid(const te_event_meta *m)
{
    return m && m->schema == TE_EVENT_SCHEMA && m->provenance == TE_SYNTHETIC &&
        m->identity_present == TE_IDENTITY_PRESENT && m->host_observation == TE_CALLBACK_ENTRY_QPC &&
        m->source_scope && m->session && m->epoch && m->generation && m->sequence &&
        m->qpc_frequency && m->normalized_device_present == 1;
}

static enum te_status event_error(te_event_state *s, enum te_status result)
{
    if (s && result != TE_OK && result != TE_CLOSED) add(&s->rejects, 1);
    return result;
}

static enum te_status event_check(te_event_state *s, const te_event_meta *m)
{
    const te_event_meta *a;
    if (!s) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (s->quarantined) return TE_QUARANTINED;
    if (!event_meta_valid(m)) return TE_INVALID;
    a = &s->identity;
    if (a->source_scope != m->source_scope || a->clock_id != m->clock_id ||
        a->peer_id != m->peer_id || a->link_id != m->link_id || a->session != m->session ||
        a->epoch != m->epoch || a->generation != m->generation ||
        a->normalized_device_id != m->normalized_device_id || a->qpc_frequency != m->qpc_frequency)
        return TE_MISMATCH;
    return m->sequence <= s->last_sequence ? TE_STALE : TE_OK;
}

static enum te_status event_commit(te_event_state *s, const te_event_record *r)
{
    uint32_t slot;
    s->last_sequence = r->meta.sequence;
    if (s->count == TE_CAPACITY) { add(&s->losses, 1); return TE_FULL; }
    slot = (s->head + s->count) % TE_CAPACITY;
    s->queue[slot] = *r;
    s->queue[slot].software_losses_before = s->losses;
    s->queue[slot].software_rejects_before = s->rejects;
    ++s->count; /* Only after the complete copy, under caller serialization. */
    return TE_OK;
}

uint32_t te_event_capabilities(void)
{
    return TE_CAP_SYNTHETIC_MLO | TE_CAP_SYNTHETIC_MANAGEMENT;
}

enum te_status te_event_init(te_event_state *s, const te_event_meta *m)
{
    if (!s || !event_meta_valid(m)) return TE_INVALID;
    memset(s, 0, sizeof(*s)); s->identity = *m;
    return TE_OK;
}

enum te_status te_event_publish_mlo(te_event_state *s, const te_event_meta *m,
    const void *message, size_t size)
{
    te_event_record r = {0};
    uint32_t w[8], i;
    enum te_status status = event_check(s, m);
    if (status != TE_OK) return event_error(s, status);
    if (!message || size != sizeof(r.mlo_raw)) return event_error(s, TE_INVALID);
    memcpy(r.mlo_raw, message, sizeof(r.mlo_raw));
    for (i = 0; i < 8; ++i) w[i] = event_le32(r.mlo_raw + i*4);
    /* Pinned reference layout only; reject reserved bits rather than guess. */
    if ((w[0] & 0xff) != 0x28 || (w[0] & 0xf000) || (w[0] >> 16) == 0 ||
        (w[6] & 0xfc000000) || (w[7] & 0xffc00000)) return event_error(s, TE_INVALID);
    r.schema = TE_EVENT_SCHEMA; r.size = sizeof(r); r.kind = TE_EVENT_MLO; r.meta = *m;
    r.mlo.firmware_device_id = (w[0] >> 8) & 3; r.mlo.chip_id = (w[0] >> 10) & 3;
    r.mlo.mac_frequency_mhz = w[0] >> 16;
    r.mlo.sync_time_us_reference = ((uint64_t)w[2] << 32) | w[1];
    r.mlo.offset_us_reference = ((uint64_t)w[4] << 32) | w[3];
    r.mlo.offset_ticks = w[5]; r.mlo.compensation_us = w[6] & 0xffff;
    r.mlo.compensation_ticks = (w[6] >> 16) & 0x3ff; r.mlo.period_us = w[7] & 0x3fffff;
    return event_commit(s, &r);
}

enum te_status te_event_publish_management(te_event_state *s, const te_event_meta *m,
    const void *header, size_t header_size, const void *frame, size_t frame_size,
    const void *reo, size_t reo_size)
{
    te_event_record r = {0};
    size_t pos;
    enum te_status status = event_check(s, m);
    if (status != TE_OK) return event_error(s, status);
    if (!m->peer_id || !header || header_size != sizeof(r.management_header) || !frame ||
        frame_size < 36 || frame_size > TE_FRAME_MAX ||
        (reo == NULL) != (reo_size == 0) || (reo_size && reo_size != sizeof(r.management_reo)))
        return event_error(s, TE_INVALID);
    memcpy(r.management_header, header, header_size);
    if (event_le32(r.management_header) != ((44u << 16) | 68u) ||
        event_le32(r.management_header + 20) != frame_size) return event_error(s, TE_INVALID);
    if (reo_size) {
        memcpy(r.management_reo, reo, reo_size);
        if (event_le32(r.management_reo) != ((978u << 16) | 16u)) return event_error(s, TE_INVALID);
        r.reo_present = 1;
    }
    memcpy(r.frame, frame, frame_size);
    /* Reference fixture supports complete unprotected Beacon/Probe Response only. */
    if ((r.frame[0] != 0x80 && r.frame[0] != 0x50) || (r.frame[1] & 0xc7) ||
        (r.frame[22] & 0x0f)) return event_error(s, TE_INVALID);
    for (pos = 36; pos < frame_size;) {
        if (frame_size-pos < 2 || r.frame[pos+1] > frame_size-pos-2) return event_error(s, TE_INVALID);
        pos += 2 + r.frame[pos+1];
    }
    r.schema = TE_EVENT_SCHEMA; r.size = sizeof(r); r.kind = TE_EVENT_MANAGEMENT;
    r.frame_size = (uint32_t)frame_size; r.meta = *m;
    return event_commit(s, &r);
}

enum te_status te_event_read(te_event_state *s, te_event_record *out, size_t capacity, size_t *written)
{
    if (!written) return TE_INVALID;
    *written = 0;
    if (!s || !out) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (s->quarantined) return TE_QUARANTINED;
    if (capacity < sizeof(*out)) return TE_SMALL_BUFFER;
    if (!s->count) return TE_EMPTY;
    memcpy(out, &s->queue[s->head], sizeof(*out));
    memset(&s->queue[s->head], 0, sizeof(*out));
    s->head = (s->head + 1) % TE_CAPACITY; --s->count;
    *written = sizeof(*out); return TE_OK;
}

static void event_flush(te_event_state *s)
{
    add(&s->losses, s->count); memset(s->queue, 0, sizeof(s->queue));
    s->head = 0; s->count = 0;
}

void te_event_quarantine(te_event_state *s)
{
    if (!s || s->closed) return;
    event_flush(s); s->quarantined = 1;
}

void te_event_close(te_event_state *s)
{
    if (!s) return;
    event_flush(s); s->closed = 1;
}

enum te_status te_event_new_generation(te_event_state *s, uint64_t epoch, uint64_t generation)
{
    if (!s) return TE_INVALID;
    if (s->closed) return TE_CLOSED;
    if (epoch <= s->identity.epoch || generation <= s->identity.generation) return TE_STALE;
    event_flush(s); s->identity.epoch = epoch; s->identity.generation = generation;
    s->last_sequence = 0; s->quarantined = 0;
    return TE_OK; /* Synthetic declaration, not proof that firmware reports drained. */
}
