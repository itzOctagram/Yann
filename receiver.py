import asyncio
import json
import websockets

async def handler(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        print(f"Received data from {path}: {data}")

async def receive_message():
    uri = "ws://localhost:8765/receiver"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                await handler(websocket, uri)
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)  # Wait before reconnecting
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)  # Wait before reconnecting

if __name__ == "__main__":
    asyncio.run(receive_message())