import io
import time
import logging
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import local modules
from settings import load_settings, save_settings
from connection import LighthouseConnection
from capture import ScreenCapture, InputSimulator

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Tkinter to Pynput Key Mapping
KEY_MAP = {
    "Return": "enter",
    "space": "space",
    "BackSpace": "backspace",
    "Tab": "tab",
    "Shift_L": "shift",
    "Shift_R": "shift",
    "Control_L": "ctrl",
    "Control_R": "ctrl",
    "Alt_L": "alt",
    "Alt_R": "alt",
    "Escape": "esc",
    "Up": "up",
    "Down": "down",
    "Left": "left",
    "Right": "right",
    "Caps_Lock": "caps_lock",
    "F1": "f1",
    "F2": "f2",
    "F3": "f3",
    "F4": "f4",
    "F5": "f5",
    "F6": "f6",
    "F7": "f7",
    "F8": "f8",
    "F9": "f9",
    "F10": "f10",
    "F11": "f11",
    "F12": "f12",
}

class LighthouseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Set app window title
        self.title("Lighthouse")
        self.geometry("750x450")
        self.resizable(False, False)

        # Set window icon dynamically if exists
        try:
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(curr_dir, "packaging", "windows", "icon.ico")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(os.path.dirname(curr_dir), "packaging", "windows", "icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Load configs
        self.settings = load_settings()
        
        # Setup Connection & Simulator
        self.conn = LighthouseConnection(self.settings)
        self.simulator = InputSimulator()
        
        # UI State variables
        self.local_username = tk.StringVar(value="Disconnected")
        self.local_password = tk.StringVar(value="----")
        self.conn_status = tk.StringVar(value="Initializing...")
        
        self.is_host_capturing = False
        self.viewer_window = None
        self.viewer_canvas = None
        self.last_mouse_send_time = 0
        
        # Build main layout
        self.setup_ui()
        
        # Link callbacks
        self.setup_conn_callbacks()
        
        # Start connection
        self.conn.start()

    def setup_ui(self):
        # Background Frame (Glassmorphic look)
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title Label
        title_label = ctk.CTkLabel(
            self.main_frame, 
            text="FREESKODEN LIGHTHOUSE", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=15)

        # Split Container (Left/Right)
        split_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=15, pady=10)
        split_frame.grid_columnconfigure(0, weight=1)
        split_frame.grid_columnconfigure(1, weight=1)
        
        # ----------------- Left Panel: Remote Control -----------------
        left_panel = ctk.CTkFrame(split_frame, corner_radius=10, fg_color=("gray90", "gray15"))
        left_panel.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")
        
        left_title = ctk.CTkLabel(
            left_panel, 
            text="Remote Control", 
            font=ctk.CTkFont(size=15, weight="bold")
        )
        left_title.pack(pady=10)
        
        # Remote Username Field
        self.remote_user_entry = ctk.CTkEntry(
            left_panel, 
            placeholder_text="Remote Username (e.g. 123 456)", 
            width=220
        )
        self.remote_user_entry.pack(pady=8)
        
        # Remote Password Field
        self.remote_pass_entry = ctk.CTkEntry(
            left_panel, 
            placeholder_text="Remote Password", 
            show="*", 
            width=220
        )
        self.remote_pass_entry.pack(pady=8)
        
        # Graphics Quality Dropdown
        lbl_quality = ctk.CTkLabel(left_panel, text="Graphics Resolution:", font=ctk.CTkFont(size=12))
        lbl_quality.pack(pady=(5, 2))

        self.quality_menu = ctk.CTkOptionMenu(
            left_panel,
            values=["Minimum", "Medium", "Maximum"],
            command=self.change_graphics_quality,
            width=220
        )
        self.quality_menu.set("Medium")
        self.quality_menu.pack(pady=5)
        
        # Connect Button
        self.btn_connect = ctk.CTkButton(
            left_panel, 
            text="Connect to Client", 
            command=self.start_remote_control, 
            font=ctk.CTkFont(weight="bold")
        )
        self.btn_connect.pack(pady=15)

        # ----------------- Right Panel: Remote Login -----------------
        right_panel = ctk.CTkFrame(split_frame, corner_radius=10, fg_color=("gray90", "gray15"))
        right_panel.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        
        right_title = ctk.CTkLabel(
            right_panel, 
            text="Remote Login", 
            font=ctk.CTkFont(size=15, weight="bold")
        )
        right_title.pack(pady=10)
        
        # Generated Local Username
        lbl_local_user = ctk.CTkLabel(right_panel, text="Local Username:", font=ctk.CTkFont(size=12))
        lbl_local_user.pack(pady=2)
        
        self.entry_local_user = ctk.CTkEntry(
            right_panel, 
            textvariable=self.local_username, 
            state="readonly", 
            width=200, 
            justify="center",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.entry_local_user.pack(pady=5)
        
        # Generated Local Password
        lbl_local_pass = ctk.CTkLabel(right_panel, text="Local Password:", font=ctk.CTkFont(size=12))
        lbl_local_pass.pack(pady=2)
        
        self.entry_local_pass = ctk.CTkEntry(
            right_panel, 
            textvariable=self.local_password, 
            state="readonly", 
            width=200, 
            justify="center",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.entry_local_pass.pack(pady=5)

        # Status and Settings Bottom Bar
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", side="bottom", padx=15, pady=10)
        
        self.lbl_status = ctk.CTkLabel(
            bottom_frame, 
            textvariable=self.conn_status, 
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray"
        )
        self.lbl_status.pack(side="left")

        btn_settings = ctk.CTkButton(
            bottom_frame, 
            text="Settings", 
            width=80, 
            height=26, 
            command=self.open_settings
        )
        btn_settings.pack(side="right")

    def setup_conn_callbacks(self):
        # Wrap callbacks to make sure they run safely on the Tkinter thread
        self.conn.on_status_changed = lambda status: self.after(0, self.update_conn_status, status)
        self.conn.on_registered = lambda user, passw: self.after(0, self.update_local_credentials, user, passw)
        self.conn.on_permission_requested = lambda from_user: self.after(0, self.prompt_permission, from_user)
        self.conn.on_connection_result = lambda status, msg: self.after(0, self.handle_conn_result, status, msg)
        self.conn.on_session_started = lambda role: self.after(0, self.handle_session_started, role)
        self.conn.on_session_ended = lambda reason: self.after(0, self.handle_session_ended, reason)
        self.conn.on_screen_received = lambda jpeg: self.after(0, self.handle_screen_frame, jpeg)
        self.conn.on_input_received = lambda event: self.after(0, self.handle_remote_input, event)

    # --- UI Status Updaters ---

    def update_conn_status(self, status):
        self.conn_status.set(f"Status: {status}")

    def update_local_credentials(self, username, password):
        formatted_username = username
        if len(username) == 6 and username.isdigit():
            formatted_username = f"{username[:3]} {username[3:]}"
        self.local_username.set(formatted_username)
        self.local_password.set(password)

    # --- Settings Dialog ---

    def open_settings(self):
        # Create setting Toplevel dialog
        self.settings_win = ctk.CTkToplevel(self)
        self.settings_win.title("Lighthouse Settings")
        self.settings_win.geometry("400x500")
        self.settings_win.resizable(False, False)
        
        # Grab focus
        self.settings_win.transient(self)
        self.settings_win.grab_set()

        frame = ctk.CTkFrame(self.settings_win, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        title = ctk.CTkLabel(frame, text="Network Configurations", font=ctk.CTkFont(size=14, weight="bold"))
        title.pack(pady=10)

        # Hostname field
        lbl_host = ctk.CTkLabel(frame, text="Server Hostname / IP:")
        lbl_host.pack(anchor="w", padx=20)
        self.entry_host = ctk.CTkEntry(frame, width=320)
        self.entry_host.insert(0, self.settings.get("server_hostname", "localhost"))
        self.entry_host.pack(pady=5)

        # Port field
        lbl_port = ctk.CTkLabel(frame, text="Server Port:")
        lbl_port.pack(anchor="w", padx=20)
        self.entry_port = ctk.CTkEntry(frame, width=320)
        self.entry_port.insert(0, str(self.settings.get("server_port", 8765)))
        self.entry_port.pack(pady=5)

        # Cloudflare option
        self.cf_var = tk.BooleanVar(value=self.settings.get("use_cloudflare", False))
        self.switch_cf = ctk.CTkSwitch(
            frame, 
            text="Use Cloudflare Tunnel", 
            variable=self.cf_var,
            command=self.toggle_cf_entry
        )
        self.switch_cf.pack(pady=10)

        self.entry_cf_url = ctk.CTkEntry(frame, placeholder_text="wss://your-tunnel.trycloudflare.com", width=320)
        self.entry_cf_url.insert(0, self.settings.get("cloudflare_url", ""))
        self.entry_cf_url.pack(pady=5)
        
        # Initialize visibility/state
        self.toggle_cf_entry()

        # Action Buttons (Save & Cancel)
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        btn_save = ctk.CTkButton(
            btn_frame, 
            text="Save & Restart", 
            width=140, 
            command=self.save_settings_action
        )
        btn_save.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            width=100, 
            fg_color="gray", 
            hover_color="darkgray", 
            command=self.settings_win.destroy
        )
        btn_cancel.pack(side="right", padx=10)

        # About & Support (Developer & PayPal Donation info)
        separator = ctk.CTkFrame(frame, height=2, fg_color="gray25")
        separator.pack(fill="x", pady=10)

        lbl_about = ctk.CTkLabel(frame, text="About & Support", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_about.pack(pady=2)

        lbl_programmer = ctk.CTkLabel(frame, text="Programmer: Anthony Markus", font=ctk.CTkFont(size=11))
        lbl_programmer.pack(pady=2)

        btn_donate = ctk.CTkButton(
            frame, 
            text="Donate via PayPal", 
            fg_color="#FFC439", 
            hover_color="#E5AF30", 
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_paypal
        )
        btn_donate.pack(pady=5)

    def open_paypal(self):
        try:
            import webbrowser
            webbrowser.open("https://paypal.me/anthonyrasat")
        except Exception as e:
            logging.error(f"Failed to open donation link: {e}")

    def toggle_cf_entry(self):
        if self.cf_var.get():
            self.entry_cf_url.configure(state="normal")
            self.entry_host.configure(state="disabled")
            self.entry_port.configure(state="disabled")
        else:
            self.entry_cf_url.configure(state="disabled")
            self.entry_host.configure(state="normal")
            self.entry_port.configure(state="normal")

    def save_settings_action(self):
        # Collect values
        try:
            port = int(self.entry_port.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer.")
            return

        self.settings["server_hostname"] = self.entry_host.get().strip()
        self.settings["server_port"] = port
        self.settings["use_cloudflare"] = self.cf_var.get()
        self.settings["cloudflare_url"] = self.entry_cf_url.get().strip()

        # Save
        if save_settings(self.settings):
            self.settings_win.destroy()
            
            # Restart connection thread to apply settings
            self.conn.stop()
            self.conn = LighthouseConnection(self.settings)
            self.setup_conn_callbacks()
            self.conn.start()
            
            messagebox.showinfo("Settings", "Settings saved successfully! Reconnecting...")
        else:
            messagebox.showerror("Error", "Failed to save settings.")

    # --- Session Flows ---

    def start_remote_control(self):
        target_username = self.remote_user_entry.get().replace(" ", "").strip()
        target_password = self.remote_pass_entry.get().strip()

        if not target_username or not target_password:
            messagebox.showwarning("Warning", "Please enter both remote username and password.")
            return

        self.btn_connect.configure(state="disabled", text="Requesting...")
        
        # Send connect request with selected quality setting
        quality = self.quality_menu.get()
        success = self.conn.request_connection(target_username, target_password, quality)
        if not success:
            self.btn_connect.configure(state="normal", text="Connect to Client")
            messagebox.showerror("Error", "Not connected to the Lighthouse server yet.")

    def change_graphics_quality(self, val):
        logging.info(f"User changed graphics quality to: {val}")
        if self.conn.websocket and self.conn.role == "controller":
            self.conn.send_input({
                "type": "change_quality",
                "quality": val
            })

    def handle_conn_result(self, status, message):
        self.btn_connect.configure(state="normal", text="Connect to Client")
        if status == "error":
            messagebox.showerror("Connection Error", message)
        elif status == "denied":
            messagebox.showwarning("Connection Denied", message)
        elif status == "approved":
            logging.info("Remote connection approved!")

    def prompt_permission(self, from_username):
        # Format the username with space if it is 6 digits
        display_name = from_username
        if len(from_username) == 6 and from_username.isdigit():
            display_name = f"{from_username[:3]} {from_username[3:]}"

        # Create a beautiful custom dialog window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Incoming Control Request")
        dialog.geometry("380x180")
        dialog.resizable(False, False)
        
        # Modal setup
        dialog.transient(self)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        lbl = ctk.CTkLabel(
            frame, 
            text=f"User '{display_name}' wants to\nremote control your computer.\n\nDo you allow this?",
            justify="center",
            font=ctk.CTkFont(size=13)
        )
        lbl.pack(pady=15)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=5)

        def on_allow():
            dialog.destroy()
            self.conn.respond_permission(approved=True)

        def on_deny():
            dialog.destroy()
            self.conn.respond_permission(approved=False)

        btn_allow = ctk.CTkButton(btn_frame, text="Allow", width=100, fg_color="green", hover_color="darkgreen", command=on_allow)
        btn_allow.pack(side="left", padx=10)

        btn_deny = ctk.CTkButton(btn_frame, text="Deny", width=100, fg_color="red", hover_color="darkred", command=on_deny)
        btn_deny.pack(side="right", padx=10)

    # --- Active Session Actions ---

    def handle_session_started(self, role):
        logging.info(f"Session started as {role}")
        self.btn_connect.configure(state="disabled", text="Active Session")
        
        if role == "host":
            self.update_conn_status("Hosting active remote control")
            
        elif role == "controller":
            # Open Viewer Window
            self.open_viewer_window()
            self.update_conn_status("Controlling remote client")

    def handle_session_ended(self, reason):
        logging.info(f"Session ended: {reason}")
        self.btn_connect.configure(state="normal", text="Connect to Client")
        
        if self.viewer_window:
            try:
                self.viewer_window.destroy()
            except Exception:
                pass
            self.viewer_window = None
            
        messagebox.showinfo("Session Info", f"Remote session ended: {reason}")
        self.update_conn_status("Connected to server")

    def handle_remote_input(self, event):
        # Simulate pynput input event received from the controller
        self.simulator.simulate_event(event)

    # --- Controller Viewer Window ---

    def open_viewer_window(self):
        if self.viewer_window:
            return

        self.viewer_window = ctk.CTkToplevel(self)
        self.viewer_window.title("Lighthouse Remote Viewer")
        self.viewer_window.geometry("1024x768")
        
        # Configure layout to be resizable
        self.viewer_window.grid_rowconfigure(0, weight=1)
        self.viewer_window.grid_columnconfigure(0, weight=1)

        # Create canvas for rendering screen frames
        self.viewer_canvas = tk.Canvas(self.viewer_window, bg="black", highlightthickness=0)
        self.viewer_canvas.grid(row=0, column=0, sticky="nsew")

        # Init state variables for scaling & aspect ratio
        self.viewer_initialized_size = False
        self.viewer_rendered_w = 0
        self.viewer_rendered_h = 0
        self.viewer_offset_x = 0
        self.viewer_offset_y = 0

        # Bind events
        self.viewer_canvas.bind("<Motion>", self.on_viewer_mouse_move)
        self.viewer_canvas.bind("<ButtonPress>", lambda e: self.on_viewer_mouse_click(e, pressed=True))
        self.viewer_canvas.bind("<ButtonRelease>", lambda e: self.on_viewer_mouse_click(e, pressed=False))
        self.viewer_canvas.bind("<MouseWheel>", self.on_viewer_mouse_scroll)
        
        # Keyboard binds on the window level
        self.viewer_window.bind("<KeyPress>", lambda e: self.on_viewer_key(e, pressed=True))
        self.viewer_window.bind("<KeyRelease>", lambda e: self.on_viewer_key(e, pressed=False))

        # Handle close window event
        self.viewer_window.protocol("WM_DELETE_WINDOW", self.close_viewer_window)

    def close_viewer_window(self):
        if messagebox.askyesno("Disconnect", "Do you want to end the remote session?"):
            self.conn.send_disconnect()
            if self.viewer_window:
                self.viewer_window.destroy()
                self.viewer_window = None

    def handle_screen_frame(self, jpeg_bytes):
        if not self.viewer_canvas or not self.viewer_window:
            return
            
        try:
            # Load received frame
            img = Image.open(io.BytesIO(jpeg_bytes))
            img_w, img_h = img.size
            aspect = img_w / img_h
            
            # 1. Automatically size the viewer window on the first received frame
            if not self.viewer_initialized_size:
                try:
                    # Get local client screen dimensions
                    screen_w = self.viewer_window.winfo_screenwidth()
                    screen_h = self.viewer_window.winfo_screenheight()
                    
                    # Target a comfortable max window size (e.g. 90% width, 80% height)
                    max_w = int(screen_w * 0.9)
                    max_h = int(screen_h * 0.8)
                    
                    if img_w <= max_w and img_h <= max_h:
                        target_w = img_w
                        target_h = img_h
                    else:
                        # Scale down remote dimensions to fit client screen preserving aspect ratio
                        if max_w / max_h > aspect:
                            target_h = max_h
                            target_w = int(max_h * aspect)
                        else:
                            target_w = max_w
                            target_h = int(max_w / aspect)
                            
                    self.viewer_window.geometry(f"{target_w}x{target_h}")
                    self.viewer_initialized_size = True
                except Exception as e:
                    logging.error(f"Error initializing window geometry: {e}")
                    self.viewer_initialized_size = True
            
            # 2. Resize remote screen image to fit canvas while preserving aspect ratio
            canvas_w = self.viewer_canvas.winfo_width()
            canvas_h = self.viewer_canvas.winfo_height()
            
            if canvas_w > 1 and canvas_h > 1:
                if canvas_w / canvas_h > aspect:
                    # Canvas is wider than image -> bound by height
                    self.viewer_rendered_h = canvas_h
                    self.viewer_rendered_w = int(canvas_h * aspect)
                else:
                    # Canvas is taller than image -> bound by width
                    self.viewer_rendered_w = canvas_w
                    self.viewer_rendered_h = int(canvas_w / aspect)
                
                # Center offset coordinates
                self.viewer_offset_x = (canvas_w - self.viewer_rendered_w) // 2
                self.viewer_offset_y = (canvas_h - self.viewer_rendered_h) // 2
                
                img = img.resize((self.viewer_rendered_w, self.viewer_rendered_h), Image.Resampling.BILINEAR)
            else:
                self.viewer_rendered_w = canvas_w
                self.viewer_rendered_h = canvas_h
                self.viewer_offset_x = 0
                self.viewer_offset_y = 0
                
            photo_img = ImageTk.PhotoImage(img)
            
            # Update canvas item with centering offsets
            self.viewer_canvas.delete("all")
            self.viewer_canvas.create_image(
                self.viewer_offset_x, 
                self.viewer_offset_y, 
                anchor="nw", 
                image=photo_img
            )
            self.viewer_canvas.image = photo_img # Prevent GC recycling
        except Exception as e:
            logging.error(f"Error rendering screen frame: {e}")

    # --- Mouse & Keyboard Capture Handlers ---

    def on_viewer_mouse_move(self, event):
        w = self.viewer_rendered_w
        h = self.viewer_rendered_h
        ox = self.viewer_offset_x
        oy = self.viewer_offset_y
        
        if w <= 0 or h <= 0:
            return

        # Calculate coordinates relative to the actual rendered remote desktop box
        img_x = event.x - ox
        img_y = event.y - oy
        
        # Normalize between 0.0 and 1.0 (clamping to display box boundary)
        x_norm = max(0.0, min(1.0, img_x / w))
        y_norm = max(0.0, min(1.0, img_y / h))

        # Throttle mouse motion to avoid flooding connection
        now = time.time()
        if now - self.last_mouse_send_time > 0.025: # Max ~40 pkts/sec
            self.conn.send_input({
                "type": "input",
                "event": "mouse_move",
                "x": x_norm,
                "y": y_norm
            })
            self.last_mouse_send_time = now

    def on_viewer_mouse_click(self, event, pressed):
        # Map Tkinter button indices to text names
        button_map = {1: "left", 2: "middle", 3: "right"}
        btn_name = button_map.get(event.num, "left")

        w = self.viewer_rendered_w
        h = self.viewer_rendered_h
        ox = self.viewer_offset_x
        oy = self.viewer_offset_y
        
        if w > 0 and h > 0:
            # Sync coordinate relative to rendered remote desktop box
            img_x = event.x - ox
            img_y = event.y - oy
            x_norm = max(0.0, min(1.0, img_x / w))
            y_norm = max(0.0, min(1.0, img_y / h))
            
            self.conn.send_input({
                "type": "input",
                "event": "mouse_move",
                "x": x_norm,
                "y": y_norm
            })

        self.conn.send_input({
            "type": "input",
            "event": "mouse_click",
            "button": btn_name,
            "pressed": pressed
        })

    def on_viewer_mouse_scroll(self, event):
        # Divide by 120 (Standard Windows delta increment)
        dy = int(event.delta / 120)
        self.conn.send_input({
            "type": "input",
            "event": "mouse_scroll",
            "dx": 0,
            "dy": dy
        })

    def on_viewer_key(self, event, pressed):
        # Check special mapping
        keysym = event.keysym
        if keysym in KEY_MAP:
            key_str = KEY_MAP[keysym]
        elif len(keysym) == 1:
            key_str = keysym
        elif event.char:
            key_str = event.char
        else:
            # Strip prefixes or return keysym directly
            key_str = keysym.lower()

        self.conn.send_input({
            "type": "input",
            "event": "key",
            "key": key_str,
            "pressed": pressed
        })

if __name__ == "__main__":
    app = LighthouseApp()
    app.mainloop()
