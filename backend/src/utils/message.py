import asyncio
import base64
import json
import time
import uuid
import warnings

from datetime import datetime
from contextlib import ContextDecorator


class Message:
    """
        Protocol message class to communicate between the server and the client.
    """

    def __init__(self, content, type="message"):
        self.type = type
        self.content = content

    def __repr__(self):
        content = str(self.content)[:min(50, len(str(self.content)))]
        return f"[Message<{self.type}>]: {content}"
    
    def to_json(self):
        return json.dumps({"type": self.type, "data": {"content": self.content}})
    
    @staticmethod
    def from_json(json_str):
        """
            Dynamically create a message from a json string.
            Can return a different protocole type, but always a protocol class.
        """

        data = json.loads(json_str)

        if "type" not in data or "data" not in data:
            # warning in yellow
            warnings.warn(f"\033[93mInvalid message: {data}\033[0m", stacklevel=3)
            return ErrorMessage("Invalid message: A message should be compose of a <type> and <data>")

        if data["type"] not in TYPES_MAP or TYPES_MAP[data["type"]] == Message:
            return Message(content=data["data"], type=data["type"])
        
        return TYPES_MAP[data["type"]].from_json(data)
    
class PartialChunkedMessage(Message):
    
    def __init__(self, type, data):
        super().__init__(content=f'PartialChunkedMessage<{type}>', type=type)

        if self.type == 'start_chunked_upload':
            self.start_dt = datetime.now()
            self.upload_id = data['upload_id']
            self.filename = data['filename']
            self.total_chunks = data['total_chunks']
            self.asked_folder = data['folder']

        elif self.type == "chunk":
            self.upload_id = data['upload_id']
            self.chunk_index = data['chunk_index']
            self.bin64 = data['bin64']

    @staticmethod
    def from_json(data):
        return PartialChunkedMessage(data["type"], data['data'])

class ChunkedMessage:
    """
    Envoie un gros message (dict / str / bytes) en plusieurs frames :
    - On encode le message complet en base64 **une seule fois**
    - Puis on découpe la chaîne encodée par blocs de `chunk_chars`
      (multiples de 4 pour rester aligné base64)
    """
    def __init__(self, content, type="message",
                 chunk_chars=16_384):          # 16 384 est déjà multiple de 4
        self.type          = "chunked"
        self.original_type = type
        self.upload_id     = str(uuid.uuid4())

        # -- contenu → bytes
        if isinstance(content, (dict, list)):
            content_bytes = json.dumps(content).encode("utf-8")
        elif isinstance(content, str):
            content_bytes = content.encode("utf-8")
        elif isinstance(content, bytes):
            content_bytes = content
        else:
            raise TypeError("Unsupported content type")

        # -- une *seule* base64 pour tout le message
        b64_all = base64.b64encode(content_bytes).decode("ascii")

        # -- découpe propre (alignée sur 4 caractères)
        chunk_chars = max(4, chunk_chars - (chunk_chars % 4))
        self.chunks = [
            b64_all[i:i + chunk_chars]
            for i in range(0, len(b64_all), chunk_chars)
        ]
        self.total_chunks = len(self.chunks)

    # ------------------------------------------------------------------  
    def iter_chunks(self):
        yield {
            "type": "start_chunked_download",
            "data": {
                "upload_id":     self.upload_id,
                "original_type": self.original_type,
                "total_chunks":  self.total_chunks
            }
        }
        for idx, b64_slice in enumerate(self.chunks):
            yield {
                "type": "chunk",
                "data": {
                    "upload_id":  self.upload_id,
                    "chunk_index": idx,
                    "bin64":       b64_slice
                }
            }

    """
    Coupe une *chaîne UTF‑8* (ou un dict que l'on json‑dump) en morceaux fixes.
    Aucune conversion base64 ⇒ surcharge mémoire minimale côté client.
    """

    def __init__(self, content, type="message", chunk_chars=16_384):
        self.type          = "chunked"
        self.original_type = type
        self.upload_id     = str(uuid.uuid4())

        # -- contenu → str JSON
        if isinstance(content, (dict, list)):
            content_str = json.dumps(content, separators=(",", ":"))
        elif isinstance(content, str):
            content_str = content
        else:
            raise TypeError("Content must be dict or str in this mode")

        self.chunks = [
            content_str[i:i + chunk_chars]
            for i in range(0, len(content_str), chunk_chars)
        ]
        self.total_chunks = len(self.chunks)

    # -- générateur à utiliser dans le `send`
    def iter_chunks(self):
        yield {
            "type": "start_chunked_download",
            "data": {
                "upload_id":     self.upload_id,
                "original_type": self.original_type,
                "total_chunks":  self.total_chunks
            }
        }
        for idx, slice_ in enumerate(self.chunks):
            yield {
                "type": "chunk",
                "data": {
                    "upload_id":  self.upload_id,
                    "chunk_index": idx,
                    "slice":       slice_   # ← tranche de texte brut
                }
            }

class PopUp(Message):
    def __init__(self, content, callback=None):
        super().__init__(content, type="pop-up")
        self.callback = callback

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "data": {
                "content": self.content,
                "callback": self.callback
            }
        })

    @staticmethod
    def from_json(data):
        pop_up = PopUp(data["data"]["content"], is_open=data["data"]["is_open"])
        pop_up.action = data["data"]["action"]

class Toast(Message):
    def __init__(self, content, toaster_type="success", duration=5000):
        super().__init__(content, type="toast")
        self.duration = duration
        self.toaster_type = toaster_type  # Default type, can be "success", "error", "info", etc.

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "data": {
                "content": self.content,
                "duration": self.duration,
                "type": self.toaster_type,
            }
        })

    @staticmethod
    def from_json(data):
        toast = Toast(data["data"]["content"])
        toast.duration = data["data"]["duration"]
        toast.toaster_type = data["data"]["type"]
        return toast
    
class Notification(Message):
    def __init__(self, content):
        super().__init__(content, type="notification")

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "data": {
                "content": self.content,
            }
        })

    @staticmethod
    def from_json(data):
        notification = Notification(data["data"]["content"])
        return notification
    
class ErrorMessage(Message):
    def __init__(self, content):
        super().__init__(content, type="error")

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "data": {
                "content": self.content
            }
        })

    @staticmethod
    def from_json(data):
        return ErrorMessage(data["data"]["content"])

class NavigationCommand(Message):
    
    def __init__(self, mode="redirect", url=None, params=None, target=None):
        """
        ----
        mode: 'redirect', 'reload', 'back', 'open'

        url: target URL for redirect or open

        params: dict of query params to append (only for 'reload')

        target: optional target for 'open' (e.g., '_blank')

        """
        assert mode in ["redirect", "reload", "back", "open"], f"Invalid mode: {mode}"
        super().__init__(content={
            "mode": mode,
            "url": url,
            "params": params or {},
            "target": target
        }, type="navigation")

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "data": {
                "content": self.content
            }
        })

    @staticmethod
    def from_json(data):
        content = data["data"]["content"]
        return NavigationCommand(
            mode=content["mode"],
            url=content.get("url"),
            params=content.get("params"),
            target=content.get("target")
        )

class LoadingCommand(Message):
    """
    Avoid to directly use LoadingCommand, prefer LoadingScreen: a manager of loading commandsn
    """

    def __init__(self, action, main_steps=None, detail=None):
        """
        action: 'show', 'update', 'hide'
        main_steps: list of dicts with keys: title, progress, optional info
        detail: dict with any additional info
        """
        assert action in {"show", "update", "hide"}
        content = {"action": action}
        if action in {"show", "update"}:
            if main_steps:
                content["main_steps"] = main_steps
            if detail:
                content["detail"] = detail
        super().__init__(type="loading", content=content)

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "data": {"content": self.content}
        })
    
class LoadingScreen(ContextDecorator):
    """
        LoadingScreen manages an interactive loading UI over a WebSocket connection.

        Usage:
        ```
            async with LoadingScreen(ws, client) as screen:
                await screen.init(["Load", "Write", "Save"])
                ...
                await screen.step("Load", 0.5, info="50MiB / 138MiB", eta_s=50)
                ...
                await screen.step("Load", 1)
                await screen.step("Write", 0.0, info="Waiting", eta_s=10)
                ...
                await screen.step("Write", 1)
                await screen.step("Save", 0.0)
                ...
            # Automatically hides loading screen on exit
        ```

        Methods:
            init(step_titles: List[str]) -> self
                Initialize loading steps and display the loading screen.

            step(title: str, progress: Optional[float] = None, info: Optional[str] = None, **extra) -> self
                Update the progress and optional info of a step, along with additional global details.

            finish() -> self
                Hide the loading screen manually (called automatically on context exit).

        Parameters:
            ws : WebSocket-like object
                WebSocket connection used to send loading screen update messages.

        Notes:
            - Progress values should be floats between 0.0 and 1.0.
            - 'info' is a free-text string displayed alongside each step's progress.
            - Additional keyword arguments (**extra) can include global details such as 'eta_s' or 'loaded_mb'.
            - Raises ValueError if updating a step not previously initialized.
    """

    def __init__(self, ws, client):
        self.ws = ws
        self.client = client
        self.steps = []
        self.step_lookup = {}
        self.detail_data = {}
        self._started = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            # une erreur est survenue
            await self.ws.send(
                self.client,
                ErrorMessage(f'An unexpected error occurred: {exc_value}')
            )
            print(traceback) # mmm
        await self.finish()

    async def init(self, step_titles):
        self.steps = [{"title": title, "progress": 0.0, "info": ""} for title in step_titles]
        self.step_lookup = {title: i for i, title in enumerate(step_titles)}
        await self._send("show")
        self._started = True
        return self

    async def step(self, title, progress=None, *, info=None, **extra):
        if title not in self.step_lookup:
            raise ValueError(f"Unknown step '{title}' — call .init([...]) first.")
        idx = self.step_lookup[title]

        if progress is not None:
            self.steps[idx]["progress"] = float(progress)

        for i, step in enumerate(self.steps):
            step["info"] = str(info) if i == idx and info is not None else ""

        self.detail_data.update(extra)
        await self._send("update")
        return self

    async def finish(self):
        await self._send("hide")
        return self

    async def _send(self, action):
        cmd = LoadingCommand(
            action=action,
            main_steps=self.steps,
            detail=self.detail_data if self.detail_data else None
        )
        # Envoie JSON via websocket
        await self.ws.send(self.client, cmd)
        await asyncio.sleep(0) # force event loop to flush socket
         
TYPES_MAP = {
    # Fondamental types
    "error": ErrorMessage,
    "message": Message,
    "start_chunked_upload": PartialChunkedMessage,
    "chunk": PartialChunkedMessage,
    "navigation": NavigationCommand,
    "loading": LoadingCommand,

    # Basic types
    "pop-up": PopUp,
    "toast": Toast,
    "notification": Notification,
}
