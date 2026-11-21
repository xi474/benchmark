"""Check legacy task permissions without network access or model calls."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
ROOT = RESULTS.parent
SUPPORT = ROOT / 'experiments/handshake_speculation_v1_report_gate_v1'
sys.path[:0] = [str(HERE), str(SUPPORT)]

# The actor receives this exact frozen helper under its deployed module name.
base_path = RESULTS / '20261116-parallel20-semantic-ab-v1/actor_adapter.py'
spec = importlib.util.spec_from_file_location('parallel20_actor_base_adapter', base_path)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

from actor_adapter import fixture_paths, preflight_template, semantic_cli
from portable_task_fixtures import portable_fixture_paths


SELECTED = {
    'multistage4/storage_tiering_migration_spec_v4',
    'context8/streaming_checkpoint_recovery_spec_v4',
    'reasoning4/edge_fleet_rollout_spec_v4',
    'reasoning4/python_import_usage',
    'linux2/reversible_file_resharding',
}


def selected_sources():
    sources = []
    for name in (
        '20261101-serial-unittest-mixed16-v1',
        '20261108-medium26-current-v5-coverage-v1',
    ):
        plan = json.loads((RESULTS / name / 'experiment_plan.json').read_text(encoding='utf8'))
        sources.extend(row for row in plan['tasks'] if row['entry_id'] in SELECTED)
    assert {row['entry_id'] for row in sources} == SELECTED and len(sources) == 5
    return sources


class PortableAdapterTests(unittest.TestCase):
    def test_published_legacy_task_placeholders(self):
        for row in selected_sources():
            task = Path(row['task_source'])
            template = task / 'workspace'
            text = (task / 'TASK.md').read_text(encoding='utf8')
            with self.subTest(task=row['entry_id']):
                fixed, editable = fixture_paths(template, text)
                self.assertEqual((fixed, editable), portable_fixture_paths(template))
                self.assertIn('check.py', fixed)
                self.assertIn('integrate.py', fixed)
                self.assertTrue(all(name.endswith('.py') for name in editable))
                self.assertTrue(all(name not in editable for name in fixed))
                self.assertEqual(set(fixed) | set(editable), set(row['workspace_files']))
                report = preflight_template(template, text)
                self.assertTrue(report['public_checker_protected'])
                self.assertTrue(report['root_entry_editable'] or report['root_entry_creation_required'])
                self.assertTrue(report['final_report_editable'] or report['final_report_creation_required'])
                print(json.dumps(dict(entry=row['entry_id'], **report), ensure_ascii=False))

    def test_supplied_infrastructure_remains_protected(self):
        with tempfile.TemporaryDirectory() as temporary:
            template = Path(temporary)
            for name in ('check.py', 'integrate.py', 'parser.py', 'model.py', 'run_all.py'):
                (template / name).write_text('raise NotImplementedError\n', encoding='utf8')
            fixed, editable = fixture_paths(template, 'Implement the supplied placeholders.')
            self.assertEqual(editable, ['model.py', 'run_all.py'])
            self.assertEqual(fixed, ['check.py', 'integrate.py', 'parser.py'])

    def test_mode_binding_reuses_frozen_controls(self):
        argv = ['runner', '--parallel-v2', 'active']
        self.assertEqual(semantic_cli(argv, 'on'), argv)
        self.assertEqual(semantic_cli(argv, 'off'),
                         ['runner', '--parallel-v2', 'off', '--no-subtasks'])
        self.assertEqual(argv, ['runner', '--parallel-v2', 'active'])


if __name__ == '__main__':
    unittest.main()
