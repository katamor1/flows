# UT PoC fixed contract 0.1.0

実施元: docs/superpowers/plans/2026-11-15-unit-test-spec-poc.md。新規パッケージのみ変更する。既存仕様・ソース・配布物は不変。

## Canonical JSON

Top-level keys: schema_version, document, target, summary, environment, assumptions, cases, families, static_checks, coverage, open_issues.

- schema_version: "0.1.0".
- document: id="UTS-RTN-ALM-001", title, revision="0.1", date="2026-11-15", status="draft_trial", status_label="試作仕様 要件確認前", routine_id="RTN-ALM-001", routine_name="AlarmQualification_Update", template_id="unit-test-spec-v01", author. All strings.
- target: program_spec_sha256, source_sha256, header_sha256. Exact current input hashes from plan.
- summary: string. environment: nonempty array of strings. assumptions: original [{id,text}]. open_issues: original [{id,owner,decision}].
- cases: [{id,title,purpose,spec_refs:[str],initial:[initial_object],steps:[step],judgment:str}]. IDs UT-ALM-001..016 per plan, add if justified.
- initial_object: {instance:"A" or "B", state_count:str, state_fill_byte:"0xA5", result_fill_byte:"0x5A", result:{qualified:str,became_qualified:str,on_count:str}}. Integers use decimal strings or UINT_MAX. Result values are valid ints; initialize field values after filling bytes.
- step: {id:"S01",instance:"A" or "B",state_pointer:"object" or "null",result_pointer:"object" or "null",signal_on:str,sample_valid:str,repeat:int,expected:{return_code:int,state_count:str,out_count:str,qualified:str,became_qualified:str,preservation:"none" or "all_valid_bytes"},note:str}.
- Input tokens: signed decimal or INT_MIN/INT_MAX/UINT_MAX. Expected counts: decimal, UINT_MAX, iteration, preserve. iteration means k=1..repeat, at each call. Qualified/event: "0", "1", "preserve". For error use preserve and all_valid_bytes. Only return_code integer.
- families: [{id,title,spec_refs:[str],mode:"product" or "sequence",dimensions:[{name:str,values:[str]}],sequence_length:int (0 for product),combination_count:int,call_count:int,initial:str,enumeration:str,method:str,expected_rule:str,examples:[str]}]. 4 families from plan with counts88/24/6/177147, calls88/24/6/1948617. No eval.
- static_checks: [{id:"SR-ALM-001",title,spec_refs:[str],method:str,criterion:str,boundary:str}]. All not executed; no pass field.
- coverage: [{spec_ref:str,method:"test"/"review"/"test_and_review"/"caller"/"out_of_scope",item_ids:[str],rationale:str}]. No duplicate spec_ref. Covers ASM01..03, P01..05, CON01..04 plus /behavior/decision_rows, /interface/return_codes, /behavior/postconditions, /behavior/timing_semantics, /interface/preconditions. References resolve to exact IDs or JSON pointers of frozen program spec. Code references are target hashes + routine name.

## Renderer view shared with template

Retain old OfficeCLI renderer machinery; replace context(). All below are scalar strings inside repeated table rows; table caption repeat:view.NAME, 1 header+1 prototype row, no nested tables.

- view.target_summary (scalar): function, input hashes wrapped at32chars, draft status, case/family counts. view.not_executed (scalar): explicit no execution statement.
- view.environment rows {text}
- view.assumptions rows {id,text}
- view.case_index rows {id,title,purpose,refs,status}; status always 未実施
- view.case_steps rows {case_step,inputs,expected,refs}. One row per canonical step, repeat stays compact. First step includes full initial objects and fill-byte prescription. Include purpose/judgment in case index purpose or step expected. All canonical information must appear in document (raw structured formatting may be condensed with legend).
- view.families rows {id,definition,oracle,refs}. Include title/mode/dimensions/sequence length/counts/initial/enumeration/method/examples; no expansion of177k rows.
- view.static_checks rows {id,method,criterion,refs}; include boundary and 未実施.
- view.coverage rows {ref,method,items,reason}
- view.open_issues rows {id,owner,decision}
- Root scalar tokens can use document fields, summary, view.target_summary, view.not_executed. Footer PAGE/NUMPAGES fields and header document ID.

## Runtime and job paths

Skill root packages/routine-unit-test-officecli/skills/routine-unit-test-spec.
New-job --code-job prototypes/routine-code-poc: copy its input/spec.json as inputs/program-spec.json; src/AlarmQualification.c and include/AlarmQualification.h as inputs/AlarmQualification.c/.h; generation-record.json. Check hashes. Copy assets/examples/alarm_unit_test.json to source/unit-test-spec.json.
new-job makes input-lock.json + package-lock.json + records/execution-record.json with every case/family/static ID not_executed and no historical pass.
validate(data,schema,program_spec) is _contract public API, return data. Root implements _contract; agent engine must call with frozen program spec. Root also supplies execution_record(data) and validate_execution(record,data), traceability(data).
render copies source to renders/run/unit-test-spec.json; record input hashes in manifest; schema/template/renderer pins. Job outside package. No overwrite or partial success publish. OfficeCLI always OFFICECLI_NO_AUTO_RESIDENT=1 and finally close. Environment paths use explicit CLI args.

## Work division

Author writes assets/examples/alarm_unit_test.json only plus maintenance/authoring-note.md. Template agent writes assets/templates/unit-test-spec-v01.docx and maintenance/template-build/* only; calls document-operation marker once immediately before first OfficeCLI create/edit. Engine agent writes scripts/utflow.py, _renderer.py, tools/release.py, runtime skill/readme/reference. Root writes _contract.py/schema/tests, integrates and seals after other resources stable.
