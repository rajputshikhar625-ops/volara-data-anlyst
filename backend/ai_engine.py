
import os
import re
import pandas as pd
import requests
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

load_dotenv()

class AIEngine:
    def __init__(self, api_key=None, model_name=None, http_post=None):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.http_post = http_post or requests.post
        self.enabled = bool(self.api_key and "your_" not in self.api_key.lower())

    def generate_text(self, prompt):
        if not self.enabled:
            raise RuntimeError("AI is not enabled. Add a Gemini API key in the local .env file.")

        models = list(dict.fromkeys([self.model_name, "gemini-3.6-flash", "gemini-3.5-flash-lite"]))
        transient_errors = []
        missing_models = []
        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            try:
                response = self.http_post(
                    url,
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=25,
                )
            except requests.Timeout:
                transient_errors.append(f"{model_name}: request timed out")
                continue

            if response.status_code in {404, 429, 503}:
                try:
                    detail = response.json().get("error", {}).get("message", getattr(response, "text", ""))
                except (AttributeError, ValueError):
                    detail = getattr(response, "text", "")
                transient_errors.append(f"{model_name} ({response.status_code}): {detail}")
                if response.status_code == 404:
                    missing_models.append(model_name)
                continue
            if response.status_code >= 400:
                try:
                    detail = response.json().get("error", {}).get("message", response.text)
                except (AttributeError, ValueError):
                    detail = getattr(response, "text", "Google returned an error.")
                raise RuntimeError(f"Gemini request failed ({response.status_code}): {detail}")

            payload = response.json()
            candidates = payload.get("candidates", [])
            parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
            text = "\n".join(part.get("text", "") for part in parts if part.get("text"))
            if not text:
                raise RuntimeError("Gemini returned an empty answer. Try asking in a different way.")
            return text

        tried = ", ".join(models)
        last_error = transient_errors[-1] if transient_errors else "No response from Google."
        if len(missing_models) == len(models):
            raise RuntimeError(
                f"Google could not find these Gemini models for this key: {tried}. "
                "Check that the key is a Gemini API key and that GEMINI_MODEL is correct."
            )
        raise RuntimeError(
            f"Gemini is busy or unavailable right now. Tried {tried}. "
            f"You can change GEMINI_MODEL in .env or try again later. Details: {last_error}"
        )
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

    def text_to_sql(self, table_name: str, schema_str: str, user_query: str, conversation_history=None) -> str:
        if not self.enabled:
            raise RuntimeError("AI is not enabled. Add a Gemini API key in the local .env file.")

        system_prompt = f"""
You help a beginner understand a dataset. Create one safe DuckDB SELECT query that answers the user's request.
Table: {table_name}
Schema: {schema_str}
Rules:
1. Return only SQL (a code block is okay), with SELECT only.
2. Use exact column names from the schema and handle missing values safely.
3. Keep results short and easy to explain.
4. Recent chat is context; answer the latest request, using its follow-up references.
User request: "{user_query}"
"""
        if conversation_history:
            recent = conversation_history[-6:]
            history_text = "\n".join(
                f"{item.get('role', 'user')}: {str(item.get('content', ''))[:500]}"
                for item in recent
                if isinstance(item, dict)
            )
            system_prompt += f"\nRecent conversation:\n{history_text}\n"
        return self._clean_sql(self.generate_text(system_prompt))

    def generate_insight(self, df_head: str, query: str) -> str:
        if not self.enabled:
            return "AI insights are turned off."
        prompt = (
            "Explain these query results in plain, friendly language for a beginner. "
            "Use only the numbers shown and say when the results are too limited to know. "
            f"Question: {query}\nResults:\n{df_head}\nGive up to three short findings."
        )
        try:
            return self.generate_text(prompt)
        except Exception as e:
            return f"I found the results, but couldn't write a summary: {e}"

ai_engine = AIEngine()





