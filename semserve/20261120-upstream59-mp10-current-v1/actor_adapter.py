"""Use the published portable placeholders for the selected legacy tasks."""

from pathlib import Path

from parallel20_actor_base_adapter import audit_semantic_root, semantic_cli


def fixture_paths(template, task_text):
    """Preserve the original portable task's editable and protected files."""
    from portable_task_fixtures import portable_fixture_paths

    return portable_fixture_paths(template)


def preflight_template(template, task_text):
    """Expose the resolved permissions for the experiment's offline receipt."""
    fixed, editable = fixture_paths(template, task_text)
    template = Path(template)
    return {
        'protected_count': len(fixed),
        'editable_count': len(editable),
        'editable': editable,
        'public_checker_protected': 'check.py' in fixed,
        'root_entry_creation_required': not (template / 'run_all.py').exists(),
        'root_entry_editable': 'run_all.py' in editable,
        'final_report_creation_required': not (template / 'final_report.py').exists(),
        'final_report_editable': 'final_report.py' in editable,
    }
