from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import threading
from fastapi import WebSocketDisconnect, Request

app = FastAPI()

# Diccionario para almacenar clientes conectados con sus respectivos nombres de usuario
clients = {}

# Objeto para manejar plantillas HTML
templates = Jinja2Templates(directory="templates")

# Ruta principal para cargar la página de chat con solicitud de nombre de usuario
@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    usernames = list(clients.keys())
    return templates.TemplateResponse("index.html", {"request": request, "usernames": usernames})

# Ruta WebSocket para establecer la conexión WebSocket con el nombre de usuario
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()

    # Agregar el nuevo cliente al diccionario con su nombre de usuario como clave
    clients[username] = websocket

    # Enviar un mensaje de bienvenida cuando un usuario se une al chat
    for client_name, client_ws in clients.items():
        if client_name != username:
            await client_ws.send_text(f"{username} se ha unido al chat")

    try:
        while True:
            data = await websocket.receive_text()

            # Analizar el mensaje para determinar si es público o privado
            if data.startswith("/public "):
                # Mensaje público
                data = data[len("/public "):]
                for client_name, client_ws in clients.items():
                    await client_ws.send_text(f"{username} (public): {data}")
            elif data.startswith("/private "):
                # Mensaje privado
                data = data[len("/private "):]
                recipient_username, _, message = data.partition(" ")
                if recipient_username in clients:
                    recipient_ws = clients[recipient_username]
                    await recipient_ws.send_text(f"{username} (private): {message}")
                else:
                    # Manejar el caso en el que el destinatario no existe
                    await websocket.send_text(f"Usuario '{recipient_username}' no encontrado.")
            else:
                # Mensaje normal (broadcasting)
                for client_name, client_ws in clients.items():
                    await client_ws.send_text(f"{username}: {data}")

            # Enviar la lista actualizada de usuarios conectados a todos los clientes
            usernames = list(clients.keys())
            for client_name, client_ws in clients.items():
                await client_ws.send_text(f"/userlist {', '.join(usernames)}")
    except WebSocketDisconnect:
        # Remover el cliente cuando se desconecta
        del clients[username]

# Función para iniciar el servidor FastAPI
def start_server():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Iniciar el servidor en un hilo separado
if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
