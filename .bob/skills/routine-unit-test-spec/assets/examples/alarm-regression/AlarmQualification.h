#ifndef ALARM_QUALIFICATION_H
#define ALARM_QUALIFICATION_H

/* PS-RTN-ALM-001 revision 0.1; draft trial, internal DLL routine. */
/* Caller owns, initializes and exclusively accesses both objects. */
/* State and result storage must not overlap any concurrent call. */
typedef struct {
    unsigned int on_count;
} AlarmQualificationState;

typedef struct {
    int qualified;
    int became_qualified;
    unsigned int on_count;
} AlarmQualificationResult;

/* Initial state.on_count: 0. Valid range: 0..10. */
/* Valid samples: signal_on is 0 or 1; invalid samples ignore it. */
/* Returns 0, -1 (NULL), -2 (input), -3 (state), in that priority. */
/* Only a return value of 0 commits state/result; consume only then. */
/* Caller detects lost cycles and supplies sample_valid=0 to reset. */
int AlarmQualification_Update(
    AlarmQualificationState *state,
    int signal_on,
    int sample_valid,
    AlarmQualificationResult *out_result);

#endif
