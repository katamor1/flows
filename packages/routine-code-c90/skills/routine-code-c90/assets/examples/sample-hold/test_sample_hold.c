#include "SampleHold_Update.h"
#include "Project_TestMock.h"

#include <limits.h>
#include <stddef.h>
#include <stdio.h>

#if PROJECT_SAMPLE_FIXTURE != 1
#error Missing fixture define.
#endif

#define CHECK(expr) do { if (!(expr)) { printf("FAIL line %d\n", __LINE__); return 1; } } while (0)

int main(void)
{
    SampleHoldState first;
    SampleHoldState second;
    int result;
    int status;

    first.last_sample = 12;
    first.has_sample = 0;
    second.last_sample = -8;
    second.has_sample = 0;
    result = 51;

    ProjectMock_Reset(0, 23);
    status = SampleHold_Update(NULL, &result);
    CHECK(status == -1 && result == 51 && ProjectMock_ReadCount() == 0);
    status = SampleHold_Update(&first, NULL);
    CHECK(status == -1 && first.last_sample == 12 && first.has_sample == 0);
    CHECK(ProjectMock_ReadCount() == 0);
    status = SampleHold_Update(NULL, NULL);
    CHECK(status == -1 && ProjectMock_ReadCount() == 0);

    status = SampleHold_Update(&first, &result);
    CHECK(status == 0 && result == 23);
    CHECK(first.last_sample == 23 && first.has_sample == 1);
    CHECK(second.last_sample == -8 && second.has_sample == 0);
    CHECK(ProjectMock_ReadCount() == 1);

    ProjectMock_Reset(7, -99);
    status = SampleHold_Update(&first, &result);
    CHECK(status == -2 && result == 23);
    CHECK(first.last_sample == 23 && first.has_sample == 1);
    CHECK(ProjectMock_ReadCount() == 1);

    ProjectMock_Reset(-5, INT_MAX);
    status = SampleHold_Update(&second, &result);
    CHECK(status == -2 && result == 23);
    CHECK(second.last_sample == -8 && second.has_sample == 0);
    CHECK(ProjectMock_ReadCount() == 1);

    ProjectMock_Reset(0, INT_MIN);
    status = SampleHold_Update(&second, &result);
    CHECK(status == 0 && result == INT_MIN);
    CHECK(second.last_sample == INT_MIN && second.has_sample == 1);
    CHECK(first.last_sample == 23 && first.has_sample == 1);
    CHECK(ProjectMock_ReadCount() == 1);

    ProjectMock_Reset(0, INT_MAX);
    status = SampleHold_Update(&first, &result);
    CHECK(status == 0 && result == INT_MAX);
    CHECK(first.last_sample == INT_MAX && first.has_sample == 1);
    CHECK(ProjectMock_ReadCount() == 1);

    printf("SampleHold_Update: literal state/API cases passed\n");
    return 0;
}
