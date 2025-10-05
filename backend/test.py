import requests
import time

URL = "http://127.0.0.1:8000/api/events"

# Sample payload
payload = {
    "userId": "u1",
    "elementId": "submit",
    "timestamp": None,  # will be filled dynamically
    "eventType": "click",
    "metadata": {}
}

# Send 3 quick clicks
for i in range(3):
    payload["timestamp"] = time.time()
    resp = requests.post(URL, json=payload)
    print(f"Click {i+1} response:", resp.json())
    time.sleep(1)  # 1 sec gap between clicks
