#!/usr/bin/env python3
"""
TwelveToneAnalyzer - Auto-updating Launcher
Cross-platform launcher: git-clone on first run, git-pull incremental updates, then launch main.py.
"""
import os, sys, subprocess, shutil, threading
from pathlib import Path

REPO_URL = "https://github.com/Yvonne6475/TwelveToneAnalyzer.git"
REPO_BRANCH = "master"
BASE_DIR = Path.home() / ".twelve_tone_analyzer"
REPO_DIR = BASE_DIR / "repo"
VENV_DIR = BASE_DIR / "venv"
REQ_HASH_FILE = BASE_DIR / "req_hash.txt"

log_lines = []
_qt_app = None
_label = None
_progress = None
_status = None
_window = None

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

def _create_ui():
    global _qt_app, _label, _progress, _status, _window
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QTextEdit
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    _qt_app = QApplication.instance() or QApplication(sys.argv)
    _qt_app.setApplicationName("TMA Launcher")
    _window = QWidget()
    _window.setWindowTitle("TwelveToneAnalyzer - Updating...")
    _window.setFixedSize(480, 320)
    _window.setWindowFlags(_window.windowFlags() | Qt.WindowStaysOnTopHint)
    screen = _qt_app.primaryScreen()
    if screen:
        cp = screen.availableGeometry().center()
        qr = _window.frameGeometry()
        qr.moveCenter(cp)
        _window.move(qr.topLeft())
    layout = QVBoxLayout(_window)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(12)
    _label = QLabel("Checking for updates...")
    font = QFont("Segoe UI" if sys.platform == "win32" else "Helvetica Neue", 16, QFont.Bold)
    _label.setFont(font)
    _label.setAlignment(Qt.AlignCenter)
    layout.addWidget(_label)
    _progress = QProgressBar()
    _progress.setRange(0, 0)
    _progress.setTextVisible(False)
    layout.addWidget(_progress)
    _status = QTextEdit()
    _status.setReadOnly(True)
    _status.setFont(QFont("Consolas" if sys.platform == "win32" else "Menlo", 11))
    _status.setMaximumHeight(180)
    _status.setStyleSheet("QTextEdit { background: transparent; border: none; }")
    layout.addWidget(_status)
    _window.show()
    _qt_app.processEvents()

def update_status(msg):
    log_lines.append(msg)
    if _status:
        _status.setPlainText("\n".join(log_lines[-12:]))
        bar = _status.verticalScrollBar()
        bar.setValue(bar.maximum())
    if _qt_app:
        _qt_app.processEvents()

def update_label(msg):
    if _label:
        _label.setText(msg)
        if _qt_app:
            _qt_app.processEvents()

def main_workflow():
    if not git_available():
        update_status("[X] Git not found. Install from https://git-scm.com")
        if _progress:
            _progress.setRange(0, 100)
            _progress.setValue(100)
        if _window:
            _window.setWindowTitle("TMA - Error")
        update_label("Git Required")
        _qt_app and _qt_app.exec_()
        sys.exit(1)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    if not REPO_DIR.exists():
        update_label("Downloading...")
        update_status("First install - cloning repository...")
        rc, out, err = run(["git", "clone", "--depth", "1", "--branch", REPO_BRANCH, REPO_URL, str(REPO_DIR)], timeout=300)
        if rc != 0:
            update_status(f"[X] Clone failed: {err}")
            _qt_app and _qt_app.exec_()
            sys.exit(1)
        update_status("[OK] Repository cloned")
    else:
        update_label("Checking for updates...")
        update_status("Fetching latest changes...")
        rc, out, err = run(["git", "fetch", "--depth", "1", "origin", REPO_BRANCH], cwd=REPO_DIR, timeout=30)
        if rc == 0:
            rc2, out2, err2 = run(["git", "reset", "--hard", f"origin/{REPO_BRANCH}"], cwd=REPO_DIR, timeout=30)
            if rc2 == 0:
                update_status("[OK] Up to date" if "HEAD is now at" in out2 else "[OK] Updated to latest")
            else:
                update_status("[!] Offline mode - using cached version")
        else:
            update_status("[!] Offline mode - using cached version")
    update_label("Setting up environment...")
    if not ensure_venv(progress_callback=update_status):
        update_status("[X] Environment setup failed")
        _qt_app and _qt_app.exec_()
        sys.exit(1)
    update_status("[OK] Environment ready")
    update_label("Launching...")
    update_status("Starting TwelveToneAnalyzer...")
    if _progress:
        _progress.setRange(0, 100)
        _progress.setValue(100)
    _qt_app and _qt_app.processEvents()
    if _window:
        _window.hide()
    vpy = venv_python()
    main_py = REPO_DIR / "main.py"
    if not main_py.exists():
        update_status(f"[X] main.py not found: {main_py}")
        _window and _window.show()
        _qt_app and _qt_app.exec_()
        sys.exit(1)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        subprocess.run([vpy, str(main_py)], cwd=REPO_DIR, env=env)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        update_label("Launch Failed")
        update_status(f"[X] Error: {e}")
        _window and _window.show()
        _qt_app and _qt_app.exec_()
        sys.exit(1)

if __name__ == "__main__":
    try:
        _create_ui()
        threading.Thread(target=main_workflow, daemon=True).start()
        _qt_app.exec_()
    except Exception:
        main_workflow()
