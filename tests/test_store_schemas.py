import os
import tempfile
import unittest

from marketing_toolkit.schemas import RECORD, ValidationError, validate
from marketing_toolkit.store import ConflictError, KnowledgeStore


def rec(**kw):
    base = {"kind": "customer_insight", "title": "Owners hate double-booking", "product": "P", "basis": "observed",
            "confidence": "medium", "data": {"statement": "x"}}
    base.update(kw)
    return base


class SchemaTests(unittest.TestCase):
    def test_valid_record(self):
        self.assertEqual(validate(rec(), RECORD, raise_on_error=False), [])

    def test_invalid_record(self):
        errs = validate({"kind": "nope", "title": "x", "data": [], "extra": 1}, RECORD, raise_on_error=False)
        joined = " ".join(errs)
        self.assertIn("kind", joined)
        self.assertIn("data", joined)
        self.assertIn("unexpected property", joined)
        self.assertIn("title", joined)  # too short

    def test_raises(self):
        with self.assertRaises(ValidationError):
            validate({"title": "abc"}, RECORD)

    def test_bool_is_not_number(self):
        self.assertTrue(validate(True, {"type": "number"}, raise_on_error=False))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.s = KnowledgeStore()

    def test_create_and_duplicate(self):
        rid, a = self.s.add(rec())
        self.assertEqual(a, "created")
        rid2, a2 = self.s.add(rec(title="  owners HATE double-booking "))  # same content after normalisation
        self.assertEqual((rid2, a2), (rid, "duplicate"))
        self.assertEqual(self.s.stats()["total"], 1)

    def test_conflict_never_silently_overwrites(self):
        rid, _ = self.s.add(rec(natural_key="k1"))
        with self.assertRaises(ConflictError) as cm:
            self.s.add(rec(natural_key="k1", data={"statement": "different"}))
        self.assertEqual(cm.exception.existing_id, rid)
        self.assertEqual(self.s.get(rid)["data"], {"statement": "x"})

    def test_skip_and_version(self):
        rid, _ = self.s.add(rec(natural_key="k1"))
        self.assertEqual(self.s.add(rec(natural_key="k1", data={"statement": "y"}), on_conflict="skip"), (rid, "skipped"))
        self.assertEqual(self.s.get(rid)["data"]["statement"], "x")
        self.assertEqual(self.s.add(rec(natural_key="k1", data={"statement": "y"}), on_conflict="version"), (rid, "versioned"))
        cur = self.s.get(rid)
        self.assertEqual((cur["data"]["statement"], cur["version"]), ("y", 2))
        hist = self.s.history(rid)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["snapshot"]["data"]["statement"], "x")

    def test_update_merges_data_and_keeps_history(self):
        rid, _ = self.s.add(rec(data={"a": 1, "b": 2}))
        self.s.update(rid, {"data": {"b": 3}, "confidence": "high"}, "test")
        cur = self.s.get(rid)
        self.assertEqual(cur["data"], {"a": 1, "b": 3})
        self.assertEqual(cur["confidence"], "high")
        self.assertEqual(self.s.history(rid)[0]["note"], "test")

    def test_noop_update_adds_no_history(self):
        rid, _ = self.s.add(rec(data={"a": 1}))
        self.s.update(rid, {"data": {"a": 1}})
        self.assertEqual(self.s.history(rid), [])
        self.assertEqual(self.s.get(rid)["version"], 1)

    def test_archive_hides(self):
        rid, _ = self.s.add(rec())
        self.s.archive(rid, "obsolete")
        self.assertEqual(self.s.find(kind="customer_insight"), [])
        self.assertEqual(len(self.s.find(kind="customer_insight", include_archived=True)), 1)

    def test_find_filters(self):
        self.s.add(rec(title="A one", confidence="low", tags=["x"]))
        self.s.add(rec(title="B two", confidence="high", product="Q"))
        self.s.add(rec(kind="offer", title="Offer C", data={}))
        self.assertEqual(len(self.s.find(kind="customer_insight")), 2)
        self.assertEqual(len(self.s.find(min_confidence="high")), 1)
        self.assertEqual(len(self.s.find(tag="x")), 1)
        self.assertEqual(len(self.s.find(text="two")), 1)
        self.assertEqual(len(self.s.find(kind=["offer", "customer_insight"], product="Q")), 1)

    def test_preview(self):
        rid, _ = self.s.add(rec(natural_key="k"))
        self.assertEqual(self.s.preview(rec(natural_key="k")), ("duplicate", rid))
        self.assertEqual(self.s.preview(rec(natural_key="k", data={"z": 1})), ("conflict", rid))
        self.assertEqual(self.s.preview(rec(natural_key="k", data={"z": 1}), "version"), ("versioned", rid))
        self.assertEqual(self.s.preview(rec(natural_key="new", data={"z": 1}))[0], "created")

    def test_persists_between_runs(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "m.db")
            s1 = KnowledgeStore(path)
            rid, _ = s1.add(rec())
            s1.close()
            s2 = KnowledgeStore(path)
            self.assertEqual(s2.get(rid)["title"], "Owners hate double-booking")
            s2.close()

    def test_none_fields_ignored(self):
        rid, a = self.s.add(rec(audience=None, product=None))
        self.assertEqual(a, "created")


if __name__ == "__main__":
    unittest.main()
