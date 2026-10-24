import unittest

from backend.ai_engine import AIEngine
from backend.main import NaturalLanguageQuery


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "Hello from Gemini"}]}}]}


class GeminiEngineTests(unittest.TestCase):
    def test_generate_text_uses_configured_supported_model_and_key_header(self):
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

        engine = AIEngine(api_key="local-test-key", model_name="gemini-3.8-flash", http_post=fake_post)
        result = engine.generate_text("Explain this dataset in one sentence.")

        self.assertEqual(result, "Hello from Gemini")
        self.assertEqual(calls[0][0], "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent")
        self.assertEqual(calls[0][1]["headers"]["x-goog-api-key"], "local-test-key")

    def test_follow_up_query_prompt_includes_recent_chat(self):
        calls = []

        def fake_post(url, **kwargs):
            calls.append(kwargs["json"]["contents"][0]["parts"][0]["text"])
            response = FakeResponse()
            response.json = lambda: {"candidates": [{"content": {"parts": [{"text": "```sql\\nSELECT Region FROM sales\\n```"}]}}]}
            return response

        engine = AIEngine(api_key="local-test-key", http_post=fake_post)
        engine.text_to_sql(
            "sales",
            "Region VARCHAR",
            "What about South?",
            [{"role": "assistant", "content": "North has the most sales."}],
        )
        self.assertIn("North has the most sales.", calls[0])
        self.assertIn("What about South?", calls[0])

    def test_model_not_found_error_gives_a_clear_model_setting_hint(self):
        class MissingModelResponse:
            status_code = 404
            text = "not found"

            def json(self):
                return {"error": {"message": "model not found"}}

        engine = AIEngine(api_key="local-test-key", http_post=lambda *args, **kwargs: MissingModelResponse())
        with self.assertRaisesRegex(RuntimeError, "GEMINI_MODEL"):
            engine.generate_text("hello")


    def test_transient_model_busy_error_tries_a_supported_fallback(self):
        urls = []

        class BusyResponse:
            status_code = 503

            def json(self):
                return {"error": {"message": "temporarily busy"}}

        def fake_post(url, **kwargs):
            urls.append(url)
            return BusyResponse() if len(urls) == 1 else FakeResponse()

        engine = AIEngine(api_key="local-test-key", model_name="gemini-3.8-flash", http_post=fake_post)
        self.assertEqual(engine.generate_text("hello"), "Hello from Gemini")
        self.assertIn("gemini-3.8-flash", urls[0])
        self.assertIn("gemini-3.6-flash", urls[1])
    def test_api_accepts_short_chat_history_for_follow_up_questions(self):
        request = NaturalLanguageQuery(
            query="What about South?",
            table_name="sales",
            chat_history=[{"role": "assistant", "content": "North was highest."}],
        )
        self.assertEqual(request.chat_history[0]["content"], "North was highest.")
if __name__ == "__main__":
    unittest.main()





