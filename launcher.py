#!/usr/bin/env python3
"""
TwelveToneAnalyzer - Auto-updating Launcher
Cross-platform launcher: git-clone on first run, git-pull incremental updates, then launch main.py.
"""
import os, sys, subprocess, shutil, threading
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, QObject
REPO_URL = "https://github.com/Yvonne6475/TwelveToneAnalyzer.git"
REPO_BRANCH = "master"
BASE_DIR = Path.home() / ".twelve_tone_analyzer"
REPO_DIR = BASE_DIR / "repo"
VENV_DIR = BASE_DIR / "venv"
REQ_HASH_FILE = BASE_DIR / "req_hash.txt"

log_lines = []

def find_python():
    if getattr(sys, 'frozen', False):
        bundled = Path(sys._MEIPASS) / ("python.exe" if sys.platform == "win32" else "python3")
        if bundled.exists():
            return str(bundled)
        if sys.platform == "darwin":
            frameworks = Path(sys._MEIPASS).parent.parent / "Frameworks"
            for f in frameworks.glob("Python*"):
                py = f / "bin" / "python3"
                if py.exists():
                    return str(py)
    for name in ("python3", "python"):
        p = shutil.which(name)
        if p:
            return p
    return "python3"

def run(cmd, cwd=None, timeout=300):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def git_available():
    return shutil.which("git") is not None

def venv_python():
    if sys.platform == "win32":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python3")

def ensure_venv(progress_callback=None):
    py = find_python()
    current_hash = ""
    req_file = REPO_DIR / "requirements.txt"
    if not req_file.exists():
        req_file = REPO_DIR / "requirements_mac.txt"
    if req_file.exists():
        import hashlib
        hasher = hashlib.md5()
        for line in sorted(req_file.read_text().splitlines()):
            line = line.strip()
            if line and not line.startswith("#"):
                hasher.update(line.encode())
        current_hash = hasher.hexdigest()
    stored_hash = REQ_HASH_FILE.read_text().strip() if REQ_HASH_FILE.exists() else ""
    if VENV_DIR.exists() and current_hash and current_hash == stored_hash:
        return True
    if progress_callback:
        progress_callback("Creating Python venv...")
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR, ignore_errors=True)
    rc, out, err = run([py, "-m", "venv", str(VENV_DIR)])
    if rc != 0:
        if progress_callback:
            progress_callback(f"venv failed: {err}")
        return False
    vpy = venv_python()
    if progress_callback:
        progress_callback("Installing pip...")
    run([vpy, "-m", "pip", "install", "--upgrade", "pip"], timeout=120)
    if progress_callback:
        progress_callback("Installing dependencies...")
    for req_name in ("requirements.txt", "requirements_mac.txt"):
        req_path = REPO_DIR / req_name
        if req_path.exists():
            rc, out, err = run([vpy, "-m", "pip", "install", "-r", str(req_path)], timeout=600)
            if rc == 0:
                break
    if current_hash:
        REQ_HASH_FILE.write_text(current_hash)
    return True


class LauncherBridge(QObject):
    """Thread-safe bridge: background thread emits signals, main thread updates UI."""
    status_signal = pyqtSignal(str)
    label_signal = pyqtSignal(str)
    done_signal = pyqtSignal(int, str)  # exit_code, error_message


def main_workflow(bridge):
    def _status(msg):
        log_lines.append(msg)
        bridge.status_signal.emit("\n".join(log_lines[-12:]))

    def _label(msg):
        bridge.label_signal.emit(msg)

    if not git_available():
        _status("[X] Git not found. Install from https://git-scm.com")
        bridge.label_signal.emit("Git Required")
        bridge.done_signal.emit(1, "Git not found")
        return

    BASE_DIR.mkdir(parents=True, exist_ok=True)

    if not REPO_DIR.exists():
        _label("Downloading...")
        _status("First install - cloning repository...")
        rc, out, err = run(["git", "clone", "--depth", "1", "--branch", REPO_BRANCH, REPO_URL, str(REPO_DIR)], timeout=300)
        if rc != 0:
            _status(f"[X] Clone failed: {err}")
            bridge.done_signal.emit(1, err)
            return
        _status("[OK] Repository cloned")
    else:
        _label("Checking for updates...")
        _status("Fetching latest changes...")
        rc, out, err = run(["git", "fetch", "--depth", "1", "origin", REPO_BRANCH], cwd=REPO_DIR, timeout=30)
        if rc == 0:
            rc2, out2, err2 = run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], cwd=REPO_DIR, timeout=30)
            if rc2 == 0:
                _status("[OK] Up to date" if "HEAD is now at" in out2 else "[OK] Updated to latest")
            else:
                _status("[!] Offline mode - using cached version")
        else:
            _status("[!] Offline mode - using cached version")

    _label("Setting up environment...")
    if not ensure_venv(progress_callback=_status):
        _status("[X] Environment setup failed")
        bridge.done_signal.emit(1, "venv setup failed")
        return

    _status("[OK] Environment ready")
    _label("Launching...")
    _status("Starting TwelveToneAnalyzer...")

    bridge.done_signal.emit(0, "")  # 0 = success, launch main.py


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QTextEdit
    from PyQt5.QtCore import Qt, pyqtSignal, QObject
    from PyQt5.QtGui import QFont

    app = QApplication(sys.argv)
    app.setApplicationName("TMA Launcher")

    window = QWidget()
    window.setWindowTitle("TwelveToneAnalyzer - Updating...")
    window.setFixedSize(480, 320)
    window.setWindowFlags(window.windowFlags() | Qt.WindowStaysOnTopHint)

    screen = app.primaryScreen()
    if screen:
        cp = screen.availableGeometry().center()
        qr = window.frameGeometry()
        qr.moveCenter(cp)
        window.move(qr.topLeft())

    layout = QVBoxLayout(window)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(12)

    label_widget = QLabel("Checking for updates...")
    label_widget.setFont(QFont("Helvetica Neue", 16, QFont.Bold))
    label_widget.setAlignment(Qt.AlignCenter)
    layout.addWidget(label_widget)

    progress = QProgressBar()
    progress.setRange(0, 0)
    progress.setTextVisible(False)
    layout.addWidget(progress)

    status_widget = QTextEdit()
    status_widget.setReadOnly(True)
    status_widget.setFont(QFont("Menlo", 11))
    status_widget.setMaximumHeight(180)
    status_widget.setStyleSheet("QTextEdit { background: transparent; border: none; }")
    layout.addWidget(status_widget)

    window.show()

    bridge = LauncherBridge()

    def _on_status(text):
        status_widget.setPlainText(text)
        bar = status_widget.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_label(text):
        label_widget.setText(text)

    def _on_done(exit_code, error):
        progress.setRange(0, 100)
        progress.setValue(100)
        if exit_code != 0:
            window.setWindowTitle("TMA - Error")
            label_widget.setText("Failed")
            status_widget.append(f"\n[X] {error}")
            return
        window.hide()
        vpy = venv_python()
        main_py = REPO_DIR / "main.py"
        if not main_py.exists():
            window.show()
            label_widget.setText("Error")
            status_widget.append(f"\n[X] main.py not found: {main_py}")
            return
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        try:
            subprocess.run([vpy, str(main_py)], cwd=REPO_DIR, env=env)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            window.show()
            label_widget.setText("Launch Failed")
            status_widget.append(f"\n[X] Error: {e}")
        sys.exit(0)

    bridge.status_signal.connect(_on_status)
    bridge.label_signal.connect(_on_label)
    bridge.done_signal.connect(_on_done)

    threading.Thread(target=main_workflow, args=(bridge,), daemon=True).start()
    app.exec_()
