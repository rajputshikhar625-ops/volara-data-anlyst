
"""
Aurlex Connectors - For institutions
Google Sheets, Postgres, MySQL, Supabase - live sync into DuckDB
"""
import os
import pandas as pd
from typing import Optional

class ConnectorManager:
    def from_google_sheet(self, sheet_url: str, creds_json: Optional[str] = None) -> pd.DataFrame:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            creds_path = creds_json or os.getenv("GOOGLE_CREDS_PATH", "creds.json")
            scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
            client = gspread.authorize(creds)
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.get_worksheet(0)
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        except ImportError:
            raise RuntimeError("Install gspread: pip install gspread google-auth")
        except Exception as e:
            raise RuntimeError(f"Sheets connector failed: {e}")

    def from_postgres(self, conn_str: str, query: str) -> pd.DataFrame:
        from sqlalchemy import create_engine
        engine = create_engine(conn_str)
        return pd.read_sql(query, engine)

connector_manager = ConnectorManager()
