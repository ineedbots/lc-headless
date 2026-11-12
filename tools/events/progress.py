"""Native operator example. Install websockets, then run with a ws:// URL."""

import asyncio
import json
import sys

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8080/api/v1/events"
    async for socket in connect(url):
        try:
            # Reconnect always starts a fresh subscription and snapshot.
            await socket.send(json.dumps({
                "version": 1, "type": "subscribe", "id": "progress",
                "events": ["account.progress"],
            }))
            async for message in socket:
                print(json.dumps(json.loads(message), indent=2))
        except asyncio.CancelledError:
            try:
                await socket.send(json.dumps({
                    "version": 1, "type": "unsubscribe", "id": "progress",
                }))
                await socket.close()
            except ConnectionClosed:
                pass
            raise
        except ConnectionClosed as error:
            print(f"Disconnected: {error}; reconnecting", file=sys.stderr)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
