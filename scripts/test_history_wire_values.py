"""History wire-format regression tests; exact business-value verification remains required."""
import pathlib
import runpy
import unittest

ns = runpy.run_path(str(pathlib.Path(__file__).resolve().parents[1] / "server" / "price_history_analysis.py"))
verify = ns["verify_history_tables"]
date_value = ns["_history_date_value"]
compare = ns["_history_compare_value"]

class WireTests(unittest.TestCase):
    def test_google_date_encodings_match_calendar_date(self):
        for value in [46314, 46314.0, "2026-10-19T07:00:00.000Z", "2026-10-19"]:
            self.assertEqual(date_value(value, "date"), "2026-10-19")
        self.assertEqual(date_value("2026-10-19T08:00:00Z", "built_at"), "2026-10-19T08:00:00Z")

    def test_numeric_upcs_do_not_use_scientific_notation(self):
        self.assertEqual(compare(24056900000), compare("24056900000"))
        self.assertNotEqual(compare(12345), compare("0012345"))

    def test_live_shape_dates_and_ids_verify(self):
        header = ["upc", "date", "cost_date", "current_cost", "valid", "data_through"]
        expected = {"ANALYSIS_UPC_DAILY": [header, ["1077738333", "2026-08-27", "2026-09-25", 13.285714, False, "2026-10-18"]]}
        actual = [header, [1077738333, "2026-08-27T07:00:00.000Z", "2026-09-25T07:00:00.000Z", 13.285714, False, "2026-10-18T07:00:00.000Z"]]
        self.assertTrue(verify(expected, lambda *args: actual)["pass"])

    def test_real_date_cost_and_id_changes_are_rejected(self):
        header = ["upc", "date", "current_cost"]
        expected = {"ANALYSIS_UPC_DAILY": [header, ["24056900000", "2026-10-19", 13.25]]}
        for row, column in [
            ([24056900000, 46313, 13.25], "date"),
            ([24056900000, 46314, 13.26], "current_cost"),
            ([24056900001, 46314, 13.25], "upc"),
        ]:
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, column):
                verify(expected, lambda *args: [header, row])

    def test_retained_dates_are_canonical_before_rebuilding(self):
        headers = ns["HEADERS"]
        def reader(title, start, end, width):
            if start == 1:return [headers[title]]
            if title != "ANALYSIS_UPC_DAILY" or start != 2:return []
            row = [""] * width
            row[headers[title].index("upc")] = 24056900000
            row[headers[title].index("date")] = "2026-10-19T07:00:00.000Z"
            return [row]
        result = ns["read_retained_tables"](reader)
        row = result["ANALYSIS_UPC_DAILY"][1]
        self.assertEqual(row[headers["ANALYSIS_UPC_DAILY"].index("date")], "2026-10-19")

    def test_equivalent_numeric_cost_preserves_old_lineage(self):
        h = ["upc", "date", "cost", "source_revision", "data_through"]
        old = {"ANALYSIS_UPC_DAILY": [h, [24056900000, "2026-10-18", 13, "old", "2026-10-18"]]}
        new = {"ANALYSIS_UPC_DAILY": [h, ["24056900000", "2026-10-18", 13.0, "new", "2026-10-19"]]}
        result = ns["preserve_unchanged_lineage"](new, old)
        self.assertEqual(result["ANALYSIS_UPC_DAILY"][1][-2:], ["old", "2026-10-18"])

if __name__ == "__main__":
    unittest.main()
