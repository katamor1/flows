"""Fixed trial profile. No routine execution or expression evaluation.

Checks shape/references/cardinality, not the correctness of prose oracles.
Unknown schema keywords fail closed; this is not a full JSON Schema engine.
"""
import math
import re

PROFILE = {
    'program_spec_sha256': '097b1185e284c17805b51c92dd821d1bec64f55d0ce1781c2c1fb369239b4265',
    'source_sha256': 'e2b910d6aaf0932a19c3f287cb6513a5193a9e365435c5876a29cd7684683bee',
    'header_sha256': '3f8799a676201b23a2fa96e7eddfaf4fe99a67429edb2e460571197a238bcf00'
}
SCHEMA_KEYS = {'$schema', '$id', 'title', 'description', 'type', 'properties',
               'required', 'additionalProperties', 'items', 'minItems',
               'minLength', 'minimum', 'const'}
REQUIRED_REFS = ([f'ASM-{n:02}' for n in range(1, 4)] + [f'P-{n:02}' for n in range(1, 6)] +
                 [f'CON-{n:02}' for n in range(1, 5)] +
                 ['/behavior/decision_rows', '/interface/return_codes',
                  '/behavior/postconditions', '/behavior/timing_semantics', '/interface/preconditions'])
DECIMAL = re.compile(r'-?(0|[1-9][0-9]{0,9})\Z')
SYMBOLS = {'INT_MIN', 'INT_MAX', 'UINT_MAX'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def resolve(data, path):
    for part in path.split('.'):
        data = data[part]
    return data


def validate_shape(data, schema, path='$'):
    require(not set(schema) - SCHEMA_KEYS, f'{path}: unsupported schema keywords')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int}
    expected = schema.get('type')
    if expected:
        require(expected in types, f'{path}: unsupported schema type')
        require(type(data) is types[expected], f'{path}: expected {expected}')
    if 'const' in schema:
        require(data == schema['const'], f'{path}: constant mismatch')
    if isinstance(data, dict):
        for name in schema.get('required', []):
            require(name in data, f'{path}.{name}: required')
        for name, value in data.items():
            if name in schema.get('properties', {}):
                validate_shape(value, schema['properties'][name], path + '.' + name)
            else:
                require(schema.get('additionalProperties') is not False, f'{path}.{name}: unknown field')
    elif isinstance(data, list):
        require(len(data) >= schema.get('minItems', 0), f'{path}: too few items')
        for index, value in enumerate(data):
            validate_shape(value, schema['items'], f'{path}[{index}]')
    elif isinstance(data, str):
        require(len(data) >= schema.get('minLength', 0), f'{path}: empty string')
    elif type(data) is int:
        require(data >= schema.get('minimum', data), f'{path}: below minimum')


def collect_ids(value):
    result = set()
    if isinstance(value, dict):
        if isinstance(value.get('id'), str):
            result.add(value['id'])
        for child in value.values():
            result.update(collect_ids(child))
    elif isinstance(value, list):
        for child in value:
            result.update(collect_ids(child))
    return result


def pointer_exists(data, pointer):
    try:
        for raw in pointer.split('/')[1:]:
            require(not re.search(r'~(?![01])', raw), 'Invalid JSON pointer escape')
            part = raw.replace('~1', '/').replace('~0', '~')
            if isinstance(data, list):
                require(re.fullmatch(r'0|[1-9][0-9]*', part) is not None, 'Invalid array index')
                data = data[int(part)]
            else:
                data = data[part]
        return True
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def token(value, expected=False, flag=False):
    allowed = {'preserve'} if expected else set(SYMBOLS)
    if expected and not flag:
        allowed.update({'iteration', 'UINT_MAX'})
    if flag:
        return type(value) is str and value in allowed | {'0', '1'}
    return type(value) is str and (value in allowed or DECIMAL.fullmatch(value) is not None)


def unique(values, label):
    require(len(values) == len(set(values)), 'Duplicate ' + label)


def all_items(data):
    return [item for name in ('cases', 'families', 'static_checks') for item in data[name]]


def validate(data, schema, program_spec):
    validate_shape(data, schema)
    require(data['target'] == PROFILE, 'Target input hashes do not match the fixed trial profile')
    require(program_spec['document']['id'] == 'PS-RTN-ALM-001' and
            program_spec['document']['routine_name'] == 'AlarmQualification_Update' and
            program_spec['behavior']['threshold'] == 10, 'Unsupported program specification')
    require(data['assumptions'] == program_spec['trial_assumptions'], 'Trial assumptions must be preserved')
    require(data['open_issues'] == program_spec['open_issues'], 'Open issues must be preserved')
    spec_ids = collect_ids(program_spec) | {program_spec['overview']['requirement_id'], program_spec['document']['routine_id']}

    def ref_valid(ref):
        return ref in spec_ids or (ref.startswith('/') and pointer_exists(program_spec, ref))

    items = all_items(data)
    item_ids = [x['id'] for x in items]
    unique(item_ids, 'case/family/static IDs')
    for section, prefix in (('cases', 'UT-ALM-'), ('families', 'FAM-ALM-'), ('static_checks', 'SR-ALM-')):
        for item in data[section]:
            require(re.fullmatch(re.escape(prefix) + r'[0-9]{3}', item['id']) is not None, 'Invalid item ID: ' + item['id'])
            unique(item['spec_refs'], 'spec refs in ' + item['id'])
            for ref in item['spec_refs']:
                require(ref_valid(ref), 'Unknown specification reference: ' + ref)
    for case in data['cases']:
        names = [x['instance'] for x in case['initial']]
        unique(names, 'initial instances')
        for initial in case['initial']:
            require(initial['instance'] in {'A', 'B'}, 'Unknown initial instance')
            require(token(initial['state_count']) and not initial['state_count'].startswith('-'), 'Invalid initial count')
            require(token(initial['result']['on_count']), 'Invalid initial result count')
            for flag in ('qualified', 'became_qualified'):
                require(initial['result'][flag] in {'0', '1'}, 'Invalid initial result flag')
        unique([x['id'] for x in case['steps']], 'step IDs')
        for step in case['steps']:
            require(re.fullmatch(r'S[0-9]{2}', step['id']) is not None, 'Invalid step ID')
            require(step['instance'] in names, 'Step refers to unknown instance')
            require(step['state_pointer'] in {'object', 'null'} and step['result_pointer'] in {'object', 'null'}, 'Unsupported pointer condition')
            require(token(step['signal_on']) and token(step['sample_valid']), 'Input must be a literal or approved C symbol')
            require(step['repeat'] <= 1000, 'Too many repeats for this document profile')
            exp = step['expected']
            require(exp['return_code'] in {0, -1, -2, -3}, 'Unsupported return code')
            for field in ('state_count', 'out_count'):
                require(token(exp[field], expected=True), 'Invalid expected count token')
            for field in ('qualified', 'became_qualified'):
                require(token(exp[field], expected=True, flag=True), 'Invalid expected flag token')
            if exp['return_code'] == 0:
                require(step['state_pointer'] == step['result_pointer'] == 'object', 'Successful call requires objects')
                require(exp['preservation'] == 'none', 'Success must declare updates')
                require('preserve' not in [exp[x] for x in ('state_count', 'out_count', 'qualified', 'became_qualified')], 'Successful values must be explicit')
                require(exp['state_count'] == exp['out_count'], 'Successful state/result counts must agree')
            else:
                require(exp['preservation'] == 'all_valid_bytes', 'Errors require full valid-storage preservation')
                require(all(exp[x] == 'preserve' for x in ('state_count', 'out_count', 'qualified', 'became_qualified')), 'Errors must preserve all result fields')
    require(len(data['families']) == 4, 'This profile defines exactly four parameter families')
    sizes = {'FAM-ALM-001': (88, 88), 'FAM-ALM-002': (24, 24), 'FAM-ALM-003': (6, 6), 'FAM-ALM-004': (177147, 1948617)}
    for family in data['families']:
        unique([d['name'] for d in family['dimensions']], 'family dimension names')
        for dimension in family['dimensions']:
            unique(dimension['values'], 'dimension values')
        if family['mode'] == 'product':
            require(family['sequence_length'] == 0, 'Product family cannot have a sequence length')
            size = math.prod(len(d['values']) for d in family['dimensions'])
            calls = size
        elif family['mode'] == 'sequence':
            require(len(family['dimensions']) == 1 and family['sequence_length'] == 11, 'Only the length-11 sequence family is supported')
            require(len(family['dimensions'][0]['values']) == 3, 'Sequence alphabet must have three symbols')
            size = 3 ** family['sequence_length']
            calls = size * family['sequence_length']
        else:
            raise ValueError('Unknown family mode')
        require((family['combination_count'], family['call_count']) == (size, calls), 'Wrong family cardinality/call count')
        require(sizes.get(family['id']) == (size, calls), 'Wrong family for fixed profile')
    refs = [x['spec_ref'] for x in data['coverage']]
    unique(refs, 'coverage specification refs')
    require(set(REQUIRED_REFS) <= set(refs), 'Missing required coverage references')
    assigned = set()
    for row in data['coverage']:
        require(ref_valid(row['spec_ref']), 'Unknown coverage specification reference')
        require(row['method'] in {'test', 'review', 'test_and_review', 'caller', 'out_of_scope'}, 'Unknown coverage method')
        require(all(x in item_ids for x in row['item_ids']), 'Dangling coverage item reference')
        if row['method'] in {'test', 'review', 'test_and_review'}:
            require(bool(row['item_ids']), 'In-scope coverage must reference items')
        assigned.update(row['item_ids'])
    require(set(item_ids) <= assigned, 'Case/family/static item lacks coverage mapping')
    return data


def execution_record(data):
    return {'format_version': '0.1.0', 'unit_test_spec_id': data['document']['id'],
            'specification_status': 'draft_trial', 'results': [
                {'item_id': item['id'], 'status': 'not_executed', 'evidence': []} for item in all_items(data)],
            'note': 'New specification items have not been executed. Legacy aggregate logs are reference evidence only.'}


def validate_execution(record, data):
    require(type(record) is dict and set(record) == {'format_version', 'unit_test_spec_id', 'specification_status', 'results', 'note'}, 'Invalid execution record shape')
    require(record['format_version'] == '0.1.0' and record['unit_test_spec_id'] == data['document']['id'] and record['specification_status'] == 'draft_trial', 'Execution record identity mismatch')
    require(type(record['results']) is list, 'Execution results must be an array')
    actual = []
    for result in record['results']:
        require(type(result) is dict and set(result) == {'item_id', 'status', 'evidence'}, 'Invalid execution result shape')
        require(result['status'] == 'not_executed' and result['evidence'] == [], 'This document-generation trial cannot import pass results')
        actual.append(result['item_id'])
    unique(actual, 'execution item IDs')
    require(set(actual) == {x['id'] for x in all_items(data)}, 'Execution item set mismatch')
    require(type(record['note']) is str and bool(record['note']), 'Missing execution note')
    return record


def traceability(data):
    return {'unit_test_spec_id': data['document']['id'], 'target': data['target'],
            'status': 'draft_trial', 'execution_status': 'not_executed',
            'counts': {'representative_cases': len(data['cases']), 'parameter_families': len(data['families']),
                       'static_review_items': len(data['static_checks']),
                       'representative_call_checks': sum(s['repeat'] for c in data['cases'] for s in c['steps']),
                       'family_instances': sum(f['combination_count'] for f in data['families']),
                       'family_call_checks': sum(f['call_count'] for f in data['families'])},
            'families': [{'id': f['id'], 'instances': f['combination_count'], 'call_checks': f['call_count']} for f in data['families']],
            'coverage': data['coverage'], 'open_issues': data['open_issues']}
