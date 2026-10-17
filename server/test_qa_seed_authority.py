import unittest
from unittest.mock import patch
from decimal import Decimal
import manual_overrides as authority

class Cursor:
    def __init__(self, existing):
        self.existing = existing
        self.writes = []
    def execute(self, sql, params=None):
        if sql.lstrip().startswith("INSERT"):
            self.writes.append(params)
    def fetchone(self):
        return self.existing

class SeedAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.seed = dict(ean_upc="81009389133", article_number="3467050",
                         selling_uom_code=None, base_uom_code=None,
                         base_qty_per_selling_unit=None, source_note="OLD_IDENTITY_SEED")
    def apply(self, existing):
        cursor = Cursor(existing)
        with patch.object(authority, "SEED_OVERRIDES", [self.seed]), patch.object(authority, "ensure_override_table"):
            changed = authority.seed_confirmed_overrides(cursor)
        return changed, cursor.writes
    def test_confirmed_answer_survives_blank_seed_and_repeated_replay(self):
        answer = dict(self.seed, override_status="CONFIRMED", selling_uom_code="PACK",
                      base_uom_code="LB", base_qty_per_selling_unit=Decimal("5"),
                      source_note="BACKOFFICE_QA_USER_CONFIRMED: 1 pack = 5LB")
        self.assertEqual(self.apply(answer), (0, []))
        self.assertEqual(self.apply(answer), (0, []))
    def test_confirmed_family_survives_stale_seed(self):
        answer = dict(self.seed, override_status="CONFIRMED", article_number="1348021",
                      source_note="BACKOFFICE_QA_USER_CONFIRMED: correct receiving family")
        self.assertEqual(self.apply(answer), (0, []))
    def test_missing_seed_is_inserted(self):
        changed, writes = self.apply(None)
        self.assertEqual((changed, len(writes)), (1, 1))
    def test_identical_legacy_seed_stays_idempotent(self):
        self.assertEqual(self.apply(dict(self.seed, override_status="CONFIRMED")), (0, []))
    def test_legacy_and_unconfirmed_records_can_still_refresh(self):
        for row in [dict(self.seed, override_status="CONFIRMED", article_number="OLD"),
                    dict(self.seed, override_status="SUPERSEDED", source_note="BACKOFFICE_QA_USER_CONFIRMED: old")]:
            changed, writes = self.apply(row)
            self.assertEqual((changed, len(writes)), (1, 1))

if __name__ == "__main__":
    unittest.main()
