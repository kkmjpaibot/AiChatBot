import os
import logging
from typing import List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------------- Logging Setup ----------------
logger = logging.getLogger("chatbot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ---------------- Google Sheets Setup ----------------
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credential.json")
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID", "109fc5EkBwdHc4pZYEzYMTqknxw0ImGGiI3kgmIo95Vc")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Sheet1")

credentials = None
service = None

# ---------------- Mapping Dictionaries ----------------
FINANCIAL_MAPPING = {
    "income_protection": "Family Income",
    "medical_expenses": "Medical Expenses",
    "education": "Education",
    "wealth_building": "Wealth Building",
    "retirement": "Retirement",

    # ✅ New plan name mappings
    "sgsa": "Satu Gaji Satu Harapan",
    "tabung_warisan": "Tabung Warisan",
    "mdak": "Tabung Warisan",
    "tabung_perubatan": "Tabung Perubatan",
    "perlindungan_combo": "Perlindungan Combo"
}

LIFE_STAGE_MAPPING = {
    "starting_family": "Starting Family",
    "raising_children": "Raising Children",
    "home": "Home",
    "pre_retirement": "Pre Retirement",
    "single": "Single",
    "retired": "Retired"
}

COVERAGE_MAPPING = {
    "1": "Basic",
    "2": "Medium",
    "3": "Comprehensive"
}

# ---------------- Keyword Mapping Function ----------------
def normalize_keyword(text: str) -> str:
    """Normalize text for matching: lowercase + replace spaces and hyphens with underscores."""
    return str(text).strip().lower().replace(" ", "_").replace("-", "_")

def map_keywords(row: List[str]) -> List[str]:
    """
    Map known financial, life stage, and coverage keywords to readable labels.
    - Case-insensitive
    - Ignores spaces, hyphens, and underscores
    """
    mapped_row = []
    for cell in row:
        normalized = normalize_keyword(cell)

        # Check life stage
        if normalized in LIFE_STAGE_MAPPING:
            mapped_row.append(LIFE_STAGE_MAPPING[normalized])
        # Check financial or plan mappings
        elif normalized in FINANCIAL_MAPPING:
            mapped_row.append(FINANCIAL_MAPPING[normalized])
        # Check coverage levels (1, 2, 3)
        elif normalized in COVERAGE_MAPPING:
            mapped_row.append(COVERAGE_MAPPING[normalized])
        else:
            mapped_row.append(str(cell).strip())  # keep original if no mapping found
    return mapped_row

# ---------------- Google Sheets API Init ----------------
def init_sheets_service():
    """Initialize Google Sheets API service with Service Account credentials."""
    global credentials, service
    if service is not None:
        return service

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=credentials)
        logger.info("✅ Google Sheets service initialized successfully")
        return service
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google Sheets service: {e}")
        raise

# ---------------- Append Row ----------------
def append_row_to_sheet(row: List[str]) -> None:
    """
    Add a single row to Google Sheet at the next empty row.
    Automatically maps financial, life stage, coverage, and plan keywords to readable labels.
    """
    try:
        if not row or not isinstance(row, list):
            raise ValueError("Row must be a non-empty list of strings")

        # 🔁 Convert terms before saving
        mapped_row = map_keywords(row)

        if not service:
            init_sheets_service()

        sheet = service.spreadsheets()
        body = {"values": [mapped_row]}

        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:A",   # ✅ append to bottom automatically
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()

        updates = result.get("updates", {})
        updated_rows = updates.get("updatedRows", 0)
        logger.info(
            f"✅ Appended {updated_rows} row(s) to sheet '{SHEET_NAME}' "
            f"in spreadsheet '{SPREADSHEET_ID}'. Data: {mapped_row}"
        )
    except HttpError as http_err:
        logger.error(f"❌ HTTP error while appending row: {http_err}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error while appending row: {e}")
        raise

# ---------------- Example Usage ----------------
if __name__ == "__main__":
    try:
        # Example row (you can change any case or add spaces - it will still map)
        test_row = ["Ely", "sgsa", "tabung_warisan", "perlindungan_combo", "2", "Starting Family"]
        append_row_to_sheet(test_row)
    except Exception as err:
        logger.error(f"Error in main: {err}")
