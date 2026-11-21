import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/block_layout/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "engines/block_layout/SPEC.md",
                "requirement_quote": "matrix是二维块列表，每块 {rows,cols,data:整数二维列表或null}",
                "reason": "SPEC does not state a ValueError rule for non-finite or unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "engines/block_layout/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支",
                "reason": "SPEC does not document a ValueError for invalid payload types.",
            },
        },
    },
    {
        "target_path": "engines/squared/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "engines/squared/SPEC.md",
                "requirement_quote": "全零块 data=null，其他块 data为整数二维列表",
                "reason": "SPEC does not state a ValueError rule for non-finite or unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "engines/squared/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支",
                "reason": "SPEC does not document a ValueError for invalid payload types.",
            },
        },
    },
    {
        "target_path": "engines/cubed/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "engines/cubed/SPEC.md",
                "requirement_quote": "消费 B² 再乘 B，返回 {layout:输入layout,blocks:B³的有形状分块矩阵}",
                "reason": "SPEC does not state a ValueError rule for non-finite or unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "engines/cubed/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支",
                "reason": "SPEC does not document a ValueError for invalid payload types.",
            },
        },
    },
]


class TestBlockLayout(unittest.TestCase):
    def test_row_and_col_sizes(self):
        matrix = [
            [{"rows": 2, "cols": 2, "data": [[2, 0], [0, 3]]}, {"rows": 2, "cols": 1, "data": None}],
            [{"rows": 1, "cols": 2, "data": None}, {"rows": 1, "cols": 1, "data": None}],
        ]
        expected = {"row_sizes": [2, 1], "col_sizes": [2, 1]}
        result = call_candidate("engines/block_layout/engine.py", "transform", args=[{"matrix": matrix}, {}])
        self.assertEqual(result, expected)


class TestSquared(unittest.TestCase):
    def test_square_preserves_zero_block_shape(self):
        # B = diag(2,3) block; B^2 = diag(4,9). Zero blocks stay shaped null.
        matrix = [
            [{"rows": 2, "cols": 2, "data": [[2, 0], [0, 3]]}, {"rows": 2, "cols": 1, "data": None}],
            [{"rows": 1, "cols": 2, "data": None}, {"rows": 1, "cols": 1, "data": None}],
        ]
        result = call_candidate("engines/squared/engine.py", "transform", args=[{"matrix": matrix}, {}])
        self.assertEqual(result[0][0], {"rows": 2, "cols": 2, "data": [[4, 0], [0, 9]]})
        self.assertEqual(result[0][1], {"rows": 2, "cols": 1, "data": None})
        self.assertEqual(result[1][0], {"rows": 1, "cols": 2, "data": None})
        self.assertEqual(result[1][1], {"rows": 1, "cols": 1, "data": None})


class TestCubed(unittest.TestCase):
    def test_cube_consumes_squared(self):
        matrix = [
            [{"rows": 2, "cols": 2, "data": [[2, 0], [0, 3]]}, {"rows": 2, "cols": 1, "data": None}],
            [{"rows": 1, "cols": 2, "data": None}, {"rows": 1, "cols": 1, "data": None}],
        ]
        squared = [
            [{"rows": 2, "cols": 2, "data": [[4, 0], [0, 9]]}, {"rows": 2, "cols": 1, "data": None}],
            [{"rows": 1, "cols": 2, "data": None}, {"rows": 1, "cols": 1, "data": None}],
        ]
        layout = {"row_sizes": [2, 1], "col_sizes": [2, 1]}
        result = call_candidate(
            "engines/cubed/engine.py",
            "transform",
            args=[{"squared": squared, "matrix": matrix, "layout": layout}, {}],
        )
        self.assertEqual(result["layout"], layout)
        self.assertEqual(result["blocks"][0][0], {"rows": 2, "cols": 2, "data": [[8, 0], [0, 27]]})
        self.assertEqual(result["blocks"][0][1], {"rows": 2, "cols": 1, "data": None})
        self.assertEqual(result["blocks"][1][0], {"rows": 1, "cols": 2, "data": None})
        self.assertEqual(result["blocks"][1][1], {"rows": 1, "cols": 1, "data": None})


if __name__ == "__main__":
    unittest.main()
