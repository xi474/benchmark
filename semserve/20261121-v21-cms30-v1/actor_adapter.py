"""Use the sealed Upstream59 fixture manifest, or the published portable placeholders."""

from pathlib import Path

from parallel20_actor_base_adapter import audit_semantic_root, semantic_cli


MANIFEST = Path('/opt/fixture_manifest.json')


def workspace_files(template):
    template = Path(template)
    return [p.relative_to(template).as_posix() for p in sorted(template.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts]


def fixture_paths(template, task_text):
    """Classify per the sealed manifest when present; else per portable placeholders."""
    if MANIFEST.is_file():
        import json
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        protected = set(manifest['protected'])
        files = workspace_files(template)
        fixed = [name for name in files if name in protected]
        editable = [name for name in files if name not in protected]
        return fixed, editable
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
        'public_checker_protected': 'check.py' in fixed or 'public_check.py' in fixed,
        'root_entry_creation_required': not (template / 'run_all.py').exists(),
        'root_entry_editable': 'run_all.py' in editable,
        'final_report_creation_required': not (template / 'final_report.py').exists(),
        'final_report_editable': 'final_report.py' in editable,
    }
