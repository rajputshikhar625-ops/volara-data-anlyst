import os
import duckdb
import pandas as pd
import uuid
from typing import Optional
from supabase import create_client, Client

class DatabaseManager:
    """
    Handles local DuckDB + optional Supabase persistence
    Production-grade singleton pattern
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.con = duckdb.connect(database=':memory:', read_only=False)
            cls._instance.supabase_client: Optional[Client] = None
            cls._instance._init_supabase()
        return cls._instance

    def _init_supabase(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key and "your_" not in url:
            try:
                self.supabase_client = create_client(url, key)
            except Exception as e:
                print(f"[Supabase] Init failed: {e}")

    def register_dataframe(self, table_name: str, df: pd.DataFrame):
        # Sanitize table name
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in table_name.lower())
        if not safe_name[0].isalpha():
            safe_name = f"t_{safe_name}"
        # Register the frame under a temporary name, then remove the view so
        # SHOW TABLES returns each uploaded dataset only once.
        source_name = f"_upload_{uuid.uuid4().hex}"
        self.con.register(source_name, df)
        try:
            self.con.execute(f"CREATE OR REPLACE TABLE {safe_name} AS SELECT * FROM {source_name}")
        finally:
            self.con.unregister(source_name)
        return safe_name

    def execute_query(self, sql: str) -> pd.DataFrame:
        # Basic SQL injection guard - block DDL/DML beyond SELECT
        forbidden = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER", "GRANT"]
        # Allow only SELECT + DESCRIBE / SHOW
        stripped = sql.strip().upper()
        if not (stripped.startswith("SELECT") or stripped.startswith("DESCRIBE") or stripped.startswith("SHOW")):
            # Still allow DESCRIBE for schema inspection
            if not any(stripped.startswith(k) for k in ["SELECT", "DESCRIBE", "SHOW"]):
                raise ValueError("Only SELECT queries are allowed")
        return self.con.execute(sql).fetchdf()

    def list_tables(self):
        return self.con.execute("SHOW TABLES").fetchdf()

    def get_dataframe(self, table_name: str) -> pd.DataFrame:
        return self.con.execute(f"SELECT * FROM {table_name}").fetchdf()

    def get_schema(self, table_name: str) -> pd.DataFrame:
        return self.con.execute(f"DESCRIBE {table_name}").fetchdf()

db_manager = DatabaseManager()
