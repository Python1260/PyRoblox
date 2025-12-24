import asyncio
import json
import uuid

import websockets
import threading

class WebSocket():
    def __init__(self, app, host="localhost", port=8080):
        self.app = app

        self.running = False

        self.host = host
        self.port = port

        self.thread = None
        self.loop = None

        self.server = None
        self.clients = set()

        self.requests = {}
        self.signal_handlers = {}

    def on(self, name, func):
        self.signal_handlers.setdefault(name, []).append(func)
    
    async def handler(self, websocket):
        self.clients.add(websocket)

        try:
            async for message in websocket:
                data = json.loads(message)
                req_type = data["type"]
                req_id = data["id"]
                req_action = data["action"]
                req_data = data["data"]

                if req_type == "client":
                    if req_id in self.requests:
                        for fut in self.requests[req_id]:
                            if not fut.done():
                                fut_loop = fut.get_loop()
                                fut_loop.call_soon_threadsafe(
                                    fut.set_result,
                                     (websocket, req_data)
                                )
                    if req_action in self.signal_handlers:
                        handlers = self.signal_handlers[req_action]

                        for handler in handlers:
                            if asyncio.iscoroutinefunction(handler):
                                self.loop.create_task(handler(websocket, req_id, req_data))
                            else:
                                self.loop.call_soon_threadsafe(handler, websocket, req_id, req_data)
                            
        except asyncio.CancelledError:
            pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
    
    async def send(self, action, data=None, request_id=None, target=None):
        if data is None: data = {}
        if request_id is None: request_id = str(uuid.uuid4())

        clients = set(self.clients) if target is None else { target }

        message = json.dumps({
            "type": "server",
            "id": request_id,
            "action": action,
            "data": data
        })

        for client in clients:
            await client.send(message)
    
    async def send_and_receive(self, action, data=None, request_id=None, timeout=5, target=None):
        if data is None: data = {}
        if request_id is None: request_id = str(uuid.uuid4())

        futures = []

        clients = set(self.clients) if target is None else { target }

        for _ in clients:
            fut = asyncio.get_running_loop().create_future()
            futures.append(fut)
            self.requests.setdefault(request_id, []).append(fut)
        
        message = json.dumps({
            "type": "server",
            "id": request_id,
            "action": action,
            "data": data
        })

        for client in clients:
            await client.send(message)
        
        responses = []

        try:
            done = await asyncio.wait_for(
                asyncio.gather(*futures),
                timeout=timeout
            )
            responses.extend(done)
        except asyncio.TimeoutError:
            pass
            
        self.requests.pop(request_id, None)
        return responses
    
    async def start_async(self):
        if self.server:
            return

        self.server = await websockets.serve(
            self.handler,
            self.host,
            self.port
        )
    
    def start(self):
        if self.thread and self.thread.is_alive():
            return
        
        self.running = True
        
        def worker():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.loop.run_until_complete(self.start_async())
            self.loop.run_forever()

            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            
            self.loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )

            self.loop.close()
            self.loop = None
        
        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()
    
    async def stop_async(self):
        for client in list(self.clients):
            client.close()
        self.clients = set()
        
        if self.server:
            self.server.close()
        self.server = None

        self.requests = {}
        
        self.loop.stop()
    
    def stop(self):
        if not self.loop or not self.loop.is_running():
            return
        
        self.running = False

        asyncio.run_coroutine_threadsafe(self.stop_async(), self.loop)
        
        self.thread = None