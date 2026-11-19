#include "Project_Sample.h"
#include "Project_TestMock.h"

#if PROJECT_SAMPLE_FIXTURE != 1
#error The mock is permitted only with the fixture profile.
#endif

static int next_status;
static int next_sample;
static int read_count;

void ProjectMock_Reset(int status, int sample)
{
    next_status = status;
    next_sample = sample;
    read_count = 0;
}

int ProjectMock_ReadCount(void)
{
    return read_count;
}

int Project_ReadSample(int *out_sample)
{
    ++read_count;
    /* Also dirty the local result on failure to test transactional writes. */
    *out_sample = next_sample;
    return next_status;
}
