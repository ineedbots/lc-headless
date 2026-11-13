"""Print live account logout events. Requires the websockets package."""

import argparse
import asyncio
import json
import sys


async def listen(args):
    try:
        from websockets.asyncio.client import connect
        from websockets.exceptions import ConnectionClosed
    except ImportError:
        raise SystemExit("Install the dependency: python -m pip install websockets")

    events = ["account.logout"]
    if args.progress:
        events.append("account.progress")
    subscription = {
        "version": 1,
        "type": "subscribe",
        "id": "logout-test",
        "events": events,
        "accounts": args.account,
    }

    print(f"Connecting to {args.url}; Ctrl+C to stop.", file=sys.stderr, flush=True)
    async for socket in connect(args.url):
        try:
            await socket.send(json.dumps(subscription))
            async for message in socket:
                value = json.loads(message)
                print(json.dumps(value, indent=2), flush=True)
                if value.get("type") == "error":
                    raise SystemExit("Subscription rejected; see the server error above.")
                if value.get("type") == "ack" and value.get("action") == "subscribe":
                    print("Subscribed; waiting for new logout events (no replay).", file=sys.stderr, flush=True)
        except ConnectionClosed as error:
            print(f"Disconnected: {error}; reconnecting", file=sys.stderr, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://127.0.0.1:8080/api/v1/events")
    parser.add_argument("--account", action="append", default=[], help="Account config name; repeat to select several. Default: all accounts.")
    parser.add_argument("--progress", action="store_true", help="Also print account.progress events.")
    args = parser.parse_args()
    try:
        asyncio.run(listen(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
