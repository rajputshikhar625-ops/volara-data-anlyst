
import os
import re
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

load_dotenv()

class AIEngine:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and "your_" not in api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.enabled = True
        else:
            self.enabled = False
            self.model = None

    def _clean_sql(self, raw_text: str) -> str:
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1)
        else:
            sql = raw_text
        sql = sql.strip().rstrip(";")
        return sql.strip()

    def check_ambiguity(self, table_name: str, user_query: str, context: Optional[Dict[str,str]] = None) -> Dict[str, Any]:
        """
        Core fix for Rahul in HR and Tech problem.
        If query mentions a name that appears in multiple groups, ask clarification.
        """
        from .database import db_manager
        try:
            df = db_manager.get_dataframe(table_name)
        except:
            return {"needs_clarification": False}
        
        q_lower = user_query.lower()
        
        # Detect potential name columns: columns with 'name', 'employee', 'user'
        name_cols = [c for c in df.columns if any(k in c.lower() for k in ['name','employee','person','user'])]
        dept_cols = [c for c in df.columns if any(k in c.lower() for k in ['dept','department','team','division'])]
        
        if not name_cols:
            return {"needs_clarification": False}
        
        # Find all names in query that exist in data
        questions = []
        options = {}
        
        # Simple entity extraction: look for values that match data
        for ncol in name_cols[:2]:  # check first 2 name cols
            unique_names = df[ncol].dropna().astype(str).unique().tolist()
            # Find which names appear in query
            for uname in unique_names:
                if len(uname) < 3:
                    continue
                if uname.lower() in q_lower:
                    # Check if this name appears in multiple departments/groups
                    if dept_cols:
                        for dcol in dept_cols[:2]:
                            groups = df[df[ncol].astype(str).str.lower() == uname.lower()][dcol].dropna().unique().tolist()
                            if len(groups) > 1:
                                # Ambiguity found! e.g., Rahul in HR and Tech
                                if context and any(str(g).lower() in str(v).lower() for v in (context or {}).values() for g in groups):
                                    continue  # already clarified
                                questions.append(f"I found '{uname}' in multiple {dcol}s: {', '.join(map(str, groups))}. Which one did you mean?")
                                options[f"{ncol}_{uname}_{dcol}"] = {"name_col": ncol, "name_value": uname, "dept_col": dcol, "departments": groups}
        
        # Also check for generic ambiguous queries like "Rahul's salary" without dept
        if not questions and dept_cols and name_cols:
            # If query mentions a name but not dept, and that name has multiple depts, ask
            for ncol in name_cols:
                # Extract potential first names from query via regex (capitalized words)
                potential_names = re.findall(r"\b[A-Z][a-z]+\b", user_query)
                for pname in potential_names:
                    matches = df[df[ncol].astype(str).str.lower().str.contains(pname.lower(), na=False)]
                    if len(matches) > 0:
                        for dcol in dept_cols:
                            if matches[dcol].nunique() > 1:
                                groups = matches[dcol].unique().tolist()
                                questions.append(f"'{pname}' appears in multiple {dcol}s ({', '.join(map(str, groups))}). Please specify which department?")
                                options[f"{pname}_{dcol}"] = {"departments": groups, "dept_col": dcol}
                                break
        
        if questions:
            return {"needs_clarification": True, "questions": questions[:3], "options": options}
        
        return {"needs_clarification": False}

    def text_to_sql(self, table_name: str, schema_str: str, user_query: str) -> str:
        if not self.enabled:
            raise RuntimeError("Gemini API Key not configured")
        
        system_prompt = f"""
You are an expert DuckDB SQL generator for Aurlex Insights.
Table: {table_name}
Schema: {schema_str}
Rules:
1. Use DuckDB dialect, only SELECT.
2. Return ONLY SQL in code block.
3. Handle NULLs safely.
4. If user mentions department/name, include WHERE with exact match.
5. User Request: "{user_query}"
"""
        response = self.model.generate_content(system_prompt)
        return self._clean_sql(response.text)

    def generate_insight(self, df_head: str, query: str) -> str:
        if not self.enabled:
            return "AI Insights disabled"
        prompt = f"Data sample: {df_head}\nQuery: {query}\nProvide 3 bullet insights with numbers."
        try:
            res = self.model.generate_content(prompt)
            return res.text
        except Exception as e:
            return f"Insight failed: {e}"

ai_engine = AIEngine()
