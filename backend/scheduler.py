
import os
import requests

def send_slack_alert(message: str):
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook or "your_" in webhook:
        print(f"[Slack] Would send: {message}")
        return
    try:
        requests.post(webhook, json={"text": message}, timeout=5)
    except Exception as e:
        print(f"Slack failed: {e}")
