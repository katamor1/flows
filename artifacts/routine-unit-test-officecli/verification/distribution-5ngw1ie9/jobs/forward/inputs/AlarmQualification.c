#include "AlarmQualification.h"

/* PS-RTN-ALM-001 rev 0.1, RTN-ALM-001; generated trial implementation. */
#define ALARM_QUALIFICATION_LIMIT 10U

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

    /* P-01: Reject NULL before accessing either object. */
    if (state == 0 || out_result == 0) {
        return -1;
    }

    /* P-02: Ignore signal_on entirely when the sample is invalid. */
    if (sample_valid != 0 && sample_valid != 1) {
        return -2;
    }
    if (sample_valid == 1 && signal_on != 0 && signal_on != 1) {
        return -2;
    }

    /* P-03: No caller-owned storage has been changed at this point. */
    if (state->on_count > ALARM_QUALIFICATION_LIMIT) {
        return -3;
    }

    /* P-04: Reset, increment, or saturate at ten valid ON samples. */
    old_count = state->on_count;
    new_count = old_count;
    if (sample_valid == 0 || signal_on == 0) {
        new_count = 0U;
    } else if (old_count < ALARM_QUALIFICATION_LIMIT) {
        new_count = old_count + 1U;
    }

    /* P-05: Commit only successful results; no shared static state. */
    qualified = (new_count == ALARM_QUALIFICATION_LIMIT);
    became_qualified = (old_count < ALARM_QUALIFICATION_LIMIT &&
                        new_count == ALARM_QUALIFICATION_LIMIT);
    state->on_count = new_count;
    out_result->qualified = qualified;
    out_result->became_qualified = became_qualified;
    out_result->on_count = new_count;
    return 0;
}
