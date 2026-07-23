import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://127.0.0.1:8000/api/v1/swarm-stream") as websocket:
            print("Connected successfully!")
            await websocket.send('{"directive": "test", "paper_trading": true}')
            response = await websocket.recv()
            print("Response:", response)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
