import os
import logging
import json
from typing import List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("chatbot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID", "109fc5EkBwdHc4pZYEzYMTqknxw0ImGGiI3kgmIo95Vc")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Sheet1")

service = None

FINANCIAL_MAPPING = {
    "income_protection": "Family Income",
    "medical_expenses": "Medical Expenses",
    "education": "Education",
    "wealth_building": "Wealth Building",
    "retirement": "Retirement",
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
        
        if normalized in LIFE_STAGE_MAPPING:
            mapped_row.append(LIFE_STAGE_MAPPING[normalized])
        elif normalized in FINANCIAL_MAPPING:
            mapped_row.append(FINANCIAL_MAPPING[normalized])
        elif normalized in COVERAGE_MAPPING:
            mapped_row.append(COVERAGE_MAPPING[normalized])
        else:
            mapped_row.append(str(cell).strip())
    return mapped_row

def get_access_token():
    """Get access token from Replit connection settings."""
    import requests
    
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    x_replit_token = None
    
    if os.getenv("REPL_IDENTITY"):
        x_replit_token = "repl " + os.getenv("REPL_IDENTITY")
    elif os.getenv("WEB_REPL_RENEWAL"):
        x_replit_token = "depl " + os.getenv("WEB_REPL_RENEWAL")
    
    if not x_replit_token:
        raise Exception("X_REPLIT_TOKEN not found for repl/depl")
    
    url = f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-sheet"
    headers = {
        "Accept": "application/json",
        "X_REPLIT_TOKEN": x_replit_token
    }
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    connection_settings = data.get("items", [{}])[0]
    
    if not connection_settings:
        raise Exception("Google Sheet not connected")
    
    access_token = (
        connection_settings.get("settings", {}).get("access_token") or
        connection_settings.get("settings", {}).get("oauth", {}).get("credentials", {}).get("access_token")
    )
    
    if not access_token:
        raise Exception("Access token not found in connection settings")
    
    return access_token

def init_sheets_service():
    """Initialize Google Sheets API service with Replit-managed OAuth credentials."""
    global service
    
    try:
        access_token = get_access_token()
        
        credentials = Credentials(token=access_token)
        
        service = build("sheets", "v4", credentials=credentials)
        logger.info("✅ Google Sheets service initialized successfully with Replit connection")
        return service
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google Sheets service: {e}")
        raise

def append_row_to_sheet(row: List[str]) -> None:
    """
    Add a single row to Google Sheet at the next empty row.
    Automatically maps financial, life stage, coverage, and plan keywords to readable labels.
    """
    try:
        if not row or not isinstance(row, list):
            raise ValueError("Row must be a non-empty list of strings")
        
        mapped_row = map_keywords(row)
        
        sheet_service = init_sheets_service()
        
        sheet = sheet_service.spreadsheets()
        body = {"values": [mapped_row]}
        
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:A",
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

if __name__ == "__main__":
    try:
        test_row = ["Ely", "sgsa", "tabung_warisan", "perlindungan_combo", "2", "Starting Family"]
        append_row_to_sheet(test_row)
    except Exception as err:
        logger.error(f"Error in main: {err}")
