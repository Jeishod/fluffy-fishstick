from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.modules.ws_server import WSServer
from app.utils.dependencies import get_ws_server


dashboard_router = APIRouter(prefix="/dashboard")


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/api/v1/dashboard/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@dashboard_router.get("/")
async def get():
    return HTMLResponse(html)


@dashboard_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, ws_server: WSServer = Depends(get_ws_server)):
    await ws_server.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_server.send_personal_message(f"You wrote: {data}", websocket)
            await ws_server.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        ws_server.disconnect(websocket)
        await ws_server.broadcast(f"Client #{client_id} left the chat")
