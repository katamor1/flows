#ifndef SAMPLE_HOLD_UPDATE_H
#define SAMPLE_HOLD_UPDATE_H
typedef struct { int last_sample; int has_sample; } SampleHoldState;
int SampleHold_Update(SampleHoldState *state, int *out_sample);
#endif
