import asyncio
import websockets

async def echo(websocket, path):
    print(f"New connection from {websocket.remote_address}")

    try:
        async for message in websocket:
            print(f"Received message: {message}")
            await websocket.send(f"Echo: {message}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed with {websocket.remote_address}")

async def main():
    # Start the server on localhost at port 8080
    server = await websockets.serve(echo, "0.0.0.0", 22)
    print("WebSocket server started on ws://0.0.0.0:22")

    # Run the server until it is stopped
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())