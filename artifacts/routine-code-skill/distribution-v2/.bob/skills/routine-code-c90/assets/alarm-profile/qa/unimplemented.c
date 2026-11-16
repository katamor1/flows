#include "AlarmQualification.h"

/* Deliberately unimplemented baseline used before AI implementation. */
int AlarmQualification_Update(
    AlarmQualificationState *state,
    int signal_on,
    int sample_valid,
    AlarmQualificationResult *out_result)
{
    (void)state;
    (void)signal_on;
    (void)sample_valid;
    (void)out_result;
    return -99;
}
