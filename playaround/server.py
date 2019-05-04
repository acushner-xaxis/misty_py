import asyncio
import websockets


async def echo(websocket, path):
    print(type(websocket), websocket, type(path), path)
    async for m in websocket:
        await websocket.send(m)

loop = asyncio.get_event_loop()
loop.run_until_complete(websockets.serve(echo, 'localhost', 8898))
loop.run_forever()


