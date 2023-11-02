import asyncio
import websockets


async def receive_message():
    uri = "ws://localhost:8760/ws/1234"  # Use your server URI here
    async with websockets.connect(uri) as websocket:
        while True:
            print("waiting for message")
            try:
                message = await websocket.recv()
            except Exception as e:
                print(f"An error occurred: {e}")


# asyncio.run is available from Python 3.7
if __name__ == "__main__":
    asyncio.run(receive_message())
