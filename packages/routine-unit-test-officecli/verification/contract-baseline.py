"""Temporary no-validation baseline, replaced after negative tests turn red."""


def resolve(data, path):
    value = data
    for part in path.split('.'):
        value = value[part]
    return value


def validate(data, schema, program_spec):
    return data


def execution_record(data):
    return {'format_version': '0.1.0', 'unit_test_spec_id': data['document']['id'],
            'specification_status': 'draft_trial', 'results': [
                {'item_id': x['id'], 'status': 'not_executed', 'evidence': []}
                for key in ('cases', 'families', 'static_checks') for x in data[key]],
            'note': 'New specification items have not been executed.'}


def validate_execution(record, data):
    return record


def traceability(data):
    return {'coverage': data['coverage']}
