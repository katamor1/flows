#include "AlarmQualification.h"

/* PS-RTN-ALM-001 revision 0.1: trial specification, internal routine. */
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

    /* P-01: NULL takes priority; neither object is dereferenced here. */
    if (state == 0 || out_result == 0) {
        return -1;
    }

    /* P-02: an invalid sample does not inspect signal_on. */
    if (sample_valid != 0 && sample_valid != 1) {
        return -2;
    }
    if (sample_valid == 1 && signal_on != 0 && signal_on != 1) {
        return -2;
    }

    /* P-03: every error returns before either object is written. */
    if (state->on_count > 10u) {
        return -3;
    }

    /* P-04: reset on invalid/OFF, otherwise count with saturation. */
    old_count = state->on_count;
    if (sample_valid == 0 || signal_on == 0) {
        new_count = 0u;
    } else if (old_count < 10u) {
        new_count = old_count + 1u;
    } else {
        new_count = 10u;
    }

    /* P-05: only the transition into 10 produces a new event. */
    qualified = (new_count == 10u);
    became_qualified = (old_count < 10u && new_count == 10u);
    state->on_count = new_count;
    out_result->qualified = qualified;
    out_result->became_qualified = became_qualified;
    out_result->on_count = new_count;
    return 0;
}
