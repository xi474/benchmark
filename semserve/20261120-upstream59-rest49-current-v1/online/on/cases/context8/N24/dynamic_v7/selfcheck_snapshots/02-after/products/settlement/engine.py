"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
from runtime import build


def _encode_account(acc):
    return acc["id"] + acc["name"].ljust(20) + str(acc["balance"]).rjust(10, "0")


def _encode_book(book):
    return book["id"] + book["title"].ljust(20) + book["owner"]


def transform(payload, contract):
    accounts = payload["accounts"]
    books = payload["books"]
    orders = payload["orders"]
    journal = payload["journal"]

    acc_by_id = {a["id"]: a for a in accounts}
    book_by_id = {b["id"]: b for b in books}

    statuses = []
    for order in orders:
        buyer = order["buyer"]
        seller = order["seller"]
        book_id = order["book"]
        amount = order["amount"]

        book = book_by_id[book_id]
        if book["owner"] == seller:
            acc_by_id[buyer]["balance"] -= amount
            acc_by_id[seller]["balance"] += amount
            book["owner"] = buyer
            journal += book_id + str(amount).rjust(10, "0") + seller + buyer
            statuses.append("accepted")
        else:
            statuses.append("rejected")

    return {
        "accounts": "".join(_encode_account(a) for a in accounts),
        "books": "".join(_encode_book(b) for b in books),
        "journal": journal,
        "statuses": statuses,
    }


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
