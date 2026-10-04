#ifndef TIMESTAMP_EXPORT_H
#define TIMESTAMP_EXPORT_H
#include <stddef.h>
#include <stdint.h>

#define TE_PAYLOAD 64u
#define TE_CAPACITY 2u
enum te_status { TE_OK, TE_INVALID, TE_MISMATCH, TE_STALE, TE_FULL,
    TE_SMALL_BUFFER, TE_EMPTY, TE_QUARANTINED, TE_CLOSED, TE_BUSY };
enum { TE_AUTONOMOUS = 1, TE_SOLICITED = 2, TE_SYNTHETIC = 1,
    TE_TICKS = 1, TE_SIMULATED_RX_START = 1, TE_SIMULATED_TX_START = 2,
    TE_HOST_TAG = 0, TE_BACKEND_TOKEN = 1, TE_BACKEND_GENERATION = 1,
    TE_TIMEOUT = 1, TE_CANCELLED = 2 };
typedef struct te_record {
    uint32_t schema, size, profile, provenance, unit, reference, meaningful_bits;
    uint32_t timestamp_valid, complete, live_clock_eligible, payload_size, reserved;
    uint32_t token_binding, reserved2;
    uint64_t timestamp, rate_hz, source_scope, clock_id, session, epoch, generation;
    uint64_t event_id, peer_id, link_id, request_token;
    uint8_t payload[TE_PAYLOAD];
} te_record;
_Static_assert(offsetof(te_record, timestamp) == 56, "unexpected ABI layout");
_Static_assert(offsetof(te_record, payload) == 144, "unexpected ABI layout");
_Static_assert(sizeof(te_record) == 208, "unexpected ABI size");
typedef struct te_state {
    te_record identity, queue[TE_CAPACITY];
    uint64_t last_event, last_token, expected_event, expected_token, losses, rejects;
    uint32_t head, count, active, quarantined, closed;
} te_state;
typedef struct te_health {
    uint32_t schema, size, quarantined, closed;
    uint64_t losses, rejects, session, epoch, generation;
    uint32_t queued, reserved;
} te_health;
_Static_assert(offsetof(te_health, losses) == 16, "unexpected health layout");
_Static_assert(sizeof(te_health) == 64, "unexpected health size");
/* Caller must serialize ALL operations and stabilize input throughout each call.
 * Buffers must not overlap state or each other. No pointers are retained.
 * Records use native endian integers, not an installed kernel/wire ABI.
 * Context must first be initialized; initialize again only after close and with
 * a fresh caller-assigned session. No persistent quarantine or firmware drain. */
enum te_status te_init(te_state *s, const te_record *identity);
enum te_status te_publish(te_state *s, const void *record, size_t size);
enum te_status te_read(te_state *s, void *output, size_t capacity, size_t *written);
enum te_status te_begin(te_state *s, uint64_t event, uint64_t token, uint32_t binding);
enum te_status te_abort(te_state *s, uint32_t reason);
enum te_status te_new_generation(te_state *s, uint64_t epoch, uint64_t generation, uint32_t binding);
enum te_status te_snapshot(const te_state *s, void *output, size_t capacity);
void te_close(te_state *s);

/* Additive offline event API. No installed-driver ABI or live producer binding.
 * Caller serializes operations, stabilizes spans and provides nonoverlapping
 * buffers. State must be initialized before use. Reinitialize only after close
 * with a new session. These rules are software preconditions, not firmware proof. */
#define TE_FRAME_MAX 4096u
enum { TE_EVENT_MLO = 1, TE_EVENT_MANAGEMENT = 2, TE_EVENT_SCHEMA = 1,
    TE_CALLBACK_ENTRY_QPC = 1, TE_IDENTITY_PRESENT = 1,
    TE_CAP_SYNTHETIC_MLO = 1, TE_CAP_SYNTHETIC_MANAGEMENT = 2 };
typedef struct te_event_meta {
    uint32_t schema, provenance, identity_present, host_observation;
    uint64_t source_scope, clock_id, peer_id, link_id, session, epoch, generation;
    uint64_t sequence, callback_entry_qpc, qpc_frequency;
    uint32_t normalized_device_id, normalized_device_present;
} te_event_meta;
typedef struct te_mlo_fields {
    uint32_t firmware_device_id, chip_id, mac_frequency_mhz;
    uint32_t offset_ticks, compensation_us, compensation_ticks, period_us;
    uint64_t sync_time_us_reference, offset_us_reference;
} te_mlo_fields;
typedef struct te_event_record {
    uint32_t schema, size, kind, frame_size, reo_present;
    uint32_t live_clock_eligible, packet_timestamp_qualified, hardware_qpc_qualified;
    uint64_t software_losses_before, software_rejects_before;
    te_event_meta meta;
    te_mlo_fields mlo;
    uint8_t mlo_raw[32], management_header[72], management_reo[20];
    uint8_t frame[TE_FRAME_MAX];
} te_event_record;
typedef struct te_event_state {
    te_event_meta identity;
    te_event_record queue[TE_CAPACITY];
    uint64_t last_sequence, losses, rejects;
    uint32_t head, count, quarantined, closed;
} te_event_state;
/* Capability bits describe tested synthetic software support, not hardware. */
uint32_t te_event_capabilities(void);
enum te_status te_event_init(te_event_state *s, const te_event_meta *identity);
enum te_status te_event_publish_mlo(te_event_state *s, const te_event_meta *meta,
    const void *message, size_t size);
enum te_status te_event_publish_management(te_event_state *s, const te_event_meta *meta,
    const void *header, size_t header_size, const void *frame, size_t frame_size,
    const void *reo, size_t reo_size);
enum te_status te_event_read(te_event_state *s, te_event_record *out, size_t capacity,
    size_t *written);
void te_event_quarantine(te_event_state *s);
void te_event_close(te_event_state *s);
enum te_status te_event_new_generation(te_event_state *s, uint64_t epoch, uint64_t generation);
#endif
