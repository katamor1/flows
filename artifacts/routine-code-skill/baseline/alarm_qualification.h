#ifndef ALARM_QUALIFICATION_H
#define ALARM_QUALIFICATION_H

/* PS-RTN-ALM-001 revision 0.1; internal DLL interface, not exported. */
typedef struct {
    unsigned int on_count;
} AlarmQualificationState;

typedef struct {
    int qualified;
    int became_qualified;
    unsigned int on_count;
} AlarmQualificationResult;

/*
 * Initialize state->on_count to zero before the first call.
 * Caller owns valid, writable, nonoverlapping state/result storage and
 * prevents concurrent access to both. Inputs belong to one cycle snapshot.
 * Return 0: state and result updated; -1: NULL; -2: invalid logical input;
 * -3: state count exceeds 10. Errors preserve state and result.
 * Error precedence: -1, -2, -3. Consume result only after return 0.
 * sample_valid == 0 ignores signal_on and resets the count.
 */
int AlarmQualification_Update(
    AlarmQualificationState *state,
    int signal_on,
    int sample_valid,
    AlarmQualificationResult *out_result);

#endif
