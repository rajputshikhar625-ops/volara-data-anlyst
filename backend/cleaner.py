
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict

class DataCleaner:
    def quick_report(self, df: pd.DataFrame) -> Dict:
        return {
            "rows": len(df),
            "cols": len(df.columns),
            "nulls": int(df.isnull().sum().sum()),
            "duplicates": int(df.duplicated().sum()),
            "empty_strings": int((df.astype(str) == "").sum().sum()) if not df.empty else 0
        }
    
    def clean(self, df: pd.DataFrame, ops: List[str]) -> Tuple[pd.DataFrame, Dict]:
        report = []
        original_len = len(df)
        
        df = df.copy()
        
        if "trim" in ops:
            # Trim whitespace from all string columns
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip().replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
            report.append("Trimmed whitespace & normalized empty strings")
        
        if "dedupe" in ops:
            before = len(df)
            df = df.drop_duplicates()
            removed = before - len(df)
            report.append(f"Removed {removed} duplicate rows")
        
        if "null_fill" in ops:
            # For numeric, fill with median; for categorical, keep NA but report
            for col in df.columns:
                if df[col].isnull().sum() > 0:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        median = df[col].median()
                        df[col] = df[col].fillna(median)
                        report.append(f"Filled {col} nulls with median {median}")
        
        if "type_fix" in ops:
            # Try to convert object columns that look numeric/date
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Try numeric
                    try:
                        converted = pd.to_numeric(df[col], errors='coerce')
                        if converted.notna().sum() / len(df) > 0.8:
                            df[col] = converted
                            report.append(f"Converted {col} to numeric")
                            continue
                    except:
                        pass
                    # Try date
                    try:
                        converted = pd.to_datetime(df[col], errors='coerce')
                        if converted.notna().sum() / len(df) > 0.8:
                            df[col] = converted
                            report.append(f"Converted {col} to datetime")
                    except:
                        pass
        
        if "lower_headers" in ops:
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            report.append("Normalized column names")
        
        final_report = {
            "operations": ops,
            "details": report,
            "rows_before": original_len,
            "rows_after": len(df),
            "nulls_after": int(df.isnull().sum().sum())
        }
        return df, final_report

cleaner = DataCleaner()
