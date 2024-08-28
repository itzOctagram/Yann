# server.py
import asyncio
import websockets
import json

# Store connected clients
clients = {
    'sender': None,
    'receiver': None
}


async def handler(websocket, path):
    # Assign the client to either sender or receiver based on path
    if path == "/sender":
        clients['sender'] = websocket
    elif path == "/receiver":
        clients['receiver'] = websocket

    async for message in websocket:
        data = json.loads(message)
        print(f"Received data from {path}: {data}")

        # Send received data to the receiver client
        if clients['receiver']:
            response = json.dumps({"received_from_sender": data})
            await clients['receiver'].send(response)
            print("Sent data to receiver")

        # Send acknowledgment to the sender client
        if clients['sender']:
            ack = json.dumps({"response": "Data received"})
            await clients['sender'].send(ack)
            print("Sent acknowledgment to sender")

start_server = websockets.serve(handler, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
