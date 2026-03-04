import sys
import os
import subprocess
import time
import signal

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT, "frontend")

_processes = []

def check_port(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_backend():
    if check_port(8000):
        print("Backend already running")
        return None
    print("Starting backend...")
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    _processes.append(proc)
    return proc

def start_frontend():
    if check_port(3000):
        print("Frontend already running")
        return None
    print("Starting frontend...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    proc = subprocess.Popen(
        [npm_cmd, "run", "start"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    _processes.append(proc)
    return proc

def wait_for_url(url, timeout=30):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except:
            time.sleep(0.5)
    return False

def main():
    print("Reddit Bot - Starting...")

    start_backend()
    frontend_proc = start_frontend()

    print("Waiting for frontend to be ready...")
    if not wait_for_url("http://localhost:3000", timeout=60):
        print("Warning: Frontend may not be ready")

    from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtCore import QUrl, QTimer
    from PyQt6.QtGui import QIcon, QAction

    app = QApplication(sys.argv)
    app.setApplicationName("Reddit Bot")
    app.setStyle("Fusion")

    window = QMainWindow()
    window.setWindowTitle("Reddit Bot")
    window.setGeometry(100, 100, 1100, 720)
    window.setMinimumSize(800, 600)

    browser = QWebEngineView()
    browser.setUrl(QUrl("http://localhost:3000"))
    window.setCentralWidget(browser)

    def on_closing():
        for proc in _processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                except:
                    pass
        window.close()
        app.quit()

    window.closeEvent = lambda e: (on_closing(), e.accept())

    window.show()
    print("App window opened!")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
