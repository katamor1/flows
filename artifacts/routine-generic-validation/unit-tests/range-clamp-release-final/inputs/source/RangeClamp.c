#include "RangeClamp.h"

/* The caller supplies lower <= upper. */
int RangeClamp(int value, int lower, int upper)
{
    if (value < lower) {
        return lower;
    }

    if (value > upper) {
        return upper;
    }

    return value;
}
