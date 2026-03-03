"""
Reddit Bot - Native App Launcher
Opens the Next.js web UI in a native macOS WebKit window using pywebview.
Starts the FastAPI backend and Next.js dev server as background processes.
"""
import subprocess
import sys
import time
import os
import threading
import socket
import webview

ROOT = os.path.dirname(os.path.abspath(__file__))


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.3) -> bool:
    """Check if a port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_port(port: int, label: str, timeout: int = 30):
    """Block until the given port is accepting connections or timeout."""
    print(f"  ⏳ Waiting for {label} (port {port})...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(port):
            print(f"  ✅ {label} is ready", flush=True)
            return True
        time.sleep(0.3)
    print(f"  ⚠️  Timeout waiting for {label}", flush=True)
    return False


def start_backend():
    """Start the FastAPI backend server."""
    if is_port_open(8000):
        print("  ✅ Backend already running on port 8000", flush=True)
        return None
    print("  → Starting Python API backend...", flush=True)
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def start_frontend():
    """Start the Next.js frontend dev server."""
    if is_port_open(3000):
        print("  ✅ Frontend already running on port 3000", flush=True)
        return None
    print("  → Starting Next.js frontend...", flush=True)
    frontend_dir = os.path.join(ROOT, "frontend")
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def main():
    print("\n🚀 Reddit Bot - Launching Native App...\n", flush=True)

    # Start both servers
    backend_proc = start_backend()
    frontend_proc = start_frontend()

    # Wait for both to be ready
    wait_for_port(8000, "API Backend")
    wait_for_port(3000, "Frontend", timeout=60)

    print("\n  ✅ All services ready — opening app window...\n", flush=True)

    # Open native WebKit window (no browser bar, no tabs)
    window = webview.create_window(
        title="Reddit Bot",
        url="http://localhost:3000",
        width=1100,
        height=720,
        min_size=(800, 600),
        resizable=True,
        frameless=False,   # Keep OS title bar for native feel
        easy_drag=False,
        background_color="#0f172a",
    )

    def on_closing():
        """Kill child processes when the window is closed."""
        print("\n  Shutting down...", flush=True)
        if backend_proc:
            backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()

    window.events.closed += on_closing

    # Start the native window (blocks until closed)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
