
import os
import duckdb
import pandas as pd
PERSIST_PATH = os.getenv("DUCKDB_PATH", "aurlex.duckdb")
con = duckdb.connect(PERSIST_PATH)

def save_as_parquet(df: pd.DataFrame, name: str) -> str:
    path = f"./parquet_cache/{name}.parquet"
    os.makedirs("./parquet_cache", exist_ok=True)
    df.to_parquet(path, index=False)
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM parquet_scan('{path}')")
    return path

def fast_summarize(table: str) -> pd.DataFrame:
    return con.execute(f"SUMMARIZE {table}").fetchdf()
