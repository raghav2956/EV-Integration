import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:22/"
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello, WebSocket!")
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.get_event_loop().run_until_complete(test_websocket())