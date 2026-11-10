"""
tests/test_pdf_parser.py: Tests for weekly epidemiology bulletin ingestion.
Verifies parsing of all 26 units from valid bulletins, and correct rejection/flagging
of corrupted files. Uses temporary test fixtures if disk files are not present.
"""

import os
import tempfile
import unittest
from src.silentnode.ingest.pdf_parser import EpidemiologicalPDFParser, RAW_PDF_DIR

VALID_SAMPLE_CONTENT = """Epidemiology Unit, Ministry of Health, Sri Lanka
WEEKLY EPIDEMIOLOGICAL REPORT - Vol. 51 No. 18 (27th Apr - 03rd May 2024)

Table 1: Selected notifiable disease surveillance - Dengue Fever (DF / DHF)
District / RDHS Division             Cases Reported Current Week
Colombo                               284
Gampaha                               142
Kalutara                               68
Kandy                                  94
Matale                                 22
Nuwara Eliya                           12
Galle                                  51
Matara                                 38
Hambantota                             29
Jaffna                                 45
Kilinochchi                             7
Mannar                                  9
Vavuniya                               14
Mullaitivu                              6
Batticaloa                             32
Ampara                                 18
Kalmunai                               27
Trincomalee                            21
Kurunegala                             64
Puttalam                               35
Anuradhapura                           26
Polonnaruwa                            19
Badulla                                31
Monaragala                             15
Ratnapura                              58
Kegalle                                43
Total Dengue Cases:                   1209
"""

CORRUPTED_SAMPLE_CONTENT = """%PDF-1.4 [CORRUPTED HEADER STREAM]
Missing tables, incomplete OCR output
Unknown district 999
Colombo 12
"""

class TestPDFParser(unittest.TestCase):

    def setUp(self):
        self.parser = EpidemiologicalPDFParser()
        self.temp_files = []

        # Check if disk sample exists, otherwise create temporary fixture
        disk_valid = os.path.join(RAW_PDF_DIR, "wer_2024_w18.txt")
        if os.path.exists(disk_valid):
            self.valid_bulletin = disk_valid
        else:
            tf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            tf.write(VALID_SAMPLE_CONTENT)
            tf.close()
            self.valid_bulletin = tf.name
            self.temp_files.append(tf.name)

        disk_corrupt = os.path.join(RAW_PDF_DIR, "corrupted_bulletin.txt")
        if os.path.exists(disk_corrupt):
            self.corrupted_bulletin = disk_corrupt
        else:
            tf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            tf.write(CORRUPTED_SAMPLE_CONTENT)
            tf.close()
            self.corrupted_bulletin = tf.name
            self.temp_files.append(tf.name)

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                os.remove(f)

    def test_valid_bulletin_parses_all_26_units(self):
        res = self.parser.ingest_weekly_report(self.valid_bulletin, expected_week=18)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["year"], 2024)
        self.assertEqual(res["week"], 18)
        self.assertFalse(res["staleness_flag"])
        self.assertEqual(len(res["cases"]), 26, "Must extract exactly 26 reporting units")

        # Check known district values from sample
        self.assertEqual(res["cases"]["Colombo"], 284)
        self.assertEqual(res["cases"]["Gampaha"], 142)
        self.assertEqual(res["cases"]["Kalmunai"], 27)

    def test_corrupted_bulletin_rejected_with_staleness(self):
        res = self.parser.ingest_weekly_report(self.corrupted_bulletin)
        self.assertNotEqual(res["status"], "SUCCESS")
        self.assertTrue(res["staleness_flag"], "Corrupted input must set staleness flag")
        # Should have either 'errors' or 'error'
        has_error = "errors" in res or "error" in res
        self.assertTrue(has_error)

if __name__ == "__main__":
    unittest.main()
