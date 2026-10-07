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

static void le32(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)value; p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16); p[3] = (uint8_t)(value >> 24);
}

static int event_checks(void)
{
    /* Static storage keeps this userspace regression's large records off stack. */
    static te_event_state s;
    static te_event_record out, unchanged;
    te_event_meta m = {0}, bad;
    uint8_t msg[32] = {0}, original[32], header[72] = {0}, frame[36] = {0}, reo[20] = {0};
    uint8_t malformed_ie[38] = {0};
    size_t written;
    m.schema = TE_EVENT_SCHEMA; m.provenance = TE_SYNTHETIC;
    m.identity_present = TE_IDENTITY_PRESENT; m.host_observation = TE_CALLBACK_ENTRY_QPC;
    m.source_scope = 1; m.clock_id = 0; m.peer_id = 2; m.link_id = 0;
    m.session = 3; m.epoch = 4; m.generation = 5; m.sequence = 1;
    m.callback_entry_qpc = 1234; m.qpc_frequency = 10000000;
    m.normalized_device_present = 1; m.normalized_device_id = 0;
    CHECK(te_event_capabilities() == (TE_CAP_SYNTHETIC_MLO | TE_CAP_SYNTHETIC_MANAGEMENT));
    CHECK(te_event_init(&s, &m) == TE_OK);
    le32(msg, 0x03200928); /* frequency 800 MHz, chip 2, raw pdev 1 */
    le32(msg+4, 0x89abcdef); le32(msg+8, 0x01234567);
    le32(msg+12, 0x76543210); le32(msg+16, 0xfedcba98);
    le32(msg+20, 7); le32(msg+24, (9u << 16) | 8u); le32(msg+28, 1000);
    memcpy(original, msg, sizeof(msg));
    CHECK(te_event_publish_mlo(&s, &m, msg, 31) == TE_INVALID && s.count == 0);
    CHECK(te_event_publish_mlo(&s, &m, msg, 33) == TE_INVALID);
    msg[0] = 0x29; CHECK(te_event_publish_mlo(&s, &m, msg, 32) == TE_INVALID); msg[0] = 0x28;
    msg[1] |= 0x10; CHECK(te_event_publish_mlo(&s, &m, msg, 32) == TE_INVALID); msg[1] &= 0x0f;
    bad = m; bad.identity_present = 0;
    CHECK(te_event_publish_mlo(&s, &bad, msg, 32) == TE_INVALID);
    bad = m; bad.qpc_frequency = 0;
    CHECK(te_event_publish_mlo(&s, &bad, msg, 32) == TE_INVALID);
    bad = m; bad.source_scope++;
    CHECK(te_event_publish_mlo(&s, &bad, msg, 32) == TE_MISMATCH);
    CHECK(te_event_publish_mlo(&s, &m, msg, 32) == TE_OK);
    memset(msg, 0xcc, sizeof(msg));
    memset(&out, 0xa5, sizeof(out)); unchanged = out;
    CHECK(te_event_read(&s, &out, sizeof(out)-1, &written) == TE_SMALL_BUFFER);
    CHECK(written == 0 && s.count == 1 && memcmp(&out, &unchanged, sizeof(out)) == 0);
    CHECK(te_event_read(&s, &out, sizeof(out), &written) == TE_OK);
    CHECK(written == sizeof(out) && out.kind == TE_EVENT_MLO);
    CHECK(memcmp(out.mlo_raw, original, 32) == 0);
    CHECK(out.mlo.firmware_device_id == 1 && out.meta.normalized_device_id == 0);
    CHECK(out.mlo.chip_id == 2 && out.mlo.mac_frequency_mhz == 800);
    CHECK(out.mlo.sync_time_us_reference == UINT64_C(0x0123456789abcdef));
    CHECK(out.mlo.offset_us_reference == UINT64_C(0xfedcba9876543210));
    CHECK(out.mlo.offset_ticks == 7 && out.mlo.compensation_ticks == 9 && out.mlo.compensation_us == 8);
    CHECK(out.software_rejects_before > 0 && out.software_losses_before == 0);
    CHECK(out.meta.callback_entry_qpc == 1234 && !out.hardware_qpc_qualified && !out.live_clock_eligible);
    CHECK(!out.packet_timestamp_qualified);
    CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_STALE);
    m.sequence = 2;
    le32(header, (44u << 16) | 68u); le32(header+20, sizeof(frame));
    frame[0] = 0x80; /* Beacon; fixture contains complete fixed header/body. */
    le32(reo, (978u << 16) | 16u);
    CHECK(te_event_publish_management(&s, &m, header, 71, frame, 36, reo, 20) == TE_INVALID);
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, 35, reo, 20) == TE_INVALID);
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, 36, reo, 19) == TE_INVALID);
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, 36, NULL, 20) == TE_INVALID);
    frame[0] = 0x08;
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, 36, reo, 20) == TE_INVALID);
    frame[0] = 0x80;
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, TE_FRAME_MAX+1, reo, 20) == TE_INVALID);
    memcpy(malformed_ie, frame, 36); malformed_ie[36] = 1; malformed_ie[37] = 7;
    le32(header+20, 38);
    CHECK(te_event_publish_management(&s, &m, header, 72, malformed_ie, 38, reo, 20) == TE_INVALID);
    le32(header+20, 36);
    frame[1] = 4;
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, 36, reo, 20) == TE_INVALID);
    frame[1] = 0;
    {
        static te_event_state trial;
        te_event_meta trial_meta = m;
        const uint8_t subtypes[] = {0x80, 0x50}, layout_flags[] = {0x01, 0x02, 0x80};
        size_t i, j;
        trial_meta.sequence = 1;
        CHECK(te_event_init(&trial, &trial_meta) == TE_OK);
        for (i = 0; i < sizeof(subtypes); ++i) for (j = 0; j < sizeof(layout_flags); ++j) {
            uint64_t last = trial.last_sequence, rejects = trial.rejects;
            frame[0] = subtypes[i]; frame[1] = layout_flags[j];
            CHECK(te_event_publish_management(&trial, &trial_meta, header, 72, frame, 36, NULL, 0) == TE_INVALID);
            CHECK(trial.count == 0 && trial.last_sequence == last && trial.rejects == rejects+1);
            frame[1] = 0x08; /* Retry is supported without changing the header layout. */
            CHECK(te_event_publish_management(&trial, &trial_meta, header, 72, frame, 36, NULL, 0) == TE_OK);
            CHECK(te_event_read(&trial, &out, sizeof(out), &written) == TE_OK);
            CHECK(out.frame[1] == 0x08 && out.meta.sequence == trial_meta.sequence);
            ++trial_meta.sequence;
        }
        te_event_close(&trial);
        frame[0] = 0x80; frame[1] = 0;
    }
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, 36, reo, 20) == TE_OK);
    memset(header, 0, 72); memset(frame, 0, 36); memset(reo, 0, 20);
    CHECK(te_event_read(&s, &out, sizeof(out), &written) == TE_OK);
    CHECK(out.kind == TE_EVENT_MANAGEMENT && out.frame_size == 36 && out.frame[0] == 0x80);
    CHECK(out.management_header[0] == 68 && out.reo_present == 1 && out.management_reo[0] == 16);
    CHECK(!out.packet_timestamp_qualified && !out.hardware_qpc_qualified && !out.live_clock_eligible);
    m.sequence = 3; CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_OK);
    m.sequence = 4; CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_OK);
    m.sequence = 5; CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_FULL);
    CHECK(s.losses == 1 && s.count == 2);
    te_event_quarantine(&s);
    CHECK(s.losses == 3 && s.count == 0);
    CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_QUARANTINED);
    CHECK(te_event_new_generation(&s, 4, 6) == TE_STALE);
    CHECK(te_event_new_generation(&s, 5, 6) == TE_OK);
    CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_MISMATCH);
    m.epoch = 5; m.generation = 6; m.sequence = 1;
    CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_OK);
    CHECK(te_event_read(&s, &out, sizeof(out), &written) == TE_OK && out.software_losses_before == 3);
    m.sequence++;
    le32(header, (44u << 16) | 68u); le32(header+20, 36); frame[0] = 0x50;
    CHECK(te_event_publish_management(&s, &m, header, 72, frame, 36, NULL, 0) == TE_OK);
    te_event_close(&s);
    CHECK(s.count == 0 && s.losses == 4);
    CHECK(te_event_read(&s, &out, sizeof(out), &written) == TE_CLOSED && written == 0);
    CHECK(te_event_publish_mlo(&s, &m, original, 32) == TE_CLOSED);
    CHECK(te_event_new_generation(&s, 6, 7) == TE_CLOSED);
    return 0;
}

int main(void)
{
    te_state s, before;
    te_record r = sample(), out, original, bad;
    te_health health, health_before;
    size_t written = 999;
    CHECK(event_checks() == 0);
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
