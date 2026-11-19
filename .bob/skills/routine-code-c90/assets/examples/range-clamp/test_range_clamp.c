#include "RangeClamp.h"

#include <limits.h>
#include <stdio.h>

int main(void)
{
    /* Expected values are literal acceptance cases, not a second clamp algorithm. */
    static const int cases[][4] = {
        {-8, -3, 4, -3},
        {-3, -3, 4, -3},
        {-2, -3, 4, -2},
        {0, -3, 4, 0},
        {2, -3, 4, 2},
        {4, -3, 4, 4},
        {9, -3, 4, 4},
        {7, 7, 7, 7},
        {-9, 7, 7, 7},
        {99, 7, 7, 7},
        {INT_MIN, INT_MIN, INT_MAX, INT_MIN},
        {INT_MAX, INT_MIN, INT_MAX, INT_MAX},
        {0, INT_MIN, INT_MAX, 0},
        {INT_MIN, -1, INT_MAX, -1},
        {INT_MAX, INT_MIN, 1, 1}
    };
    unsigned int i;
    int actual;

    for (i = 0U; i < sizeof cases / sizeof cases[0]; ++i) {
        actual = RangeClamp(cases[i][0], cases[i][1], cases[i][2]);
        if (actual != cases[i][3]) {
            printf("FAIL RangeClamp case %u: actual=%d expected=%d\n",
                   i, actual, cases[i][3]);
            return 1;
        }
    }
    printf("RangeClamp: 15 literal cases passed\n");
    return 0;
}
