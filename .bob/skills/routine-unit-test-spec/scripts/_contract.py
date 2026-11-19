"""Finite JSON contract and traceability checks. Values are data, never evaluated."""
import json
import math
import re
SCHEMA_KEYS = {'$schema', '$id', 'title', 'description', 'type', 'properties', 'required', 'additionalProperties',
               'items', 'minItems', 'minLength', 'minimum', 'const', 'enum'}
def require(condition, message):
    if not condition: raise ValueError(message)
def resolve(data, path):
    for part in path.split('.'): data = data[part]
    return data

def finite_json(data, path='$'):
    if type(data) is float: require(math.isfinite(data), path+': nonfinite JSON number')
    elif type(data) in (str, int, bool) or data is None: pass
    elif type(data) is list:
        for n, value in enumerate(data): finite_json(value, f'{path}[{n}]')
    elif type(data) is dict:
        for name, value in data.items():
            require(type(name) is str, path+': JSON object keys must be strings')
            finite_json(value, path+'.'+name)
    else: raise ValueError(path+': not a JSON value')

def audit_schema(schema, path='$schema'):
    require(type(schema) is dict and not set(schema)-SCHEMA_KEYS, path+': unsupported schema keywords')
    for name, child in schema.get('properties', {}).items(): audit_schema(child, path+'.'+name)
    if 'items' in schema: audit_schema(schema['items'], path+'[]')
    if type(schema.get('additionalProperties')) is dict: audit_schema(schema['additionalProperties'], path+'.*')

def validate_shape(data, schema, path='$'):
    audit_schema(schema)
    types = {'object': lambda v: type(v) is dict, 'array': lambda v: type(v) is list,
             'string': lambda v: type(v) is str, 'integer': lambda v: type(v) is int,
             'number': lambda v: type(v) in (int, float), 'boolean': lambda v: type(v) is bool,
             'null': lambda v: v is None}
    expected = schema.get('type')
    if expected:
        require(expected in types, path+': unsupported schema type')
        require(types[expected](data), path+': expected '+expected)
    if 'const' in schema: require(data == schema['const'], path+': constant mismatch')
    if 'enum' in schema: require(data in schema['enum'], path+': enum mismatch')
    if isinstance(data, dict):
        for name in schema.get('required', []): require(name in data, path+'.'+name+': required')
        for name, value in data.items():
            if name in schema.get('properties', {}): validate_shape(value, schema['properties'][name], path+'.'+name)
            else:
                extra = schema.get('additionalProperties', True)
                require(extra is not False, path+'.'+name+': unknown field')
                if isinstance(extra, dict): validate_shape(value, extra, path+'.'+name)
    elif isinstance(data, list):
        require(len(data) >= schema.get('minItems', 0), path+': too few items')
        for n, value in enumerate(data): validate_shape(value, schema.get('items', {}), f'{path}[{n}]')
    elif isinstance(data, str): require(len(data.strip()) >= schema.get('minLength', 0), path+': empty string')
    elif type(data) in (int, float): require(data >= schema.get('minimum', data), path+': below minimum')

def unique(values, label):
    require(len(values) == len(set(values)), 'Duplicate '+label)

DECLARATION_COLLECTIONS = ('trial_assumptions', 'behavior.steps', 'constraints',
                           'verification_examples', 'open_issues')


def declaration_ids(program):
    """Only program-contract declaration records own IDs.

    Configuration values and decision results are arbitrary JSON data. Their
    literal `id` keys have no declaration meaning and remain pointer-addressable.
    """
    result = []
    for path in DECLARATION_COLLECTIONS:
        try: records = resolve(program, path)
        except (KeyError, TypeError): continue
        if not isinstance(records, list): continue
        for n, record in enumerate(records):
            if isinstance(record, dict) and isinstance(record.get('id'), str):
                result.append(('/'+path.replace('.', '/')+'/'+str(n), record['id']))
    return result


def collect_ids(program):
    result = [identifier for _, identifier in declaration_ids(program)]
    document_id = program.get('document', {}).get('id')
    if isinstance(document_id, str): result.append(document_id)
    return result


def pointer_exists(data, pointer):
    if not pointer.startswith('/'): return False
    try:
        for raw in pointer.split('/')[1:]:
            require(not re.search(r'~(?![01])', raw), 'Invalid JSON pointer escape')
            part = raw.replace('~1', '/').replace('~0', '~')
            if isinstance(data, list):
                require(re.fullmatch(r'0|[1-9][0-9]*', part) is not None, 'Invalid array index')
                data = data[int(part)]
            else: data = data[part]
        return True
    except (KeyError, IndexError, TypeError, ValueError): return False

def required_refs(program):
    """Declared normative records use their IDs; records without IDs use pointers.

    Interface/behavior fields are independently accounted for. Empty fields carry
    no declarations. This supports full program documents and supplied contracts.
    """
    result = []
    declared = dict(declaration_ids(program))
    def visit(value, pointer):
        if value in ('', None) or value == [] or value == {}: return
        if pointer in declared: result.append(declared[pointer])
        elif isinstance(value, list):
            for n, child in enumerate(value): visit(child, pointer+'/'+str(n))
        else: result.append(pointer)
    for section in ('trial_assumptions', 'constraints', 'verification_examples'):
        visit(program.get(section, []), '/'+section)
    for section in ('interface', 'behavior', 'external_api'):
        value = program.get(section, {})
        if isinstance(value, dict):
            for key, child in value.items(): visit(child, '/'+section+'/'+key.replace('~', '~0').replace('/', '~1'))
        else: visit(value, '/'+section)
    requirement = program.get('overview', {}).get('requirement_id')
    if isinstance(requirement, str) and requirement: result.append(requirement)
    return set(result)

def all_items(data): return [item for name in ('cases', 'families', 'static_checks') for item in data[name]]

def validate(data, schema, program_spec, target=None):
    finite_json(data)
    finite_json(program_spec)
    validate_shape(data, schema)
    require(target is not None and data['target'] == target, 'Target hashes do not match the actual locked input bytes')
    for value in data['target'].values(): require(re.fullmatch(r'[0-9a-f]{64}', value) is not None, 'Invalid SHA-256')
    for key in ('routine_id', 'routine_name'):
        require(data['document'][key] == program_spec['document'][key], 'Document target identity mismatch: '+key)
    require(data['assumptions'] == program_spec.get('trial_assumptions', []), 'Source assumptions must be preserved')
    require(data['open_issues'] == program_spec.get('open_issues', []), 'Source open issues must be preserved')
    spec_ids = collect_ids(program_spec)
    unique(spec_ids, 'source specification IDs')
    valid_ids = set(spec_ids)
    for value in (program_spec.get('overview', {}).get('requirement_id'), program_spec['document'].get('routine_id')):
        if isinstance(value, str): valid_ids.add(value)
    def ref_valid(ref): return ref in valid_ids or pointer_exists(program_spec, ref)
    items = all_items(data)
    require(bool(items), 'At least one case, family, or static check is required; blank skeleton cannot be rendered')
    ids = [item['id'] for item in items]
    unique(ids, 'case/family/static IDs')
    for item in items:
        unique(item['spec_refs'], 'spec refs in '+item['id'])
        for ref in item['spec_refs']: require(ref_valid(ref), 'Unknown specification reference: '+ref)
    for case in data['cases']:
        unique([x['name'] for x in case['initial_conditions']], 'initial condition names')
        unique([x['id'] for x in case['steps']], 'step IDs')
        for step in case['steps']:
            unique([x['name'] for x in step['inputs']], 'step input names')
            unique([(x['target'], x['comparison']) for x in step['expected']], 'step expected comparisons')
    for family in data['families']:
        unique([x['name'] for x in family['dimensions']], 'family dimension names')
        for dimension in family['dimensions']:
            values = dimension['values']
            require(not any(value == previous for n, value in enumerate(values) for previous in values[:n]), 'Duplicate dimension values')
        if family['mode'] == 'product':
            require(family['sequence_length'] == 0, 'Product family sequence_length must be zero')
            size = math.prod(len(d['values']) for d in family['dimensions'])
        else:
            require(len(family['dimensions']) == 1 and family['sequence_length'] > 0, 'Sequence requires one alphabet and a positive length')
            size = len(family['dimensions'][0]['values']) ** family['sequence_length']
        require(family['combination_count'] == size, 'Wrong family combination_count')
        require(family['call_count'] == size * family['calls_per_instance'], 'Wrong family call_count')
    refs = [x['spec_ref'] for x in data['coverage']]
    unique(refs, 'coverage specification refs')
    missing = required_refs(program_spec)-set(refs)
    require(not missing, 'Missing source coverage declarations: '+', '.join(sorted(missing)))
    assigned = set()
    by_id = {item['id']: item for item in items}
    for row in data['coverage']:
        require(ref_valid(row['spec_ref']), 'Unknown coverage specification reference: '+row['spec_ref'])
        unique(row['item_ids'], 'coverage item IDs')
        require(all(x in by_id for x in row['item_ids']), 'Dangling coverage item reference')
        if row['method'] in {'test', 'review', 'test_and_review'}: require(bool(row['item_ids']), 'In-scope coverage must reference items')
        else: require(not row['item_ids'], 'Unverified/caller/out-of-scope coverage cannot claim item evidence')
        for item_id in row['item_ids']:
            require(row['spec_ref'] in by_id[item_id]['spec_refs'], 'Coverage reference absent from item spec_refs')
        assigned.update(row['item_ids'])
    require(set(ids) <= assigned, 'Case/family/static item lacks coverage mapping')
    for item in items:
        mapped = {row['spec_ref'] for row in data['coverage'] if item['id'] in row['item_ids']}
        require(set(item['spec_refs']) <= mapped, 'Item specification reference lacks reverse coverage mapping: '+item['id'])
    return data

def execution_record(data):
    return {'format_version': '0.2.0', 'unit_test_spec_id': data['document']['id'],
            'specification_status': data['document']['status'], 'results': [
                {'item_id': item['id'], 'status': 'not_executed', 'evidence': []} for item in all_items(data)],
            'note': 'No test or review has been executed by document generation. Existing logs are not pass evidence.'}

def validate_execution(record, data):
    require(type(record) is dict and set(record) == {'format_version', 'unit_test_spec_id', 'specification_status', 'results', 'note'}, 'Invalid execution record shape')
    require(record['format_version'] == '0.2.0' and record['unit_test_spec_id'] == data['document']['id'] and record['specification_status'] == data['document']['status'], 'Execution record identity mismatch')
    require(type(record['results']) is list, 'Execution results must be an array')
    ids = []
    for result in record['results']:
        require(type(result) is dict and set(result) == {'item_id', 'status', 'evidence'}, 'Invalid execution result shape')
        require(result['status'] == 'not_executed' and result['evidence'] == [], 'Document generation cannot import pass results')
        ids.append(result['item_id'])
    unique(ids, 'execution item IDs')
    require(set(ids) == {x['id'] for x in all_items(data)}, 'Execution item set mismatch; synchronize the unexecuted record after authoring')
    require(type(record['note']) is str and bool(record['note']), 'Missing execution note')
    return record

def traceability(data):
    return {'unit_test_spec_id': data['document']['id'], 'target': data['target'], 'status': data['document']['status'],
            'execution_status': 'not_executed', 'counts': {'representative_cases': len(data['cases']), 'parameter_families': len(data['families']),
             'static_review_items': len(data['static_checks']), 'representative_call_checks': sum(s['repeat'] for c in data['cases'] for s in c['steps']),
             'family_instances': sum(f['combination_count'] for f in data['families']), 'family_call_checks': sum(f['call_count'] for f in data['families'])},
            'families': [{'id': f['id'], 'instances': f['combination_count'], 'call_checks': f['call_count']} for f in data['families']],
            'coverage': data['coverage'], 'open_issues': data['open_issues']}
