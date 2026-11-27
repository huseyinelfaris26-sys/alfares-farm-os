"""Push weather, disease, and fertilizer results into farmOS as logs.

Usage:
    python farmos_sync.py --log diagnosis --asset-id 1 --class Tomato___Early_blight
    python farmos_sync.py --log fertilizer --asset-id 3 --plan '{"N_kg": 24}'
"""

import argparse
import json
import os
import sys
from datetime import date

import requests

FARMOS_URL = os.getenv("FARMOS_URL", "http://localhost:8080").rstrip("/")
CLIENT_ID = os.getenv("FARMOS_CLIENT_ID", "sync_client")
CLIENT_SECRET = os.getenv("FARMOS_CLIENT_SECRET", "")

LOG_TYPES = {
    "weather": "obervation_weather",
    "diagnosis": "obervation_disease",
    "fertilizer": "input_fertilizer",
}


def get_token() -> str:
    if not CLIENT_SECRET:
        sys.exit("يجب ضبط FARMOS_CLIENT_SECRET")
    r = requests.post(
        f"{FARMOS_URL}/oauth/token",
        data={"grant_type": "client_credentials", "client_id": CLIENT_ID,
              "client_secret": CLIENT_SECRET},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def create_log(token: str, log_type: str, asset_id: int, note: str) -> dict:
    body = {
        "data": {
            "type": "log--" + log_type,
            "attributes": {
                "name": f"[AlFares Farm OS] {log_type} {date.today().isoformat()}",
                "timestamp": f"{date.today().isoformat()}T08:00:00+03:00",
                "status": "done",
                "notes": {"value": note, "format": "plain_text"},
            },
            "relationships": {"asset": {"data": [{"type": "asset--land", "id": asset_id}]}},
        }
    }
    r = requests.post(
        f"{FARMOS_URL}/api/logs/{log_type}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json",
        },
        data=json.dumps(body),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", choices=LOG_TYPES, required=True)
    parser.add_argument("--asset-id", type=int, required=True, help="معرّف الحقل (land asset) في farmOS")
    parser.add_argument("--note", default="")
    parser.add_argument("--class", dest="cls", default="")
    parser.add_argument("--plan", default="")
    args = parser.parse_args()

    if args.cls:
        args.note = f"تشخيص المرض: {args.cls}. {args.note}"
    if args.plan:
        args.note = f"خطة التسميد: {args.plan}. {args.note}"

    token = get_token()
    result = create_log(token, LOG_TYPES[args.log], args.asset_id, args.note)
    log_id = result.get("data", {}).get("id")
    print(f"تم إنشاء السجل في farmOS برقم: {log_id}")


if __name__ == "__main__":
    main()
