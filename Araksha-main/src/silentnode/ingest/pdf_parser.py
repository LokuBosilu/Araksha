"""
src/silentnode/ingest/pdf_parser.py: Weekly Epidemiology Report (WER) PDF parser
for Sri Lanka Epidemiology Unit (epid.gov.lk) with WHO SEARO fallback and staleness handling.
"""

import os
import re
import csv
import json
import datetime
from typing import Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
RAW_PDF_DIR = os.path.join(BASE_DIR, "data", "raw", "sample_pdfs")
LOOKUP_FILE = os.path.join(PROCESSED_DIR, "district_lookup.csv")

class EpidemiologicalPDFParser:
    def __init__(self, lookup_path: str = LOOKUP_FILE):
        self.canonical_map = {}
        if os.path.exists(lookup_path):
            with open(lookup_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    self.canonical_map[r["district_name"].lower()] = r["district_name"]
        # Common typos and variations in Epidemiology Unit bulletins
        self.aliases = {
            "kalmune": "Kalmunai",
            "kalmunai rdhs": "Kalmunai",
            "ampara rdhs": "Ampara",
            "hambanthota": "Hambantota",
            "nuwara-eliya": "Nuwara Eliya",
            "nuwaraeliya": "Nuwara Eliya",
        }

    def parse_text_stream(self, text_content: str) -> Tuple[Optional[int], Optional[int], Dict[str, int], List[str]]:
        """
        Parses text extracted from a WER dengue table.
        Returns: (year, epi_week, cases_by_district, error_log)
        """
        errors = []
        cases = {}

        # 1. Extract Year and Epi Week
        # Typical patterns: "Vol. 51 No. 18" or "Week 18 (27th Apr - 03rd May 2024)"
        year_match = re.search(r"202[0-9]", text_content)
        week_match = re.search(r"(?:Week|No\.)\s*([0-9]{1,2})", text_content, re.IGNORECASE)

        parsed_year = int(year_match.group(0)) if year_match else None
        parsed_week = int(week_match.group(1)) if week_match else None

        if not parsed_week:
            errors.append("Could not extract epi week number from header.")

        # 2. Extract District Row Lines
        lines = text_content.splitlines()
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            # Look for line matching: <DistrictName> ... <cases_int>
            tokens = line_clean.split()
            if len(tokens) >= 2:
                # Check possible multi-word district (e.g., Nuwara Eliya)
                candidate_name = None
                case_count = None

                if len(tokens) >= 3 and f"{tokens[0]} {tokens[1]}".lower() in self.canonical_map:
                    candidate_name = f"{tokens[0]} {tokens[1]}"
                    # Last token or token at column position
                    for tok in reversed(tokens[2:]):
                        if tok.isdigit():
                            case_count = int(tok)
                            break
                elif tokens[0].lower() in self.canonical_map:
                    candidate_name = tokens[0]
                    for tok in reversed(tokens[1:]):
                        if tok.isdigit():
                            case_count = int(tok)
                            break
                elif tokens[0].lower() in self.aliases:
                    candidate_name = self.aliases[tokens[0].lower()]
                    for tok in reversed(tokens[1:]):
                        if tok.isdigit():
                            case_count = int(tok)
                            break

                if candidate_name and case_count is not None:
                    canonical = self.canonical_map.get(candidate_name.lower(), candidate_name)
                    cases[canonical] = case_count

        # Validation: check coverage of 26 units
        missing_districts = [d for d in self.canonical_map.values() if d not in cases]
        if missing_districts:
            errors.append(f"Missing {len(missing_districts)} units: {missing_districts[:5]}...")

        return parsed_year, parsed_week, cases, errors

    def fetch_who_searo_fallback(self, year: int, week: int) -> Optional[Dict[str, int]]:
        """
        Secondary path using WHO SEARO dengue dashboard.
        Returns None with explicit logging rather than faking data when API endpoint is unavailable.
        """
        print(f"[WHO SEARO Fallback] Querying regional repository for {year}-W{week:02d}...")
        # Note: WHO SEARO provides aggregated country-level dashboards;
        # subnational 26-unit MOH data is published via Sri Lanka Epidemiology Unit PDF bulletins.
        return None

    def ingest_weekly_report(
        self,
        pdf_path: str,
        expected_week: Optional[int] = None
    ) -> Dict:
        """
        Attempts ingestion: Primary (PDF) -> Fallback (WHO SEARO) -> Last Valid (Staleness Flag).
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not os.path.exists(pdf_path):
            return {
                "status": "FAILED",
                "source": "None",
                "timestamp": timestamp,
                "error": f"File not found: {pdf_path}",
                "staleness_flag": True,
            }

        try:
            with open(pdf_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            year, week, cases, errors = self.parse_text_stream(content)

            if errors or (expected_week and week != expected_week):
                # Try fallback
                fallback_data = self.fetch_who_searo_fallback(year or 2024, week or 18)
                if fallback_data:
                    return {
                        "status": "FALLBACK_SUCCESS",
                        "source": "WHO_SEARO",
                        "timestamp": timestamp,
                        "year": year,
                        "week": week,
                        "cases": fallback_data,
                        "staleness_flag": False,
                    }
                else:
                    return {
                        "status": "VALIDATION_FAILED",
                        "source": "PDF_PRIMARY",
                        "timestamp": timestamp,
                        "year": year,
                        "week": week,
                        "errors": errors,
                        "staleness_flag": True,
                    }

            return {
                "status": "SUCCESS",
                "source": "PDF_PRIMARY",
                "timestamp": timestamp,
                "year": year,
                "week": week,
                "cases": cases,
                "units_count": len(cases),
                "staleness_flag": False,
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "source": "PDF_PRIMARY",
                "timestamp": timestamp,
                "error": str(e),
                "staleness_flag": True,
            }
