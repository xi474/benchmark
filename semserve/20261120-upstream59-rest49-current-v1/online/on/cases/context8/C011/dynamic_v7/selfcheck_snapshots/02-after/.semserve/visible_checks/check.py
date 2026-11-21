import unittest
import json
from pathlib import Path

# The transform API takes a single payload object (not a two-argument
# transform). The visible contract (TASK.md) documents transform(payload).
# The SDK's public_api_targets inventory only flags functions named transform
# with >=2 positional args, so solution.transform (1 arg) is not inventoried.
# We therefore declare no API boundary requirements and instead exercise the
# business behavior with ordinary unittest + call_candidate.

API_BOUNDARY_REQUIREMENTS = []


def _load(name):
    return json.loads(Path(name).read_text(encoding='utf-8'))


class TestTransform(unittest.TestCase):
    def test_public_fixture_matches_expected(self):
        # Independent oracle: the public input must produce the public expected
        # output exactly (container shape, ordering, and values).
        payload = _load('public_input.json')
        expected = _load('public_expected.json')
        actual = call_candidate('solution.py', 'transform', args=[payload])
        self.assertEqual(actual, expected)

    def test_output_container_shape(self):
        # Output contract: top-level keys and their types.
        payload = _load('public_input.json')
        actual = call_candidate('solution.py', 'transform', args=[payload])
        self.assertEqual(set(actual), {'selected', 'erp', 'mes', 'wms'})
        self.assertIsInstance(actual['selected'], list)
        self.assertIsInstance(actual['erp'], dict)
        self.assertIsInstance(actual['mes'], list)
        self.assertIsInstance(actual['wms'], list)
        self.assertEqual(set(actual['erp']), {'run', 'orders'})
        self.assertEqual(actual['erp']['run']['id'], payload['run_id'])
        self.assertEqual(actual['erp']['run']['freeze'], payload['freeze'])

    def test_selected_sorted_and_consistent(self):
        # selected must be ascending order ids and match ERP PLANNED orders.
        payload = _load('public_input.json')
        actual = call_candidate('solution.py', 'transform', args=[payload])
        self.assertEqual(actual['selected'], sorted(actual['selected']))
        planned = [o['wo'] for o in actual['erp']['orders']
                   if o['status'] == 'PLANNED']
        self.assertEqual(actual['selected'], planned)

    def test_wip_present_and_first_on_line(self):
        # WIP is mandatory, WIP_CONT, parent null, and occupies seq 1 on its line.
        payload = _load('public_input.json')
        actual = call_candidate('solution.py', 'transform', args=[payload])
        wip_ids = {w['id'] for w in payload['wip']}
        erp_wip = [o for o in actual['erp']['orders'] if o['status'] == 'WIP_CONT']
        self.assertEqual({o['wo'] for o in erp_wip}, wip_ids)
        for o in erp_wip:
            self.assertIsNone(o['parent'])
        for line in {m['line'] for m in actual['mes']}:
            seqs = [m for m in actual['mes'] if m['line'] == line]
            seqs.sort(key=lambda m: m['seq'])
            self.assertEqual(seqs[0]['seq'], 1)
            if seqs[0]['wo'] in wip_ids:
                self.assertEqual(seqs[0]['status'], 'WIP_CONT')

    def test_reservation_totals_do_not_exceed_lot_qty(self):
        # Shared inventory: total reserved per lot must not exceed lot.qty.
        payload = _load('public_input.json')
        actual = call_candidate('solution.py', 'transform', args=[payload])
        lot_qty = {l['id']: l['qty'] for l in payload['lots']}
        used = {}
        for r in actual['wms']:
            used[r['lot']] = used.get(r['lot'], 0) + r['qty']
        for lot, q in used.items():
            self.assertLessEqual(q, lot_qty[lot])

    def test_reservation_expiry_and_status(self):
        # Only PASS lots with expiry >= task end may be reserved.
        payload = _load('public_input.json')
        actual = call_candidate('solution.py', 'transform', args=[payload])
        lots = {l['id']: l for l in payload['lots']}
        end_by_wo = {o['wo']: o['end'] for o in actual['erp']['orders']}
        for r in actual['wms']:
            lot = lots[r['lot']]
            self.assertEqual(lot['status'], 'PASS')
            self.assertGreaterEqual(lot['expiry'], end_by_wo[r['wo']])

    def test_changeover_and_window_respected(self):
        # Adjacent tasks on a line (including WIP) are separated by changeover,
        # and every task lies within a window and ends <= due.
        payload = _load('public_input.json')
        actual = call_candidate('solution.py', 'transform', args=[payload])
        co = payload['changeover']
        windows = {l['id']: l['windows'] for l in payload['lines']}
        due = {o['id']: o['due'] for o in payload['orders']}
        due.update({w['id']: w['due'] for w in payload['wip']})
        for line in {m['line'] for m in actual['mes']}:
            tasks = sorted([m for m in actual['mes'] if m['line'] == line],
                           key=lambda m: m['start'])
            for i in range(len(tasks) - 1):
                self.assertGreaterEqual(tasks[i + 1]['start'],
                                        tasks[i]['end'] + co)
            for t in tasks:
                self.assertLessEqual(t['end'], due[t['wo']])
                in_window = any(ws <= t['start'] and t['end'] <= we
                                for (ws, we) in windows[line])
                self.assertTrue(in_window)


if __name__ == '__main__':
    unittest.main()
