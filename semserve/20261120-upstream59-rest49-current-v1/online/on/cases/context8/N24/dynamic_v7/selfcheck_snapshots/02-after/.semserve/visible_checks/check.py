import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "products/accounts/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "products/accounts/SPEC.md",
                "requirement_quote": "按34字符定长记录解析账户，字段 ID4/姓名20/余额10。返回 [{id,name:去掉末尾填充空格,balance:整数}]，保持文件顺序。合法 ASCII 输入。",
                "reason": "SPEC only guarantees legal ASCII input; no rule requires rejecting non-finite values.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "products/accounts/SPEC.md",
                "requirement_quote": "按34字符定长记录解析账户，字段 ID4/姓名20/余额10。返回 [{id,name:去掉末尾填充空格,balance:整数}]，保持文件顺序。合法 ASCII 输入。",
                "reason": "SPEC does not document a ValueError contract for invalid payload types.",
            },
        },
    },
    {
        "target_path": "products/books/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "products/books/SPEC.md",
                "requirement_quote": "按28字符定长记录解析图书，字段 ID4/书名20/owner4。返回 [{id,title:去掉末尾空格,owner}]，保持文件顺序。",
                "reason": "SPEC does not require rejecting non-finite values.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "products/books/SPEC.md",
                "requirement_quote": "按28字符定长记录解析图书，字段 ID4/书名20/owner4。返回 [{id,title:去掉末尾空格,owner}]，保持文件顺序。",
                "reason": "SPEC does not document a ValueError contract for invalid payload types.",
            },
        },
    },
    {
        "target_path": "products/orders/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "products/orders/SPEC.md",
                "requirement_quote": "逐个解析22字符交易请求：buyer4/seller4/book4/amount10。返回 [{buyer,seller,book,amount:整数}]，保持请求顺序。",
                "reason": "SPEC does not require rejecting non-finite values.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "products/orders/SPEC.md",
                "requirement_quote": "逐个解析22字符交易请求：buyer4/seller4/book4/amount10。返回 [{buyer,seller,book,amount:整数}]，保持请求顺序。",
                "reason": "SPEC does not document a ValueError contract for invalid payload types.",
            },
        },
    },
    {
        "target_path": "products/settlement/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "products/settlement/SPEC.md",
                "requirement_quote": "顺序执行交易。请求中的买卖账户和书均存在，买卖方不同、正常金额且余额足够；当前 owner==seller 才成功。",
                "reason": "SPEC does not require rejecting non-finite values.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "products/settlement/SPEC.md",
                "requirement_quote": "顺序执行交易。请求中的买卖账户和书均存在，买卖方不同、正常金额且余额足够；当前 owner==seller 才成功。",
                "reason": "SPEC does not document a ValueError contract for invalid payload types.",
            },
        },
    },
]


class TestAccounts(unittest.TestCase):
    def test_parse_accounts(self):
        payloads = {"text": "U001John Doe            0000001000U002Jane Smith          0000002000"}
        contract = {}
        result = call_candidate("products/accounts/engine.py", "transform", args=[payloads, contract])
        self.assertEqual(
            result,
            [
                {"id": "U001", "name": "John Doe", "balance": 1000},
                {"id": "U002", "name": "Jane Smith", "balance": 2000},
            ],
        )


class TestBooks(unittest.TestCase):
    def test_parse_books(self):
        payloads = {"text": "B001Python Basics       U001B003Java Tutorial       U003"}
        contract = {}
        result = call_candidate("products/books/engine.py", "transform", args=[payloads, contract])
        self.assertEqual(
            result,
            [
                {"id": "B001", "title": "Python Basics", "owner": "U001"},
                {"id": "B003", "title": "Java Tutorial", "owner": "U003"},
            ],
        )


class TestOrders(unittest.TestCase):
    def test_parse_orders(self):
        payloads = {"orders": ["U001U003B0030000000020"]}
        contract = {}
        result = call_candidate("products/orders/engine.py", "transform", args=[payloads, contract])
        self.assertEqual(
            result,
            [{"buyer": "U001", "seller": "U003", "book": "B003", "amount": 20}],
        )


class TestSettlement(unittest.TestCase):
    def _accounts(self):
        return [
            {"id": "U001", "name": "John Doe", "balance": 1000},
            {"id": "U002", "name": "Jane Smith", "balance": 2000},
            {"id": "U003", "name": "Bob Wilson", "balance": 1500},
        ]

    def _books(self):
        return [
            {"id": "B001", "title": "Python Basics", "owner": "U001"},
            {"id": "B003", "title": "Java Tutorial", "owner": "U003"},
        ]

    def test_reject_when_owner_mismatch(self):
        payloads = {
            "accounts": self._accounts(),
            "books": self._books(),
            "orders": [{"buyer": "U002", "seller": "U001", "book": "B003", "amount": 50}],
            "journal": "",
        }
        contract = {}
        result = call_candidate("products/settlement/engine.py", "transform", args=[payloads, contract])
        self.assertEqual(result["statuses"], ["rejected"])
        # No state change: journal empty, balances unchanged, owner unchanged.
        self.assertEqual(result["journal"], "")
        self.assertIn("U001John Doe            0000001000", result["accounts"])
        self.assertIn("B003Java Tutorial       U003", result["books"])

    def test_accept_transfer(self):
        payloads = {
            "accounts": self._accounts(),
            "books": self._books(),
            "orders": [{"buyer": "U001", "seller": "U003", "book": "B003", "amount": 20}],
            "journal": "",
        }
        contract = {}
        result = call_candidate("products/settlement/engine.py", "transform", args=[payloads, contract])
        self.assertEqual(result["statuses"], ["accepted"])
        self.assertEqual(result["journal"], "B0030000000020U003U001")
        self.assertIn("U001John Doe            0000000980", result["accounts"])
        self.assertIn("U003Bob Wilson          0000001520", result["accounts"])
        self.assertIn("B003Java Tutorial       U001", result["books"])


if __name__ == "__main__":
    unittest.main()
