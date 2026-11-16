#include "AlarmQualification.h"

#include <limits.h>
#include <stdio.h>
#include <string.h>

static unsigned long checks = 0UL;
static unsigned long failures = 0UL;

static int expect_update(const char *case_id,
                         AlarmQualificationState *state,
                         int signal_on, int sample_valid,
                         unsigned int expected_count,
                         int expected_qualified, int expected_event)
{
    AlarmQualificationResult result;
    int status;

    memset(&result, 0xa5, sizeof result);
    status = AlarmQualification_Update(state, signal_on, sample_valid, &result);
    ++checks;
    if (status != 0 || state->on_count != expected_count ||
        result.on_count != expected_count ||
        result.qualified != expected_qualified ||
        result.became_qualified != expected_event) {
        ++failures;
        printf("FAIL %s: rc=%d state=%u out=(%u,%d,%d), expected=(%u,%d,%d)\n",
               case_id, status, state->on_count, result.on_count,
               result.qualified, result.became_qualified, expected_count,
               expected_qualified, expected_event);
        return 0;
    }
    return 1;
}

static int expect_error(const char *case_id, unsigned int initial_count,
                        int signal_on, int sample_valid,
                        int null_state, int null_result, int expected_status)
{
    AlarmQualificationState state;
    AlarmQualificationResult result;
    unsigned char saved_state[sizeof state];
    unsigned char saved_result[sizeof result];
    int status;

    memset(&state, 0xa5, sizeof state);
    memset(&result, 0x5a, sizeof result);
    state.on_count = initial_count;
    result.qualified = 1;
    result.became_qualified = 1;
    result.on_count = 10U;
    memcpy(saved_state, &state, sizeof state);
    memcpy(saved_result, &result, sizeof result);
    status = AlarmQualification_Update(null_state ? NULL : &state,
                                       signal_on, sample_valid,
                                       null_result ? NULL : &result);
    ++checks;
    if (status != expected_status ||
        memcmp(saved_state, &state, sizeof state) != 0 ||
        memcmp(saved_result, &result, sizeof result) != 0) {
        ++failures;
        printf("FAIL %s: rc=%d expected=%d; all initialized bytes must remain unchanged\n",
               case_id, status, expected_status);
        return 0;
    }
    return 1;
}

static void test_spec_examples_and_rearm(void)
{
    AlarmQualificationState state;
    unsigned int i;

    state.on_count = 0U;
    for (i = 1U; i <= 9U; ++i) {
        if (!expect_update("CHK-01", &state, 1, 1, i, 0, 0)) {
            return;
        }
    }
    if (!expect_update("CHK-02", &state, 1, 1, 10U, 1, 1)) {
        return;
    }
    for (i = 0U; i < 100U; ++i) {
        if (!expect_update("CHK-03", &state, 1, 1, 10U, 1, 0)) {
            return;
        }
    }
    if (!expect_update("REARM-OFF", &state, 0, 1, 0U, 0, 0)) {
        return;
    }
    for (i = 1U; i <= 9U; ++i) {
        if (!expect_update("REARM-OFF-PREFIX", &state, 1, 1, i, 0, 0)) {
            return;
        }
    }
    if (!expect_update("REARM-AFTER-OFF", &state, 1, 1, 10U, 1, 1) ||
        !expect_update("CHK-04-RESET", &state, 0, 1, 0U, 0, 0)) {
        return;
    }
    for (i = 1U; i <= 9U; ++i) {
        if (!expect_update("CHK-04-PREFIX", &state, 1, 1, i, 0, 0)) {
            return;
        }
    }
    if (!expect_update("CHK-04-OFF", &state, 0, 1, 0U, 0, 0) ||
        !expect_update("CHK-04", &state, 1, 1, 1U, 0, 0)) {
        return;
    }
    for (i = 2U; i <= 9U; ++i) {
        if (!expect_update("CHK-05-PREFIX", &state, 1, 1, i, 0, 0)) {
            return;
        }
    }
    if (!expect_update("CHK-05-INVALID", &state, INT_MIN, 0, 0U, 0, 0) ||
        !expect_update("CHK-05", &state, 1, 1, 1U, 0, 0)) {
        return;
    }
    for (i = 2U; i <= 9U; ++i) {
        if (!expect_update("REARM-INVALID-PREFIX", &state, 1, 1, i, 0, 0)) {
            return;
        }
    }
    if (!expect_update("REARM-AFTER-INVALID", &state, 1, 1, 10U, 1, 1) ||
        !expect_update("REARM-QUALIFIED-INVALID", &state, INT_MAX, 0,
                       0U, 0, 0)) {
        return;
    }
    for (i = 1U; i <= 9U; ++i) {
        if (!expect_update("REARM-FINAL-PREFIX", &state, 1, 1, i, 0, 0)) {
            return;
        }
    }
    (void)expect_update("REARM-FINAL", &state, 1, 1, 10U, 1, 1);
}

static void test_transition_table(void)
{
    static const unsigned int next_on[11] = {
        1U, 2U, 3U, 4U, 5U, 6U, 7U, 8U, 9U, 10U, 10U
    };
    static const int qualified_on[11] = {
        0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1
    };
    static const int event_on[11] = {
        0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0
    };
    static const int ignored_signals[6] = {
        INT_MIN, -1, 0, 1, 2, INT_MAX
    };
    AlarmQualificationState state;
    unsigned int old_count;
    unsigned int i;

    for (old_count = 0U; old_count <= 10U; ++old_count) {
        state.on_count = old_count;
        if (!expect_update("TABLE-ON", &state, 1, 1,
                           next_on[old_count], qualified_on[old_count],
                           event_on[old_count])) {
            return;
        }
        state.on_count = old_count;
        if (!expect_update("TABLE-OFF", &state, 0, 1, 0U, 0, 0)) {
            return;
        }
        for (i = 0U; i < 6U; ++i) {
            state.on_count = old_count;
            if (!expect_update("TABLE-INVALID-IGNORES-SIGNAL", &state,
                               ignored_signals[i], 0, 0U, 0, 0)) {
                return;
            }
        }
    }
}

static void test_errors(void)
{
    static const int bad_bools[4] = { INT_MIN, -1, 2, INT_MAX };
    static const unsigned int bad_counts[2] = { 11U, UINT_MAX };
    unsigned int i;
    unsigned int j;

    if (!expect_error("ERR-NULL-STATE", 9U, 1, 1, 1, 0, -1) ||
        !expect_error("ERR-NULL-RESULT", 9U, 1, 1, 0, 1, -1) ||
        !expect_error("ERR-NULL-BOTH", 9U, 1, 1, 1, 1, -1) ||
        !expect_error("PRIORITY-NULL-STATE", 11U, 2, 2, 1, 0, -1) ||
        !expect_error("PRIORITY-NULL-RESULT", 11U, 2, 2, 0, 1, -1)) {
        return;
    }
    for (i = 0U; i < 4U; ++i) {
        if (!expect_error("ERR-SAMPLE-VALID", 9U, 1, bad_bools[i],
                          0, 0, -2) ||
            !expect_error("ERR-SIGNAL-ON", 9U, bad_bools[i], 1,
                          0, 0, -2) ||
            !expect_error("PRIORITY-INPUT-BEFORE-STATE", 11U, 1,
                          bad_bools[i], 0, 0, -2) ||
            !expect_error("PRIORITY-SIGNAL-BEFORE-STATE", UINT_MAX,
                          bad_bools[i], 1, 0, 0, -2)) {
            return;
        }
    }
    for (i = 0U; i < 2U; ++i) {
        if (!expect_error("ERR-STATE-ON", bad_counts[i], 1, 1,
                          0, 0, -3) ||
            !expect_error("ERR-STATE-OFF", bad_counts[i], 0, 1,
                          0, 0, -3)) {
            return;
        }
        for (j = 0U; j < 4U; ++j) {
            if (!expect_error("ERR-STATE-INVALID-IGNORES-SIGNAL",
                              bad_counts[i], bad_bools[j], 0,
                              0, 0, -3)) {
                return;
            }
        }
    }
}

static void test_independent_instances(void)
{
    AlarmQualificationState a;
    AlarmQualificationState b;
    unsigned int i;

    a.on_count = 0U;
    b.on_count = 0U;
    for (i = 1U; i <= 9U; ++i) {
        if (!expect_update("INSTANCE-A", &a, 1, 1, i, 0, 0) ||
            !expect_update("INSTANCE-B-OFF", &b, 0, 1, 0U, 0, 0)) {
            return;
        }
    }
    if (!expect_update("INSTANCE-A-EVENT", &a, 1, 1, 10U, 1, 1)) {
        return;
    }
    for (i = 1U; i <= 9U; ++i) {
        if (!expect_update("INSTANCE-B", &b, 1, 1, i, 0, 0) ||
            !expect_update("INSTANCE-A-SATURATED", &a, 1, 1,
                           10U, 1, 0)) {
            return;
        }
    }
    if (!expect_update("INSTANCE-B-EVENT", &b, 1, 1, 10U, 1, 1) ||
        !expect_update("INSTANCE-A-RESET", &a, 0, 1, 0U, 0, 0)) {
        return;
    }
    (void)expect_update("INSTANCE-B-STILL-QUALIFIED", &b, 1, 1,
                        10U, 1, 0);
}

/* Oracle: inspect the input history, without advancing a counter model. */
static unsigned int history_suffix(const unsigned int *history,
                                   unsigned int length)
{
    unsigned int n;

    n = 0U;
    while (n < 10U && n < length && history[length - n - 1U] == 0U) {
        ++n;
    }
    return n;
}

static void test_all_eleven_sample_sequences(void)
{
    AlarmQualificationState state;
    unsigned int history[11];
    unsigned long sequence;
    unsigned long digits;
    unsigned int i;
    unsigned int previous_suffix;
    unsigned int suffix;
    int signal_on;
    int sample_valid;

    for (sequence = 0UL; sequence < 177147UL; ++sequence) {
        digits = sequence;
        for (i = 0U; i < 11U; ++i) {
            history[i] = (unsigned int)(digits % 3UL);
            digits /= 3UL;
        }
        state.on_count = 0U;
        for (i = 0U; i < 11U; ++i) {
            previous_suffix = history_suffix(history, i);
            suffix = history_suffix(history, i + 1U);
            signal_on = history[i] == 0U ? 1 : 0;
            sample_valid = history[i] == 2U ? 0 : 1;
            if (!expect_update("ALL-11-SAMPLE-SEQUENCES", &state,
                               signal_on, sample_valid, suffix,
                               suffix == 10U,
                               suffix == 10U && previous_suffix < 10U)) {
                printf("Sequence index=%lu, sample index=%u (zero-based)\n",
                       sequence, i);
                return;
            }
        }
    }
}

static void report_group(const char *case_id, unsigned long before)
{
    printf("%s: %lu checks\n", case_id, checks - before);
}

int main(void)
{
    unsigned long before;

    before = checks;
    test_spec_examples_and_rearm();
    report_group("CHK-01..05 / REARM", before);
    before = checks;
    test_transition_table();
    report_group("ALL-VALID-STATE-TRANSITIONS", before);
    before = checks;
    test_errors();
    report_group("CHK-06 / ERROR-PRIORITY / NO-WRITES", before);
    before = checks;
    test_independent_instances();
    report_group("INDEPENDENT-INSTANCES", before);
    before = checks;
    test_all_eleven_sample_sequences();
    report_group("177147 ELEVEN-SAMPLE-SEQUENCES", before);
    printf("TOTAL: %lu checks, %lu failures\n", checks, failures);
    return failures == 0UL ? 0 : 1;
}

