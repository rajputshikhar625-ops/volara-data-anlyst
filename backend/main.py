import os
import io
import re
import sqlite3
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from .database import db_manager
from .ai_engine import ai_engine
from .cleaner import cleaner

load_dotenv()

app = FastAPI(
    title="Aurlex Insights API",
    version="2.0.0",
    description="Multi-file, cleaning, filtering, disambiguation - DuckDB + Gemini"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NaturalLanguageQuery(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    table_name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    disambiguation_context: Optional[Dict[str, str]] = None
    chat_history: List[Dict[str, str]] = Field(default_factory=list, max_length=12)

class SQLExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=6)

class CleanRequest(BaseModel):
    table_name: str
    operations: List[str] = Field(default_factory=lambda: ["trim", "dedupe", "null_fill", "type_fix"])

class FilterSortRequest(BaseModel):
    table_name: str
    filters: Optional[List[Dict[str, Any]]] = None
    sort_by: Optional[str] = None
    sort_dir: str = "asc"
    page: int = 1
    page_size: int = 100

def validate_table_exists(table_name: str):
    tables = db_manager.list_tables()["name"].tolist()
    if table_name not in tables:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found. Available: {tables}")
    return table_name

def read_one_file(file: UploadFile, contents: bytes) -> pd.DataFrame:
    name = file.filename.lower()
    if name.endswith('.csv'):
        # try to detect encoding
        try:
            return pd.read_csv(io.BytesIO(contents))
        except:
            return pd.read_csv(io.BytesIO(contents), encoding='latin1')
    elif name.endswith(('.xls','.xlsx')):
        return pd.read_excel(io.BytesIO(contents))
    elif name.endswith('.parquet'):
        return pd.read_parquet(io.BytesIO(contents))
    elif name.endswith('.json'):
        return pd.read_json(io.BytesIO(contents))
    elif name.endswith('.sql') or name.endswith('.sqlite') or name.endswith('.db'):
        # If .sql file contains CREATE TABLE + INSERT, try parse as sqlite dump
        # For simplicity, if it's sqlite file binary, load via sqlite3
        tmp_path = f"/tmp/{file.filename}"
        with open(tmp_path, 'wb') as f:
            f.write(contents)
        try:
            conn = sqlite3.connect(tmp_path)
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
            if not tables.empty:
                # Load first table
                tname = tables.iloc[0]['name']
                df = pd.read_sql(f"SELECT * FROM {tname}", conn)
                conn.close()
                os.remove(tmp_path)
                return df
        except Exception as e:
            # Try to parse raw SQL text for data rows? fallback
            pass
        # If text sql with INSERTs, try extract with pandas? fail gracefully
        raise HTTPException(status_code=400, detail=f"SQL file parsing failed: {file.filename}. Export your SQL as CSV or provide .sqlite file with one table.")
    else:
        # raw text / tsv
        try:
            return pd.read_csv(io.BytesIO(contents), sep=None, engine='python')
        except:
            raise HTTPException(status_code=400, detail=f"Unsupported file {file.filename}")

@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        df = read_one_file(file, contents)
        if df.empty:
            raise HTTPException(status_code=400, detail="Empty dataset")
        raw_name = os.path.splitext(file.filename)[0]
        safe_table = db_manager.register_dataframe(raw_name, df)
        return {
            "status": "success",
            "table_name": safe_table,
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "preview": df.head(5).to_dict(orient="records"),
            "null_counts": df.isnull().sum().to_dict(),
            "clean_report": cleaner.quick_report(df)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-multi")
async def upload_multi(files: List[UploadFile] = File(...), merge_how: str = Query("concat", enum=["concat","union","separate"])):
    """
    Upload 2-3 Excel/CSV/SQL files at once.
    concat: stack rows (same schema)
    union: stack and dedupe
    separate: keep as separate tables
    """
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Upload at least 2 files for multi")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Max 10 files at once")
    
    dfs = []
    table_names = []
    for file in files:
        contents = await file.read()
        try:
            df = read_one_file(file, contents)
            dfs.append(df)
            table_names.append(file.filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"{file.filename}: {str(e)}")
    
    try:
        if merge_how in ["concat","union"]:
            # Align columns - union of all columns
            all_cols = set()
            for d in dfs:
                all_cols.update(d.columns)
            all_cols = list(all_cols)
            aligned = []
            for d in dfs:
                for c in all_cols:
                    if c not in d.columns:
                        d[c] = pd.NA
                aligned.append(d[all_cols])
            combined = pd.concat(aligned, ignore_index=True)
            if merge_how == "union":
                combined = combined.drop_duplicates()
            safe_table = db_manager.register_dataframe("combined_dataset", combined)
            return {
                "status": "success",
                "mode": merge_how,
                "table_name": safe_table,
                "rows": len(combined),
                "columns": list(combined.columns),
                "source_files": table_names,
                "preview": combined.head(5).to_dict(orient="records"),
                "clean_report": cleaner.quick_report(combined)
            }
        else:
            # separate tables
            results = []
            for df, fname in zip(dfs, table_names):
                safe = db_manager.register_dataframe(fname, df)
                results.append({"file": fname, "table": safe, "rows": len(df)})
            return {"status": "success", "mode": "separate", "tables": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clean")
async def clean_table(req: CleanRequest):
    validate_table_exists(req.table_name)
    try:
        df = db_manager.get_dataframe(req.table_name)
        cleaned_df, report = cleaner.clean(df, req.operations)
        safe = db_manager.register_dataframe(req.table_name + "_cleaned", cleaned_df)
        # Also replace original
        db_manager.register_dataframe(req.table_name, cleaned_df)
        return {
            "status": "cleaned",
            "table_name": req.table_name,
            "cleaned_table": safe,
            "report": report,
            "rows_after": len(cleaned_df),
            "preview": cleaned_df.head(5).to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/filter-sort")
async def filter_sort(req: FilterSortRequest):
    validate_table_exists(req.table_name)
    try:
        df = db_manager.get_dataframe(req.table_name)
        # Apply filters: [{"column":"dept","op":"=","value":"HR"}]
        if req.filters:
            for f in req.filters:
                col = f.get("column")
                op = f.get("op","=")
                val = f.get("value")
                if col not in df.columns:
                    continue
                if op == "=":
                    df = df[df[col]==val]
                elif op == "!=":
                    df = df[df[col]!=val]
                elif op == "contains":
                    df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
                elif op == ">":
                    df = df[df[col]>val]
                elif op == "<":
                    df = df[df[col]<val]
        if req.sort_by and req.sort_by in df.columns:
            df = df.sort_values(by=req.sort_by, ascending=(req.sort_dir=="asc"))
        
        total = len(df)
        start = (req.page-1)*req.page_size
        end = start + req.page_size
        page_df = df.iloc[start:end]
        
        return {
            "total_rows": total,
            "page": req.page,
            "page_size": req.page_size,
            "data": page_df.to_dict(orient="records"),
            "columns": list(df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai-query")
async def ai_query(payload: NaturalLanguageQuery):
    validate_table_exists(payload.table_name)
    try:
        # First, check for ambiguity
        ambiguity = ai_engine.check_ambiguity(payload.table_name, payload.query, payload.disambiguation_context)
        if ambiguity.get("needs_clarification"):
            return {
                "status": "needs_clarification",
                "questions": ambiguity["questions"],
                "options": ambiguity["options"],
                "sql_query": None,
                "data": []
            }
        
        schema_df = db_manager.get_schema(payload.table_name)
        schema_str = schema_df.to_string()
        # Include disambiguation context in prompt
        extra_ctx = ""
        if payload.disambiguation_context:
            extra_ctx = f"\nDisambiguation context provided by user: {payload.disambiguation_context}"
        
        sql_query = ai_engine.text_to_sql(payload.table_name, schema_str, payload.query + extra_ctx, payload.chat_history)
        result_df = db_manager.execute_query(sql_query)
        insight = ai_engine.generate_insight(result_df.head(10).to_string(), payload.query)

        return {
            "status": "success",
            "sql_query": sql_query,
            "data": result_df.to_dict(orient="records"),
            "row_count": len(result_df),
            "insight": insight
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sql")
async def direct_sql(req: SQLExecuteRequest):
    try:
        df = db_manager.execute_query(req.sql)
        return {"data": df.to_dict(orient="records"), "row_count": len(df)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tables")
def list_tables():
    df = db_manager.list_tables()
    return {"tables": df["name"].tolist() if not df.empty else []}

@app.get("/api/schema/{table_name}")
def get_schema(table_name: str):
    validate_table_exists(table_name)
    df = db_manager.get_schema(table_name)
    sample = db_manager.get_dataframe(table_name).head(3).to_dict(orient="records")
    return {"schema": df.to_dict(orient="records"), "sample": sample}

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "engine": f"DuckDB 0.10.0 + {ai_engine.model_name}",
        "ai_enabled": ai_engine.enabled,
        "tables_loaded": len(db_manager.list_tables()),
        "version": "2.1.0 - multi-upload + cleaning + disambiguation"
    }



