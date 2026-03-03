"""
Reddit Bot - Native App Launcher (Production Mode)
─────────────────────────────────────────────────
Uses `next start` (production) instead of `next dev`.
Production mode starts in ~1-2s vs 20-60s for dev mode.

Strategy for near-instant open (like ExpressVPN):
 1. If servers are already running → open window immediately (< 1s)
 2. If cold start → open window with splash screen immediately,
    background-load the real app once services are ready.
"""
import subprocess
import sys
import time
import os
import threading
import socket
import urllib.request
import webview

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")

# ── Inline splash page shown while services start ──────────────────────────
SPLASH_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #0d1424;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    height: 100vh; font-family: -apple-system, 'Inter', sans-serif;
    color: #fff;
  }
  .logo {
    width: 52px; height: 52px; border-radius: 16px;
    background: #ff5a5f;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 20px;
    box-shadow: 0 0 40px rgba(255,90,95,0.35);
    animation: pulse 2s ease-in-out infinite;
  }
  .logo svg { width: 26px; height: 26px; fill: white; }
  h1 { font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }
  p  { font-size: 12px; color: #4b5563; margin-top: 8px; }
  .dots { display: flex; gap: 6px; margin-top: 28px; }
  .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #ff5a5f; opacity: 0.3;
    animation: blink 1.2s ease-in-out infinite;
  }
  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink {
    0%, 80%, 100% { opacity: 0.2; }
    40%           { opacity: 1;   }
  }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 30px rgba(255,90,95,0.3); }
    50%       { box-shadow: 0 0 55px rgba(255,90,95,0.5); }
  }
</style>
</head>
<body>
  <div class="logo">
    <svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/></svg>
  </div>
  <h1>Reddit Bot</h1>
  <p id="status">Starting services\u2026</p>
  <div class="dots">
    <div class="dot"></div>
    <div class="dot"></div>
    <div class="dot"></div>
  </div>

  <script>
    // Self-contained polling — no Python threads needed.
    // fetch() with no-cors succeeds as long as the server accepts the connection,
    // regardless of CORS headers or response body. Perfect for readiness probing.
    const BACKEND  = 'http://localhost:8000/health';
    const FRONTEND = 'http://localhost:3000';
    const status   = document.getElementById('status');

    async function probe(url) {
      try { await fetch(url, { mode: 'no-cors', cache: 'no-store' }); return true; }
      catch { return false; }
    }

    async function waitAndRedirect() {
      let backendOk = false, frontendOk = false;
      while (true) {
        if (!backendOk)  backendOk  = await probe(BACKEND);
        if (!frontendOk) frontendOk = await probe(FRONTEND);

        if (backendOk && frontendOk) {
          status.textContent = 'Ready \u2014 opening\u2026';
          await new Promise(r => setTimeout(r, 300));
          window.location.href = FRONTEND;
          return;
        }

        status.textContent = !backendOk ? 'Starting API\u2026' : 'Starting frontend\u2026';
        await new Promise(r => setTimeout(r, 500));
      }
    }

    waitAndRedirect();
  </script>
</body>
</html>"""


# ── Port helpers ──────────────────────────────────────────────────────────

def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_port(port: int, label: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(port):
            return True
        time.sleep(0.25)
    print(f"  ⚠️  Timeout waiting for {label}", flush=True)
    return False


def wait_for_http(url: str, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5):
                return True
        except Exception:
            time.sleep(0.3)
    return False


def kill_port_owner(port: int):
    """Force kill any process holding the specified port. Cross-platform."""
    try:
        if os.name == 'nt':  # Windows
            # Get PIDs holding the port using netstat
            cmd = f'netstat -ano | findstr :{port}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")
            pids = set()
            for line in lines:
                parts = line.split()
                if len(parts) > 4:
                    pids.add(parts[-1])
            
            if pids:
                print(f"  ⚠️  Cleaning up orphan process on port {port} (PIDs: {', '.join(pids)})...", flush=True)
                for pid in pids:
                    try:
                        subprocess.run(["taskkill", "/F", "/PID", pid], check=False, creationflags=subprocess.CREATE_NO_WINDOW)
                    except:
                        pass
        else:  # macOS/Linux
            # Get PIDs holding the port using lsof
            try:
                result = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
                pids = result.strip().split("\n")
                if pids and pids[0]:
                    print(f"  ⚠️  Cleaning up orphan process on port {port} (PIDs: {', '.join(pids)})...", flush=True)
                    for pid in pids:
                        try:
                            subprocess.run(["kill", "-9", pid], check=False)
                        except:
                            pass
            except subprocess.CalledProcessError:
                pass # lsof returns exit code 1 if no process found
    except Exception as e:
        print(f"  ⚠️  Note: Could not auto-clear port {port}: {e}", flush=True)


# ── Process starters ──────────────────────────────────────────────────────

def start_backend():
    if is_port_open(8000):
        print("  ✅ Backend already running", flush=True)
        return None
    
    print("  → Starting API backend\u2026", flush=True)
    
    # Ensure logs directory exists
    logs_dir = os.path.join(ROOT, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    stdout_log = open(os.path.join(logs_dir, "backend_stdout.log"), "a")
    stderr_log = open(os.path.join(logs_dir, "backend_stderr.log"), "a")
    
    stdout_log.write(f"\n--- Starting Backend at {time.ctime()} ---\n")
    stderr_log.write(f"\n--- Starting Backend at {time.ctime()} ---\n")
    
    return subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=ROOT,
        stdout=stdout_log,
        stderr=stderr_log,
    )


def start_frontend():
    if is_port_open(3000):
        print("  ✅ Frontend already running", flush=True)
        return None
    
    print("  → Starting frontend (production)\u2026", flush=True)
    
    # Ensure logs directory exists
    logs_dir = os.path.join(ROOT, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    stdout_log = open(os.path.join(logs_dir, "frontend_stdout.log"), "a")
    stderr_log = open(os.path.join(logs_dir, "frontend_stderr.log"), "a")
    
    stdout_log.write(f"\n--- Starting Frontend at {time.ctime()} ---\n")
    stderr_log.write(f"\n--- Starting Frontend at {time.ctime()} ---\n")
    
    return subprocess.Popen(
        ["npm", "run", "start"],
        cwd=FRONTEND_DIR,
        stdout=stdout_log,
        stderr=stderr_log,
    )


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("\n🚀 Reddit Bot - Launching\u2026\n", flush=True)

    # Clean up stale processes
    kill_port_owner(8000)
    kill_port_owner(3000)

    backend_proc = start_backend()
    frontend_proc = start_frontend()

    def on_closing():
        if backend_proc:
            backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()

    # Always open with the self-redirecting splash.
    # The JavaScript inside polls /health + port 3000 every 500ms and
    # navigates to http://localhost:3000 the moment both respond.
    # No threading, no Python-side navigation — clean and reliable.
    window = webview.create_window(
        title="Reddit Bot",
        html=SPLASH_HTML,          # inline HTML, no URL needed
        width=1100,
        height=720,
        min_size=(800, 600),
        resizable=True,
        frameless=False,
        easy_drag=False,
        background_color="#0d1424",
    )

    window.events.closed += on_closing
    webview.start(debug=False)


if __name__ == "__main__":
    main()
