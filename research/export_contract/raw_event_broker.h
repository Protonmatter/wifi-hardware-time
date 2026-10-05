#ifndef RAW_EVENT_BROKER_H
#define RAW_EVENT_BROKER_H
#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32) && defined(RB_BUILD_SHARED)
#define RB_API __declspec(dllexport)
#else
#define RB_API
#endif
#ifdef __cplusplus
extern "C" {
#endif

#define RB_CAPACITY 8u
#define RB_REQUESTS 8u
#define RB_PAYLOAD_MAX 4096u
#define RB_HEADER_BYTES 96u
#define RB_RESPONSE_MAX (RB_HEADER_BYTES + RB_PAYLOAD_MAX)
#define RB_TIMEOUT_MAX_MS 60000u

enum rb_status { RB_OK, RB_INVALID, RB_CLOSED, RB_FULL, RB_SMALL_BUFFER,
    RB_EMPTY, RB_TIMEOUT, RB_CANCELLED, RB_NOT_FOUND, RB_BUSY, RB_STALE,
    RB_LIMIT, RB_INTERNAL };
enum rb_origin { RB_FIXTURE = 1, RB_REPLAY_UNQUALIFIED = 2 };
enum rb_copy_point { RB_SIMULATED_POINT_A = 1, RB_SIMULATED_POINT_B = 2,
    RB_REPLAY_POINT_UNKNOWN = 3 };
enum rb_close_reason { RB_OPEN = 0, RB_OWNER_CLOSE = 1, RB_SOURCE_LOSS = 2,
    RB_CONTINUITY_UNKNOWN = 3 };

typedef struct rb_broker rb_broker;
typedef struct rb_health {
    uint64_t published, delivered, dropped_full, dropped_close, rejected;
    uint64_t source_losses_reported, cancellations, timeouts;
    uint32_t queued, pending_requests, active_reads, closed, close_reason;
} rb_health;

/* User-mode Windows/Linux research API; NOT callable at a kernel copy point.
 * No device access, IOCTL, driver hook or firmware association is implemented.
 * IDs/generation below describe a SOFTWARE session, not attested firmware state.
 * Choose a fresh session for each instance; the library checks nonzero values,
 * not global/persistent uniqueness. Ticket identities are scoped to that session.
 * All operational calls use an internal mutex. Source memory must independently
 * remain valid and stable for the entire publish call (including lock wait).
 * The broker never retains input/output pointers. Output/size pointers must be
 * valid and non-overlapping. Raw responses are explicit little-endian bytes.
 * No accepted provenance enables live clocks or source-copy qualification. */
RB_API rb_broker *rb_create(uint64_t session, uint64_t generation,
    uint64_t source_scope, uint32_t origin);
RB_API enum rb_status rb_publish(rb_broker *b, uint64_t generation,
    const void *source, size_t capacity, size_t offset, size_t received,
    uint32_t copy_point);

/* Read tickets are one-use APPLICATION request identities, never firmware tokens.
 * Reserve before dispatching a reader so cancellation may precede its wait.
 * Once accepted, read retires its ticket on every result, including SMALL_BUFFER.
 * Argument validation and BUSY leave the ticket unchanged; release unused tickets.
 * release retires a reserved ticket; a waiting ticket must be cancelled instead. */
RB_API enum rb_status rb_begin_read(rb_broker *b, uint64_t *ticket);
RB_API enum rb_status rb_read(rb_broker *b, uint64_t ticket,
    void *output, size_t capacity, uint32_t timeout_ms,
    size_t *written, size_t *required);
RB_API enum rb_status rb_cancel(rb_broker *b, uint64_t ticket);
RB_API enum rb_status rb_release_read(rb_broker *b, uint64_t ticket);
RB_API enum rb_status rb_get_health(rb_broker *b, rb_health *out);

/* Close is idempotent, wakes waiting reads, discards queued records with counts,
 * and retires unused tickets. Late publishes reject. No automatic reopening.
 * Invalidate closes on a reported source gap/unknown continuity; zero source-loss
 * count is not proof of lossless hardware. Neither operation drains firmware. */
RB_API enum rb_status rb_close(rb_broker *b);
RB_API enum rb_status rb_invalidate(rb_broker *b, uint64_t source_losses,
    uint32_t reason);

/* TWO-STAGE TEARDOWN: close, stop/join every caller, THEN destroy.
 * destroy checks closed/quiescent state but cannot make a dangling C pointer safe.
 * No new/concurrent calls may enter while destroying. BUSY leaves *owner intact. */
RB_API enum rb_status rb_destroy(rb_broker **owner);

#ifdef __cplusplus
}
#endif
#endif
