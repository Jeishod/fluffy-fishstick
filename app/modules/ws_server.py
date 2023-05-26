import websockets.exceptions
from fastapi import WebSocket


class WSServer:
    active_connections: list[WebSocket]

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for websocket_connection in self.active_connections:
            try:
                await websocket_connection.send_text(message)
            except websockets.exceptions.ConnectionClosedError:
                self.disconnect(websocket=websocket_connection)
