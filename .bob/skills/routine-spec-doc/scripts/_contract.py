"""Self-contained full specification contract; JSON data is never executed."""
import math

def resolve(data, path):
    value = data
    for part in path.split("."):
        value = value[part]
    return value


def validate_schema(schema, path='$'):
    supported = {'$schema', '$id', 'title', 'description', 'type', 'properties', 'required',
                 'additionalProperties', 'items', 'minItems', 'minLength', 'minimum', 'const', 'enum'}
    unknown = set(schema) - supported
    if unknown:
        raise ValueError(f'{path}: unsupported schema keywords {sorted(unknown)}')
    if schema.get('type') not in (None, 'object', 'array', 'string', 'integer', 'number', 'boolean', 'null'):
        raise ValueError(f'{path}: unsupported schema type')
    for key, value in schema.get('properties', {}).items():
        validate_schema(value, path+'.properties.'+key)
    for key in ('items', 'additionalProperties'):
        if isinstance(schema.get(key), dict):
            validate_schema(schema[key], path+'.'+key)


def finite_json(value, path='$'):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for i, item in enumerate(value):
            finite_json(item, f'{path}[{i}]')
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for key, item in value.items():
            finite_json(item, path+'.'+key)
        return
    raise ValueError(f'{path}: expected finite JSON value')


def validate_value(value, schema, path='$', errors=None):
    if errors is None:
        validate_schema(schema)
        finite_json(value)
        errors = []
    types = {'object': lambda v: type(v) is dict, 'array': lambda v: type(v) is list,
             'string': lambda v: type(v) is str, 'integer': lambda v: type(v) is int,
             'number': lambda v: type(v) in (int, float),
             'boolean': lambda v: type(v) is bool, 'null': lambda v: v is None}
    expected = schema.get("type")
    if expected not in (None, *types):
        raise ValueError(f'{path}: unsupported schema type')
    if expected and not types[expected](value):
        errors.append(f"{path}: expected {expected}")
        return errors
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: unsupported value {value!r}')
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errors.append(f"{path}.{k}: required")
        for k, v in value.items():
            if k in schema.get("properties", {}):
                validate_value(v, schema["properties"][k], path + "." + k, errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{k}: unknown field")
            elif isinstance(schema.get('additionalProperties'), dict):
                validate_value(v, schema['additionalProperties'], path+'.'+k, errors)
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        for i, v in enumerate(value):
            validate_value(v, schema.get("items", {}), f"{path}[{i}]", errors)
    elif isinstance(value, str) and len(value.strip()) < schema.get("minLength", 0):
        errors.append(f"{path}: empty string")
    elif type(value) in (int, float) and value < schema.get("minimum", value):
        errors.append(f"{path}: below minimum")
    return errors


def validate(data, schema):
    errors = validate_value(data, schema)
    if errors:
        raise ValueError("\n".join(errors))
    for path in ("trial_assumptions", "behavior.steps", "constraints", "verification_examples", "open_issues"):
        ids = [r["id"] for r in resolve(data, path)]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate IDs in {path}")
    return data


def skeleton(routine_name='', routine_id='', document_id=''):
    """Intentionally invalid authoring starting point without business rules."""
    return {'schema_version': '0.2.0',
            'document': {'id': document_id, 'title': '', 'revision': '', 'date': '',
                         'status': 'draft_trial', 'status_label': '未記入 人による確認前',
                         'routine_id': routine_id, 'routine_name': routine_name,
                         'template_id': 'routine-spec-v02', 'author': ''},
            'overview': dict.fromkeys(('purpose', 'scope', 'source_requirement',
                                      'requirement_id', 'source_locator', 'coverage'), ''),
            'trial_assumptions': [],
            'interface': {'language': 'C90', 'visibility': '', 'prototype': '',
                          'type_definitions': '', 'parameters': [], 'return_codes': [],
                          'preconditions': ''},
            'behavior': {'state_fields': [], 'result_fields': [], 'steps': [],
                         'decision_rows': [], 'postconditions': '', 'timing_semantics': ''},
            'constraints': [], 'verification_examples': [], 'traceability': [], 'open_issues': []}
