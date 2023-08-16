import string
import requests
import json
import random
from requests.adapters import HTTPAdapter
from config import DOMAIN, TELEGRAM_TOKEN

requests_ses = requests.Session()
requests_ses.mount("https://api.telegram.org", HTTPAdapter(max_retries=5))


def apiCall(method, parameters):
    r = requests_ses.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}",
        timeout=3,
        data=parameters,
    )
    if r.status_code == 200:
        result = r.json()
        if result["ok"] != True:
            print(f"Error: {result['description']}")
            return None
        return result["result"]
    print(f"Network error:{r.text}")
    return None


SECRET = "".join(
    random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
    for _ in range(32)
)

try:
    requests_ses.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
        timeout=10,
        data={
            "url": DOMAIN,
            "max_connections": 1,
            "allowed_updates": json.dumps(
                ["message", "chat_join_request", "chat_member", "callback_query"]
            ),
            "drop_pending_updates": True,
            "secret_token": SECRET,
        },
    )
    print("Webhook is set!")
except:
    print("Failed to setup webhook")
    exit(1)
