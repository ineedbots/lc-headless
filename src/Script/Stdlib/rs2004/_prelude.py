# Run into every script's builtins when the API is bound, before _load_stdlib.py: helpers the host calls
# through CallBuiltin. Scripts don't call these.


def _report_rows(report):
    if not isinstance(report, dict):
        raise TypeError(f'on_progress_report() must return a dict, not {type(report).__name__}')
    return [[str(name), str(value)] for name, value in report.items()]
