import asyncio
import base64
import json
import os
import traceback
import websockets

from .message import *
from .console import Style

class ServerSocket:
    """
    A class to manage a WebSocket server.

    Attributes
    ----------
    host : str
        The host of the server.

    port : int
        The port of the server.

    running : bool
        Whether the server is running or not.

    _print : bool
        Whether to print information or not.

    server : websockets.server.WebSocketServer
        The server object.

    clients : set[websockets.server.WebSocketServerProtocol]
        The set of connected clients.

    loop : asyncio.AbstractEventLoop
        The asyncio event loop.

    messages : dict[str, list]
        The messages received from the clients.

    How to use:
    ----------

    --- synchrone --------------------
    >>> server = ServerSocket() # Create a server

    --- asynchrone --------------------
    >>> async with server: # Start the server
    >>>     await server.wait_for_clients(1) # Wait for a client to connect
    >>>     await server.broadcast("Hello, clients!") # Broadcast a message to all clients
    >>>     await server.wait() # Keep the server running
    """

    class EVENTS_TYPES:
        on_client_connect = "on_client_connect"
        """
        Event triggered when a client connects to the server
        Listener arguments: client
        """

        on_client_disconnect = "on_client_disconnect"
        """
        Event triggered when a client disconnects from the server
        Listener arguments: client
        """

        on_message = "on_message"
        """
        Event triggered when a message is received from a client
        Listener arguments: client, message
        """

        on_server_stop = "on_server_stop"
        """
        Event triggered when the server is stopped
        Listener arguments: None
        """

        @staticmethod
        def all():
            return [
                event for event in ServerSocket.EVENTS_TYPES.__dict__.values()
                if type(event) is str and not event.startswith("__")
            ]

    HISTORY_LIMIT = 3
    def __init__(self, host="127.0.0.1", port=5384, _print=False, upload_dir=os.path.join('backend', 'uploads')):
        self.host = host
        self.port = port
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        self.running = False
        self._print = _print

        self._stop_future = None
        self._uploading_chunks = {}

        self.server = None
        self.clients = set()  # To keep track of connected clients

        self.loop = asyncio.get_event_loop()

        self.messages: dict[str, list] = {}

        self._events_listeners = {event: {} for event in self.EVENTS_TYPES.all()}

    def _update_history(self, client, message):
        if client.remote_address not in self.messages:
            self.messages[client.remote_address] = []
        self.messages[client.remote_address].append(message)
        if len(self.messages[client.remote_address]) > self.HISTORY_LIMIT:
            self.messages[client.remote_address].pop(0)

        if self._print and message.type != 'chunk':
            print("[info]\t\t", Style("INFO", f"Client {client.remote_address}: {message}"))

    async def _execute_event(self, event_type, *args):
        listeners_output = []
        for listener in self._events_listeners[event_type].values():
            try:
                listeners_output.append(listener(*args))
            except TypeError as e:
                # if the listener does not have the right number of arguments
                warnings.warn(Style("WARNING", f"Error occurred in {event_type} event.\nListener does not have the right number of arguments: {e}\nThe listener will not be executed."), stacklevel=2)
                traceback.print_exc()

            except Exception as e:
                warnings.warn(Style("WARNING", f"Error occurred in {event_type} event: {e}"), stacklevel=2)
                traceback.print_exc()

        # s'il y a des éléments dans listeners_output que l'on doit await, alors les await
        listeners_output = [output for output in listeners_output if asyncio.iscoroutine(output)]
        # if listeners_output:
        #     await asyncio.wait(listeners_output, timeout=3)

        if listeners_output:
            # Turn each coroutine into a Task
            tasks = [asyncio.create_task(coro) for coro in listeners_output]
            
            # Now pass tasks (not raw coroutines) to asyncio.wait
            done, pending = await asyncio.wait(tasks, timeout=3)

    async def _handler(self, websocket, path=None):
        """Register client and manage communication."""
        # Register the client
        self.clients.add(websocket)
        self._update_history(websocket, Message("network", "Client connected"))

        if self._print:
            print("[network]\t", Style("SECONDARY_SUCCESS", f"Client connected: {websocket.remote_address}"))

        # execute the on_client_connect event
        await self._execute_event(self.EVENTS_TYPES.on_client_connect, websocket)

        # keep the connection alive
        while True:
            try:
                # Wait for a message from the client
                message = await websocket.recv()
                message = Message.from_json(message)

                if message.type == 'start_chunked_upload':
                    if websocket not in self._uploading_chunks:
                        self._uploading_chunks[websocket] = {'id': None, 'start': None, 'end': None, 'path': None, 'file': None}
                    else:
                        print("[server]\t", Style('ERROR', "A client try to send a chunked message when the previous one isn't finish"))
                        raise EOFError("The previous chunked message never ended (no EOF message)")
                    
                    self._uploading_chunks[websocket]['start'] = message

                    self._uploading_chunks[websocket]['path'] = os.path.join(self.upload_dir, *message.asked_folder, f"{message.upload_id}_{message.filename}")
                    self._uploading_chunks[websocket]['file'] = open(self._uploading_chunks[websocket]['path'], "wb")

                
                elif message.type == 'chunk':
                    data = base64.b64decode(message.bin64)
                    file = self._uploading_chunks[websocket]['file']
                    if file:
                        file.write(data)
                    else:
                        print("[server]\t", Style('ERROR', 'A client sent a <chunk message> before a <start of chunked message>'))
                        raise RuntimeError('A client sent a <chunk message> before a <start of chunked message>')
                    
                elif message.type == "end_chunked_upload":
                    file = self._uploading_chunks[websocket]['file']
                    if file:
                        file.close()
                    else:
                        print("[server]\t", Style('ERROR', 'A client sent a <end of chunked message> before a <start of chunked message>'))
                        raise RuntimeError('A client sent a <end of chunked message> before a <start of chunked message>')
                    
                    del self._uploading_chunks[websocket]['file']
                    message.content = self._uploading_chunks.pop(websocket)
                    

                # execute the on_message event
                await self._execute_event(self.EVENTS_TYPES.on_message, websocket, message)

                self._update_history(websocket, message)

            # If the client disconnects, remove it from the list of clients
            except websockets.ConnectionClosed:
                message = Message("network", "Client disconnected")

                # execute the on_client_disconnect event
                await self._execute_event(self.EVENTS_TYPES.on_client_disconnect, websocket)

                self._update_history(websocket, message)
                self.clients.remove(websocket)
                if websocket in self._uploading_chunks: del self._uploading_chunks[websocket]

                if self._print:
                    print("[network]\t", Style("SECONDARY_WARNING", f"Client disconnected: {websocket.remote_address}"))
                break

            # if error occurs, remove the client
            except Exception as e:
                message = ErrorMessage(str(e))
                warnings.warn(Style("ERROR", f"Error occurred: {e}"), stacklevel=2)
                traceback.print_exc()
                self._update_history(websocket, message)
                self.clients.remove(websocket)
                break

    async def _start(self):
        """Start the server. Don't forget to `socket.wait()` in order to keep the server alive!"""
        if self.running:
            raise Exception("Server is already running")
        
        self._stop_future = asyncio.get_event_loop().create_future()
        self.running = True
        self.server = await websockets.serve(self._handler, self.host, self.port, ping_timeout=60)
        if self._print:
            print("[server]\t", Style("SUCCESS", f"Server started at ws://{self.host}:{self.port}"))

    async def wait(self):
        """Keep the server alive"""
        await self._stop_future

    async def stop(self):
        """Stop the server."""
        if not self.running: return
        # execute the on_server_stop event
        await self._execute_event(self.EVENTS_TYPES.on_server_stop)

        # close all clients
        closing_tasks = [asyncio.create_task(client.close()) for client in self.clients]
        if closing_tasks:
            await asyncio.wait(closing_tasks, timeout=3)
        
        # check if some clients are still connected
        if len(self.clients) > 0:
            warnings.warn(f"Failed to close {len(self.clients)} clients; closing forcefully")

        self.server.close()
        self._stop_future.set_result(True)
        self.running = False

        if self._print:
            print("[server]\t", Style("SECONDARY_ERROR", "Server stopped"))

    async def broadcast(self, message):
        """Broadcast a message to all connected clients."""
        if isinstance(message, Message) or issubclass(type(message), Message):
            message = message.to_json()
            
        if type(message) is not str:
            print(Style("ERROR", message))
            raise ValueError(f"Message must be a string or a Message object not a {type(message)}")
        if not self.running:
            raise Exception("Server is not running")
        for client in self.clients:
            await client.send(message)

    async def send(self, client, message):
        """Send a message to a specific client."""
        if not self.running:
            raise Exception("Server is not running")
        
        if isinstance(message, ChunkedMessage):
            for chunk in message.iter_chunks():
                await client.send(json.dumps(chunk))
            return
        
        elif isinstance(message, Message) or issubclass(type(message), Message):
            message = message.to_json()
        
        await client.send(message)

    async def wait_for_clients(self, num_clients):
        """Wait until the specified number of clients are connected."""
        if self._print:
            print("[server]\t", Style("SECONDARY_INFO", f"Waiting for {num_clients} clients to be connected"))
        while len(self.clients) < num_clients:
            await asyncio.sleep(1)

    def on(self, event_type, listener_id, listener):
        """Add an event listener."""
        if event_type not in self._events_listeners:
            raise ValueError(f"Invalid event type: {event_type}")
        if listener_id in self._events_listeners[event_type]:
            raise ValueError(f"Listener with id {listener_id} already exists")
        
        self._events_listeners[event_type][listener_id] = listener
        return listener_id
    
    def off(self, event_type, listener_id):
        """Remove an event listener."""
        if event_type not in self._events_listeners:
            raise ValueError(f"Invalid event type: {event_type}")
        if listener_id not in self._events_listeners[event_type]:
            raise ValueError(f"Listener with id {listener_id} does not exist")
        
        del self._events_listeners[event_type][listener_id]
        return listener_id
    
    async def __aenter__(self):
        await self._start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is asyncio.CancelledError:
            if self._print: print("[server]\t", Style("WARNING", "Run cancelled"))
        if exc_type is KeyboardInterrupt:
            if self._print: print("[server]\t", Style("WARNING", "KeyboardInterrupt"))
        if exc_type:
            print("[server]\t", Style("ERROR", f"Unhandled exception: {exc_type.__name__}"))

        await self.stop()
        if exc_type: raise exc

    
    def safe_run(self, coro):
        """
        This method is a decorator, use it to wrap the function that managing the socket in order to ensure a 'safe run'
        """
        async def wrapper(*args, **kwargs):
            try:
                await coro(*args, **kwargs)
            except asyncio.CancelledError:
                if self._print:
                    print("[server]\t", Style("WARNING", "Run cancelled"))
                raise
            except KeyboardInterrupt:
                if self._print:
                    print("[server]\t", Style("WARNING", "KeyboardInterrupt"))
            except Exception as e:
                print("[server]\t", Style("ERROR", f"Unhandled exception: {e}"))
            finally:
                await self.stop()
        return wrapper
