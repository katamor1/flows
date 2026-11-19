#ifndef PROJECT_TEST_MOCK_H
#define PROJECT_TEST_MOCK_H

/* Test harness controls; never included by production implementation. */
void ProjectMock_Reset(int status, int sample);
int ProjectMock_ReadCount(void);

#endif
