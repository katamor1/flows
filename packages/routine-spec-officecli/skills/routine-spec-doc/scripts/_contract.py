"""Fixed sample contract; intentionally limited JSON Schema keyword support."""

def resolve(data, path):
    value = data
    for part in path.split("."):
        value = value[part]
    return value


def validate_value(value, schema, path="$", errors=None):
    """Validate only the explicitly supported keywords used by our schema.

    The JSON Schema file remains interoperable with a full Draft 2020-12 validator.
    Unknown validation keywords fail closed instead of being silently ignored.
    """
    if errors is None:
        errors = []
    supported = {"$schema", "$id", "title", "description", "type", "properties", "required",
                 "additionalProperties", "items", "minItems", "minLength", "minimum", "const"}
    unknown = set(schema) - supported
    if unknown:
        errors.append(f"{path}: unsupported schema keywords {sorted(unknown)}")
        return errors
    types = {"object": dict, "array": list, "string": str, "integer": int}
    expected = schema.get("type")
    if expected and type(value) is not types[expected]:
        errors.append(f"{path}: expected {expected}")
        return errors
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errors.append(f"{path}.{k}: required")
        for k, v in value.items():
            if k in schema.get("properties", {}):
                validate_value(v, schema["properties"][k], path + "." + k, errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{k}: unknown field")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        for i, v in enumerate(value):
            validate_value(v, schema["items"], f"{path}[{i}]", errors)
    elif isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: empty string")
    elif type(value) is int and value < schema.get("minimum", value):
        errors.append(f"{path}: below minimum")
    return errors


def validate(data, schema):
    errors = validate_value(data, schema)
    if errors:
        raise ValueError("\n".join(errors))
    if data["document"]["status"] != "draft_trial":
        raise ValueError("This prototype cannot create approved specifications")
    if data["behavior"]["threshold"] != 10:
        raise ValueError("This sample's rules and examples are defined for threshold 10")
    for path in ("trial_assumptions", "behavior.steps", "constraints", "verification_examples", "open_issues"):
        ids = [r["id"] for r in resolve(data, path)]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate IDs in {path}")
    return data
