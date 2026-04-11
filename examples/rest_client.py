"""REST API client example."""

import httpx
import json

API_URL = "http://localhost:8000"
API_KEY = "dev-key-change-in-prod"

logs = [
    "ERROR: Database connection failed",
    "ERROR: Retry attempt 1/3",
    "FATAL: Connection pool exhausted",
]

response = httpx.post(
    f"{API_URL}/triage",
    json={"log_lines": logs},
    headers={"X-API-Key": API_KEY},
)

print(response.json())
