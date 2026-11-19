# RangeClamp specification to implementation

Input: PS-RTN-CLAMP-001 revision 0.1, RTN-CLAMP-001, schema 0.2.0.
Status: `draft_trial` (trial specification, before requirements confirmation and human approval).
Canonical input SHA-256: `403f5e9255c9bcb5205d1dfe44e1af3999f8bde5194bc8138214e83c0feadcf7`.

The implementation was newly authored by Codex from the canonical JSON and its frozen header. No earlier DUT, fixture implementation, baseline C, or independent test source was read to derive it. IBM Bob was not executed. The generation record binds the source and this mapping to the input; QA records bind the tested snapshot and compiler commands.

| Requirement or specification location | Implementation in `src/RangeClamp.c`, function `RangeClamp` | Verification or responsibility |
| --- | --- | --- |
| REQ-CLAMP-INCLUSIVE; overview.source_requirement | Ordered lower comparison, upper comparison, then original value | Supplied independent profile and O0/O2 host execution; results in `qa/r001/verification.json` |
| CLAMP-STEP-LOWER; CLAMP-EX-LOWER | `value < lower` returns `lower` | Direct contract review; supplied host tests |
| CLAMP-STEP-UPPER; CLAMP-EX-UPPER | Following the lower branch, `value > upper` returns `upper` | Direct contract review; supplied host tests |
| CLAMP-STEP-PRESERVE; CLAMP-EX-INSIDE; CLAMP-EX-EQUAL | Final `return value` preserves in-range values, including equal bounds | Direct contract review; supplied host tests |
| interface.prototype, parameters, return_codes | Header declares and source defines `int RangeClamp(int value, int lower, int upper)` | Frozen header; strict C90 compilation |
| CLAMP-PRE-ORDER; interface.preconditions | Comment documents `lower <= upper`; no invented error handling | Caller owns this precondition. Behavior for reversed bounds is outside the specified contract and is not an acceptance claim. |
| CLAMP-C90 | Two `if` statements and returns; no external calls, allocation, loops or recursion | Source review; strict C90 build; object symbol inspection |
| CLAMP-OVERFLOW | Direct comparisons only; no subtraction or other arithmetic | Source review; works without assumptions about the width of `int` |
| behavior.state_fields; postconditions | Arguments passed by value; no stored state, memory writes or resource access | Source review; object inspection |
| behavior.timing_semantics | At most two comparisons and one return on any valid call | Bounded source path only; no RTOS timing or WCET measurement claimed |

All specified routine behavior is implemented for the stated caller precondition. There are no defined error returns to add. No state, pointer ownership, shared resource, or platform API is introduced. Profile assets remain fixed and are used as supplied; specific test coverage is established by their recorded execution rather than inferred from this table.

Formal target compiler compatibility, DLL ABI/export/calling convention, RTOS integration, and real-target WCET remain outside the supplied contract and this host verification. Trial status is preserved. The handoff must carry these limits and leave expected-result ownership with the independently supplied project tests and their maintainer.
