#!/usr/bin/env python3
"""
RTMP Stream Handler
Handles communication between RTMP server and Mem backend
"""

import sys
import os
import httpx
import json
from datetime import datetime

BACKEND_URL = os.environ.get("BACKEND_URL", "http://mem-backend:8000")


def notify_backend(event_type: str, stream_key: str, metadata: dict = None):
    """Notify the backend about stream events."""
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{BACKEND_URL}/api/streams/events",
                json={
                    "event_type": event_type,
                    "stream_key": stream_key,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": metadata or {},
                },
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Error notifying backend: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point for stream handler."""
    if len(sys.argv) < 3:
        print("Usage: stream_handler.py <event> <stream_key> [metadata_json]")
        sys.exit(1)

    event = sys.argv[1]
    stream_key = sys.argv[2]
    metadata = {}

    if len(sys.argv) > 3:
        try:
            metadata = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            print(f"Invalid metadata JSON: {sys.argv[3]}", file=sys.stderr)

    success = notify_backend(event, stream_key, metadata)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
