#include "alarm_qualification.h"

#include <limits.h>
#include <stddef.h>
#include <stdio.h>

static unsigned int checks = 0U;
static unsigned int failures = 0U;

static void expect(int condition, const char *name)
{
    ++checks;
    if (!condition) {
        ++failures;
        printf("FAIL: %s\n", name);
    }
}

static void seed_result(AlarmQualificationResult *result)
{
    result->qualified = 7;
    result->became_qualified = -8;
    result->on_count = 99U;
}

static int is_seed_result(const AlarmQualificationResult *result)
{
    return result->qualified == 7 && result->became_qualified == -8 &&
           result->on_count == 99U;
}

static void expect_result(const AlarmQualificationState *state,
                          const AlarmQualificationResult *result,
                          unsigned int count, int qualified, int event,
                          const char *name)
{
    expect(state->on_count == count && result->on_count == count &&
           result->qualified == qualified &&
           result->became_qualified == event, name);
}

/* Decision rows are encoded as tables, independent of the routine branches. */
static void test_decision_rows(void)
{
    static const unsigned int counts[11] = {
        1U, 2U, 3U, 4U, 5U, 6U, 7U, 8U, 9U, 10U, 10U
    };
    static const int qualified[11] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1};
    static const int events[11] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0};
    static const int ignored_signals[6] = {INT_MIN, -1, 0, 1, 2, INT_MAX};
    AlarmQualificationState state;
    AlarmQualificationResult result;
    unsigned int old;
    unsigned int i;
    int rc;

    for (old = 0U; old <= 10U; ++old) {
        state.on_count = old;
        seed_result(&result);
        rc = AlarmQualification_Update(&state, 1, 1, &result);
        expect(rc == 0, "valid ON return");
        expect_result(&state, &result, counts[old], qualified[old],
                      events[old], "valid ON decision row");

        state.on_count = old;
        seed_result(&result);
        rc = AlarmQualification_Update(&state, 0, 1, &result);
        expect(rc == 0, "valid OFF return");
        expect_result(&state, &result, 0U, 0, 0, "valid OFF decision row");

        for (i = 0U; i < 6U; ++i) {
            state.on_count = old;
            seed_result(&result);
            rc = AlarmQualification_Update(&state, ignored_signals[i], 0,
                                           &result);
            expect(rc == 0, "invalid sample ignores all signal values");
            expect_result(&state, &result, 0U, 0, 0,
                          "invalid sample decision row");
        }
    }
}

static void test_sequences(void)
{
    AlarmQualificationState state;
    AlarmQualificationResult result;
    unsigned int i;
    int rc;
    int events;

    state.on_count = 0U;
    events = 0;
    for (i = 0U; i < 9U; ++i) {
        rc = AlarmQualification_Update(&state, 1, 1, &result);
        expect(rc == 0, "CHK-01 ON return");
        expect_result(&state, &result, i + 1U, 0, 0, "CHK-01 nine ON");
        events += result.became_qualified;
    }
    rc = AlarmQualification_Update(&state, 1, 1, &result);
    expect(rc == 0, "CHK-02 tenth ON return");
    expect_result(&state, &result, 10U, 1, 1, "CHK-02 tenth ON event");
    events += result.became_qualified;

    for (i = 0U; i < 100U; ++i) {
        rc = AlarmQualification_Update(&state, 1, 1, &result);
        expect(rc == 0, "CHK-03 sustained ON return");
        expect_result(&state, &result, 10U, 1, 0, "CHK-03 saturation");
        events += result.became_qualified;
    }
    expect(events == 1, "exactly one event during sustained ON");

    state.on_count = 9U;
    rc = AlarmQualification_Update(&state, 0, 1, &result);
    expect(rc == 0, "CHK-04 OFF return");
    expect_result(&state, &result, 0U, 0, 0, "CHK-04 OFF reset");
    rc = AlarmQualification_Update(&state, 1, 1, &result);
    expect(rc == 0, "CHK-04 next ON return");
    expect_result(&state, &result, 1U, 0, 0, "CHK-04 next ON");

    state.on_count = 9U;
    rc = AlarmQualification_Update(&state, INT_MIN, 0, &result);
    expect(rc == 0, "CHK-05 invalid sample return");
    expect_result(&state, &result, 0U, 0, 0, "CHK-05 invalid reset");
    rc = AlarmQualification_Update(&state, 1, 1, &result);
    expect(rc == 0, "CHK-05 next ON return");
    expect_result(&state, &result, 1U, 0, 0, "CHK-05 next ON");

    /* ASM-03: both reset kinds allow a fresh qualification event. */
    for (i = 0U; i < 2U; ++i) {
        state.on_count = 10U;
        rc = AlarmQualification_Update(&state, 0, (int)i, &result);
        expect(rc == 0, "ASM-03 reset return");
        events = 0;
        {
            unsigned int j;
            for (j = 0U; j < 10U; ++j) {
                rc = AlarmQualification_Update(&state, 1, 1, &result);
                expect(rc == 0, "ASM-03 requalification return");
                events += result.became_qualified;
            }
        }
        expect_result(&state, &result, 10U, 1, 1,
                      "ASM-03 requalification tenth sample");
        expect(events == 1, "ASM-03 exactly one fresh event");
    }
}

static void test_error_contract(void)
{
    static const int invalid_logicals[4] = {INT_MIN, -1, 2, INT_MAX};
    static const unsigned int state_counts[3] = {9U, 11U, UINT_MAX};
    static const int valid_signals[2] = {0, 1};
    AlarmQualificationState state;
    AlarmQualificationResult result;
    unsigned int i;
    unsigned int j;
    unsigned int k;
    int rc;

    for (j = 0U; j < 3U; ++j) {
        state.on_count = state_counts[j];
        seed_result(&result);
        rc = AlarmQualification_Update(NULL, 2, 2, &result);
        expect(rc == -1 && is_seed_result(&result),
               "NULL state precedence and unchanged output");
        rc = AlarmQualification_Update(&state, 2, 2, NULL);
        expect(rc == -1 && state.on_count == state_counts[j],
               "NULL output precedence and unchanged state");
        rc = AlarmQualification_Update(NULL, 2, 2, NULL);
        expect(rc == -1, "both NULL pointers");

        for (i = 0U; i < 4U; ++i) {
            state.on_count = state_counts[j];
            seed_result(&result);
            rc = AlarmQualification_Update(&state, 1,
                                           invalid_logicals[i], &result);
            expect(rc == -2 && state.on_count == state_counts[j] &&
                   is_seed_result(&result),
                   "invalid sample logical precedence and preservation");
            rc = AlarmQualification_Update(&state, invalid_logicals[i], 1,
                                           &result);
            expect(rc == -2 && state.on_count == state_counts[j] &&
                   is_seed_result(&result),
                   "invalid signal logical precedence and preservation");
        }
    }

    for (j = 1U; j < 3U; ++j) {
        for (k = 0U; k < 2U; ++k) {
            state.on_count = state_counts[j];
            seed_result(&result);
            rc = AlarmQualification_Update(&state, valid_signals[k], 1,
                                           &result);
            expect(rc == -3 && state.on_count == state_counts[j] &&
                   is_seed_result(&result), "invalid state preservation");
        }
        state.on_count = state_counts[j];
        seed_result(&result);
        rc = AlarmQualification_Update(&state, INT_MAX, 0, &result);
        expect(rc == -3 && state.on_count == state_counts[j] &&
               is_seed_result(&result),
               "invalid sample does not silently repair corrupt state");
    }
}

int main(void)
{
    test_decision_rows();
    test_sequences();
    test_error_contract();
    printf("checks=%u failures=%u\n", checks, failures);
    return failures == 0U ? 0 : 1;
}
