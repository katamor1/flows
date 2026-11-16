#include "alarm_qualification.h"

#include <stddef.h>

int AlarmQualification_Update(
    AlarmQualificationState *state,
    int signal_on,
    int sample_valid,
    AlarmQualificationResult *out_result)
{
    unsigned int old_count;
    unsigned int new_count;
    int qualified;
    int became_qualified;

    /* P-01: do not inspect the other pointer when either pointer is NULL. */
    if (state == NULL || out_result == NULL) {
        return -1;
    }

    /* P-02: an invalid sample does not inspect signal_on. */
    if (sample_valid != 0 && sample_valid != 1) {
        return -2;
    }
    if (sample_valid == 1 && signal_on != 0 && signal_on != 1) {
        return -2;
    }

    /* P-03: every failure precedes every write. */
    if (state->on_count > 10U) {
        return -3;
    }

    /* P-04: first ON is sample one; the count saturates at ten. */
    old_count = state->on_count;
    if (sample_valid == 0 || signal_on == 0) {
        new_count = 0U;
    } else if (old_count < 10U) {
        new_count = old_count + 1U;
    } else {
        new_count = 10U;
    }

    /* P-05: only the transition into ten emits the event. */
    qualified = (new_count == 10U);
    became_qualified = (old_count < 10U && new_count == 10U);

    state->on_count = new_count;
    out_result->qualified = qualified;
    out_result->became_qualified = became_qualified;
    out_result->on_count = new_count;
    return 0;
}
