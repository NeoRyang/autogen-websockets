from starlette.websockets import WebSocketDisconnect
from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict
from typing import Dict
import uuid
import autogen
from autogen import AssistantAgent, UserProxyAgent

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": {
            "gpt-4",
            "gpt-4-32k",
        }
    },
)

llm_config = {
    "config_list": config_list,
    "request_timeout": 220,
}


def extract_messages(de):
    signal = "TERMINATE"
    manager = list(de.keys())[0]
    dicts = de[manager]
    messages = [d["content"].strip() for d in dicts]
    cleaned_messages = [msg for msg in messages if msg and msg != signal]
    return cleaned_messages


class TrackableAssistantAgent(AssistantAgent):
    def __init__(self, websocket, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket = websocket

    async def _process_received_message(self, message, sender, silent):
        msg_lines = [f"{sender.name.capitalize()}: {message}"]
        await self.websocket.send("\n".join(msg_lines))

        return super()._process_received_message(message, sender, silent)


class TrackableUserProxyAgent(UserProxyAgent):
    def __init__(self, websocket, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket = websocket

    async def _process_received_message(self, message, sender, silent):
        msg_lines = [f"{sender.name.capitalize()}: {message}"]
        await self.websocket.send("\n".join(msg_lines))
        return super()._process_received_message(message, sender, silent)


# 创建全局的websocket连接池
sockets: Dict[str, WebSocket] = defaultdict()

# NotImplementedError: WebSocketEndpoint.on_receive() must be overridden 去掉websocket 类

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket):
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id)

    async def send_message(self, client_id: str, message: str):
        socket = self.active_connections.get(client_id)
        print("active_connections", client_id)
        print(message)
        if socket:
            print("active_connections", client_id)
            print(message)

            await socket.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()  # Accept WebSocket connection
    try:
        while True:
            data = await websocket.receive_text()
            # 你的逻辑代码...
    except WebSocketDisconnect:
        manager.disconnect(client_id)


@app.post("/items/")
async def create_item(client_id: str):
    print(client_id)
    await manager.send_message(client_id, '{"message": "item created"}')


@app.post("/query/")
async def query(client_id: str, query: str):
    # create an AssistantAgent instance named "assistant"
    assistant = TrackableAssistantAgent(name="assistant", llm_config=llm_config)

    # create a UserProxyAgent instance named "user"
    user_proxy = TrackableUserProxyAgent(
        name="user", human_input_mode="NEVER", llm_config=llm_config
    )

    async def initiate_chat():
        await user_proxy.a_initiate_chat(
            assistant,
            message=query,
        )

    await initiate_chat()
