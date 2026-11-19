/* Framework test fixture only; excluded from the distributed skill. */
#include "RangeClamp.h"

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
