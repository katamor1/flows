/* Framework test fixture only; excluded from the distributed skill. */
#include "SampleHold_Update.h"
#include "Project_Sample.h"

#include <stddef.h>

int SampleHold_Update(SampleHoldState *state, int *out_sample)
{
    int sample;
    int status;

    if (state == NULL || out_sample == NULL) {
        return -1;
    }
    status = Project_ReadSample(&sample);
    if (status != 0) {
        return -2;
    }
    state->last_sample = sample;
    state->has_sample = 1;
    *out_sample = sample;
    return 0;
}
