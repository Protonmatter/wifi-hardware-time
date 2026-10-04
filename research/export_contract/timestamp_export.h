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
#endif
