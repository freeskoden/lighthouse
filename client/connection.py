import asyncio
import threading
import json
import logging
import websockets

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class LighthouseConnection:
    def __init__(self, settings):
        self.settings = settings
        self.websocket = None
        self.loop = None
        self.thread = None
        self.running = False
        self.role = "idle"
        self.capture_task = None
        self.capture_quality = "Medium"
        
        # Thread-safe callback wrappers (to be configured by the GUI)
        self.on_status_changed = lambda status: None
        self.on_registered = lambda username, password: None
        self.on_permission_requested = lambda from_username: None
        self.on_connection_result = lambda status, message: None
        self.on_session_started = lambda role: None
        self.on_session_ended = lambda reason: None
        self.on_screen_received = lambda jpeg_bytes: None
        self.on_input_received = lambda event_dict: None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main_task())
        except Exception as e:
            logging.error(f"Error in connection thread loop: {e}")
        finally:
            self._cancel_capture_task()
            self.loop.close()

    def _cancel_capture_task(self):
        if self.capture_task and not self.capture_task.done():
            self.capture_task.cancel()
        self.capture_task = None

    async def _host_capture_loop(self):
        logging.info("Starting host capture loop...")
        try:
            from capture import ScreenCapture
            
            QUALITY_PRESETS = {
                "Minimum": {"scale": 0.5, "quality": 30},
                "Medium": {"scale": 0.7, "quality": 50},
                "Maximum": {"scale": 1.0, "quality": 80}
            }
            
            while self.websocket and self.role == "host":
                start_time = asyncio.get_event_loop().time()
                
                # Fetch target quality presets dynamically
                preset = QUALITY_PRESETS.get(self.capture_quality, QUALITY_PRESETS["Medium"])
                
                # Capture screen in background thread using the selected preset
                jpeg_bytes = await asyncio.to_thread(
                    ScreenCapture.capture, 
                    preset["quality"], 
                    preset["scale"]
                )
                
                if jpeg_bytes and self.websocket:
                    try:
                        # Awaiting the send directly implements natural backpressure!
                        await self.websocket.send(jpeg_bytes)
                    except Exception as e:
                        logging.error(f"Error sending screen frame: {e}")
                        break
                
                # Target max ~10 FPS (100ms interval) to keep it lightweight
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0.01, 0.1 - elapsed)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logging.info("Host capture loop cancelled.")
        except Exception as e:
            logging.error(f"Error in host capture loop: {e}")
        finally:
            logging.info("Stopped host capture loop.")

    async def _main_task(self):
        while self.running:
            # Re-read settings in case they changed
            if self.settings.get("use_cloudflare") and self.settings.get("cloudflare_url"):
                url = self.settings.get("cloudflare_url")
                if not url.startswith("ws://") and not url.startswith("wss://"):
                    url = "wss://" + url
            else:
                host = self.settings.get("server_hostname", "localhost")
                port = self.settings.get("server_port", 8765)
                url = f"ws://{host}:{port}"
                if not url.startswith("ws://") and not url.startswith("wss://"):
                    url = "ws://" + url

            self.on_status_changed(f"Connecting to {url}...")
            try:
                async with websockets.connect(url, ping_interval=10, ping_timeout=10) as ws:
                    self.websocket = ws
                    self.on_status_changed("Connected to server")
                    
                    # Request generation of Local Username and Local Password
                    await self._send_json({"type": "register"})
                    
                    async for message in ws:
                        if isinstance(message, bytes):
                            # Binary frame is screen graphics (JPEG) sent to the viewer
                            self.on_screen_received(message)
                        else:
                            # Text frame is command/control JSON
                            try:
                                data = json.loads(message)
                            except json.JSONDecodeError:
                                logging.warning(f"Malformed JSON text frame: {message}")
                                continue
                            
                            await self._handle_message(data)
                            
            except Exception as e:
                logging.error(f"Connection error: {e}")
                self.on_status_changed("Disconnected. Retrying...")
                self.websocket = None
                self.role = "idle"
                self._cancel_capture_task()
                
            # Wait 3 seconds before trying to reconnect
            await asyncio.sleep(3)

    async def _handle_message(self, data):
        msg_type = data.get("type")
        if msg_type == "register_response":
            self.on_registered(data.get("username"), data.get("password"))
        elif msg_type == "permission_request":
            self.on_permission_requested(data.get("from_username"))
        elif msg_type == "connect_response":
            self.on_connection_result(data.get("status"), data.get("message", ""))
        elif msg_type == "session_started":
            role = data.get("role")
            self.role = role
            if role == "host":
                self.capture_quality = data.get("quality", "Medium")
                self._cancel_capture_task()
                self.capture_task = asyncio.create_task(self._host_capture_loop())
            self.on_session_started(role)
        elif msg_type == "change_quality":
            self.capture_quality = data.get("quality", "Medium")
            logging.info(f"Changed capture quality dynamically to: {self.capture_quality}")
        elif msg_type == "session_ended":
            self.role = "idle"
            self._cancel_capture_task()
            self.on_session_ended(data.get("reason", ""))
        elif msg_type == "input":
            self.on_input_received(data)

    async def _send_json(self, data):
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(data))
            except Exception as e:
                logging.error(f"Socket send failed (JSON): {e}")

    async def _send_binary(self, data):
        if self.websocket:
            try:
                await self.websocket.send(data)
            except Exception as e:
                logging.error(f"Socket send failed (Binary): {e}")

    # --- Thread-Safe Public API called from main Tkinter thread ---

    def request_connection(self, target_username, target_password, quality="Medium"):
        if not self.loop or not self.websocket:
            return False
        asyncio.run_coroutine_threadsafe(
            self._send_json({
                "type": "connect_request",
                "target_username": target_username,
                "target_password": target_password,
                "quality": quality
            }),
            self.loop
        )
        return True

    def respond_permission(self, approved):
        if not self.loop or not self.websocket:
            return False
        asyncio.run_coroutine_threadsafe(
            self._send_json({
                "type": "permission_response",
                "approved": approved
            }),
            self.loop
        )
        return True

    def send_input(self, event_dict):
        if not self.loop or not self.websocket:
            return False
        asyncio.run_coroutine_threadsafe(
            self._send_json(event_dict),
            self.loop
        )
        return True

    def send_screen(self, jpeg_bytes):
        if not self.loop or not self.websocket:
            return False
        asyncio.run_coroutine_threadsafe(
            self._send_binary(jpeg_bytes),
            self.loop
        )
        return True

    def send_disconnect(self):
        if not self.loop or not self.websocket:
            return False
        asyncio.run_coroutine_threadsafe(
            self._send_json({"type": "disconnect"}),
            self.loop
        )
        return True
