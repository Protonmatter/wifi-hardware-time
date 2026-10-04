#include "../research/export_contract/timestamp_export.h"
#include <stdio.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)

static te_record sample(void)
{
    te_record r = {0};
    r.schema = 1; r.size = sizeof(r); r.profile = TE_AUTONOMOUS;
    r.provenance = TE_SYNTHETIC; r.unit = TE_TICKS;
    r.reference = TE_SIMULATED_RX_START; r.meaningful_bits = 48;
    r.timestamp_valid = 1; r.complete = 1; r.timestamp = 123;
    r.rate_hz = 1000000; r.source_scope = 10; r.clock_id = 20;
    r.session = 30; r.epoch = 40; r.generation = 50;
    r.event_id = 1; r.peer_id = 60; r.link_id = 70;
    r.payload_size = 3; memcpy(r.payload, "abc", 3);
    return r;
}

int main(void)
{
    te_state s, before;
    te_record r = sample(), out, original, bad;
    te_health health, health_before;
    size_t written = 999;
    CHECK(te_init(&s, &r) == TE_OK);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    original = r; r.timestamp = 999; memset(r.payload, 'x', 3);
    before = s; memset(&out, 0xa5, sizeof(out)); bad = out;
    CHECK(te_read(&s, &out, sizeof(out)-1, &written) == TE_SMALL_BUFFER);
    CHECK(written == 0 && memcmp(&s, &before, sizeof(s)) == 0);
    CHECK(memcmp(&out, &bad, sizeof(out)) == 0);
    CHECK(te_read(&s, &out, sizeof(out), &written) == TE_OK);
    CHECK(written == sizeof(out) && memcmp(&out, &original, sizeof(out)) == 0);
    CHECK(te_read(&s, &out, sizeof(out), &written) == TE_EMPTY && written == 0);
    CHECK(te_publish(&s, &original, sizeof(original)) == TE_STALE);
    r = sample(); r.event_id = 2;
#define INVALID_FIELD(field, value) do { bad = r; bad.field = (value); \
    CHECK(te_publish(&s, &bad, sizeof(bad)) != TE_OK); CHECK(s.count == 0); } while (0)
    INVALID_FIELD(schema, 2); INVALID_FIELD(size, sizeof(r)-1);
    INVALID_FIELD(profile, 99); INVALID_FIELD(provenance, 0);
    INVALID_FIELD(unit, 0); INVALID_FIELD(reference, 0);
    INVALID_FIELD(meaningful_bits, 0); INVALID_FIELD(meaningful_bits, 65);
    INVALID_FIELD(timestamp, UINT64_MAX); INVALID_FIELD(rate_hz, 0);
    INVALID_FIELD(timestamp_valid, 0); INVALID_FIELD(timestamp_valid, 2);
    INVALID_FIELD(complete, 0); INVALID_FIELD(live_clock_eligible, 1);
    INVALID_FIELD(payload_size, TE_PAYLOAD + 1); INVALID_FIELD(reserved, 1);
    INVALID_FIELD(reserved2, 1); INVALID_FIELD(rate_hz, 1000001);
    INVALID_FIELD(source_scope, 11); INVALID_FIELD(clock_id, 21);
    INVALID_FIELD(session, 31); INVALID_FIELD(epoch, 39);
    INVALID_FIELD(generation, 49); INVALID_FIELD(peer_id, 61);
    INVALID_FIELD(link_id, 71); INVALID_FIELD(request_token, 1);
    INVALID_FIELD(token_binding, TE_BACKEND_TOKEN);
    bad = r; bad.payload[TE_PAYLOAD-1] = 1;
    CHECK(te_publish(&s, &bad, sizeof(bad)) == TE_INVALID);
    CHECK(te_publish(&s, &r, sizeof(r)-1) == TE_INVALID && s.count == 0);
    CHECK(te_publish(&s, NULL, sizeof(r)) == TE_INVALID);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    before = s; bad = out;
    CHECK(te_read(&s, &out, sizeof(out), NULL) == TE_INVALID);
    CHECK(memcmp(&s, &before, sizeof(s)) == 0 && memcmp(&out, &bad, sizeof(out)) == 0);
    CHECK(te_read(&s, NULL, sizeof(out), &written) == TE_INVALID && s.count == 1);
    ++r.event_id; CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    ++r.event_id; CHECK(te_publish(&s, &r, sizeof(r)) == TE_FULL);
    CHECK(s.losses == 1 && s.count == TE_CAPACITY);
    memset(&health, 0xa5, sizeof(health)); health_before = health; before = s;
    CHECK(te_snapshot(&s, &health, sizeof(health)-1) == TE_SMALL_BUFFER);
    CHECK(memcmp(&health, &health_before, sizeof(health)) == 0);
    CHECK(memcmp(&s, &before, sizeof(s)) == 0);
    CHECK(te_read(&s, &out, sizeof(out), &written) == TE_OK && out.event_id == 2);
    CHECK(te_snapshot(&s, &health, sizeof(health)) == TE_OK);
    CHECK(health.schema == 1 && health.size == sizeof(health) && health.losses == 1);
    CHECK(health.queued == 1 && health.session == 30 && health.epoch == 40);
    CHECK(health.generation == 50 && health.closed == 0 && health.quarantined == 0);
    CHECK(health.reserved == 0 && health.rejects > 0);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_STALE); /* Dropped event consumed. */
    CHECK(te_new_generation(&s, 41, 50, TE_BACKEND_GENERATION) == TE_STALE);
    CHECK(te_new_generation(&s, 41, 51, TE_HOST_TAG) == TE_INVALID);
    CHECK(te_new_generation(&s, 41, 51, TE_BACKEND_GENERATION) == TE_OK);
    CHECK(s.losses == 2 && s.count == 0);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_MISMATCH);
    r.epoch = 41; r.generation = 51; r.event_id = 1;
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    te_close(&s);
    CHECK(te_read(&s, &out, sizeof(out), &written) == TE_CLOSED);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_CLOSED);
    CHECK(s.losses == 3 && s.count == 0);

    r = sample(); r.session = 31; r.profile = TE_SOLICITED; r.request_token = 7;
    r.token_binding = TE_BACKEND_TOKEN;
    CHECK(te_init(&s, &r) == TE_OK);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_MISMATCH);
    CHECK(te_begin(&s, 1, 7, TE_HOST_TAG) == TE_INVALID);
    CHECK(te_begin(&s, 1, 7, TE_BACKEND_TOKEN) == TE_OK);
    before = s;
    CHECK(te_begin(&s, 2, 8, TE_BACKEND_TOKEN) == TE_BUSY);
    CHECK(memcmp(&s, &before, sizeof(s)) == 0);
    bad = r; bad.request_token = 8;
    CHECK(te_publish(&s, &bad, sizeof(bad)) == TE_MISMATCH);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_STALE);
    CHECK(te_begin(&s, 2, 7, TE_BACKEND_TOKEN) == TE_STALE);
    CHECK(te_begin(&s, 2, 8, TE_BACKEND_TOKEN) == TE_OK);
    CHECK(te_abort(&s, TE_TIMEOUT) == TE_OK);
    CHECK(te_begin(&s, 3, 9, TE_BACKEND_TOKEN) == TE_QUARANTINED);
    r.event_id = 2; r.request_token = 8;
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_QUARANTINED);
    CHECK(te_new_generation(&s, 41, 50, TE_BACKEND_GENERATION) == TE_STALE);
    CHECK(s.quarantined == 1);
    CHECK(te_new_generation(&s, 41, 51, TE_BACKEND_GENERATION) == TE_OK);
    CHECK(te_begin(&s, 1, 7, TE_BACKEND_TOKEN) == TE_OK);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_MISMATCH); /* Old generation, reused token. */
    r.event_id = 1; r.request_token = 7; r.epoch = 41; r.generation = 51;
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    CHECK(te_begin(&s, 2, 8, TE_BACKEND_TOKEN) == TE_OK);
    CHECK(te_abort(&s, TE_CANCELLED) == TE_OK);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_QUARANTINED);
    CHECK(te_new_generation(&s, 42, 52, TE_BACKEND_GENERATION) == TE_OK);
    r.epoch = 42; r.generation = 52; r.meaningful_bits = 64;
    r.timestamp = UINT64_MAX;
    te_close(&s);
    r.session = 32;
    CHECK(te_init(&s, &r) == TE_OK);
    CHECK(te_begin(&s, 1, 7, TE_BACKEND_TOKEN) == TE_OK);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    s.rejects = UINT64_MAX;
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_STALE && s.rejects == UINT64_MAX);
    s.losses = UINT64_MAX;
    te_close(&s);
    CHECK(s.losses == UINT64_MAX);
    r = sample(); r.session = 33; r.clock_id = 0; r.link_id = 0;
    CHECK(te_init(&s, &r) == TE_OK);
    bad = r; bad.clock_id = 1;
    CHECK(te_publish(&s, &bad, sizeof(bad)) == TE_MISMATCH);
    bad = r; bad.link_id = 1;
    CHECK(te_publish(&s, &bad, sizeof(bad)) == TE_MISMATCH);
    CHECK(te_publish(&s, &r, sizeof(r)) == TE_OK);
    CHECK(te_read(&s, &out, sizeof(out), &written) == TE_OK);
    CHECK(out.clock_id == 0 && out.link_id == 0);
    te_close(&s);
    puts("owned timestamp export: all offline contract checks passed");
    return 0;
}
