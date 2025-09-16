# GUI Launcher — API 서버 + Web UI 서버 (네트워크 접근/로그인 UI)
import os, sys, subprocess, threading, queue, time, webbrowser, signal, socket, secrets, pathlib
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = os.path.dirname(os.path.abspath(__file__))
PID_API = os.path.join(ROOT, ".api.pid")
PID_UI  = os.path.join(ROOT, ".ui.pid")
JWT_FILE = os.path.join(ROOT, "data", ".jwt_secret")

class Launcher:
    def __init__(self, master):
        self.master = master
        self.master.title("Modular Framework — Launcher")
        self.api_proc = None
        self.ui_proc = None
        self.log_q = queue.Queue()
        self.reload = tk.BooleanVar(value=True)
        self.external = tk.BooleanVar(value=True)  # 외부 접속 허용 기본 ON
        self.api_port = tk.StringVar(value="8000")
        self.ui_port  = tk.StringVar(value="5173")
        self._build_ui()
        self._ensure_jwt_secret()
        self._after()

    def _ensure_jwt_secret(self):
        os.makedirs(os.path.dirname(JWT_FILE), exist_ok=True)
        if not os.path.exists(JWT_FILE):
            sec = secrets.token_urlsafe(48)
            open(JWT_FILE, "w", encoding="utf-8").write(sec)
        # 주입
        os.environ["JWT_SECRET"] = open(JWT_FILE, "r", encoding="utf-8").read().strip()

    def _build_ui(self):
        nb = ttk.Notebook(self.master); nb.pack(fill="both", expand=True)

        tab1 = ttk.Frame(nb, padding=10); nb.add(tab1, text="서버")
        row = ttk.Frame(tab1); row.pack(fill="x")
        ttk.Button(row, text="의존성 설치/점검", command=self.install_deps).pack(side="left")
        ttk.Checkbutton(row, text="--reload", variable=self.reload).pack(side="left", padx=6)
        ttk.Checkbutton(row, text="외부 접속 허용(0.0.0.0)", variable=self.external).pack(side="left", padx=6)

        row2 = ttk.Frame(tab1); row2.pack(fill="x", pady=(8,6))
        ttk.Label(row2, text="API Port").pack(side="left"); ttk.Entry(row2, textvariable=self.api_port, width=6).pack(side="left", padx=(4,12))
        ttk.Label(row2, text="Web UI Port").pack(side="left"); ttk.Entry(row2, textvariable=self.ui_port, width=6).pack(side="left", padx=(4,12))

        row3 = ttk.Frame(tab1); row3.pack(fill="x", pady=(8,6))
        ttk.Button(row3, text="API 시작", command=self.start_api).pack(side="left")
        ttk.Button(row3, text="API 중단", command=self.stop_api).pack(side="left", padx=(6,12))
        ttk.Button(row3, text="Web UI 시작", command=self.start_ui).pack(side="left")
        ttk.Button(row3, text="Web UI 중단", command=self.stop_ui).pack(side="left", padx=(6,12))
        ttk.Button(row3, text="Open Web UI", command=self.open_ui).pack(side="right")

        self.url_lbl = ttk.Label(tab1, text="URL: -"); self.url_lbl.pack(anchor="w", pady=(4,6))

        self.log = tk.Text(tab1, height=18, state="disabled"); self.log.pack(fill="both", expand=True)

        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def _after(self):
        self._drain_logs()
        self.master.after(150, self._after)

    def _log(self, msg):
        self.log.configure(state="normal"); self.log.insert("end", msg+"\n"); self.log.see("end"); self.log.configure(state="disabled")

    def install_deps(self):
        req = os.path.join(ROOT, "requirements.txt")
        if not os.path.exists(req):
            messagebox.showerror("오류", "requirements.txt가 없습니다."); return
        cmd = [sys.executable, "-m", "pip", "install", "-r", req]
        self._log("$ " + " ".join(cmd))
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            for line in out.splitlines(): self._log(line)
            messagebox.showinfo("완료", "의존성 설치/점검 완료")
        except subprocess.CalledProcessError as e:
            self._log(e.output); messagebox.showerror("오류", "pip 설치 중 오류")

    def _host(self):
        return "0.0.0.0" if self.external.get() else "127.0.0.1"

    def _ip_hint(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
            return ip
        except Exception:
            return socket.gethostbyname(socket.gethostname())

    def start_api(self):
        if self.api_proc and self.api_proc.poll() is None:
            messagebox.showinfo("안내", "API 이미 실행 중"); return
        host = self._host(); port = self.api_port.get().strip() or "8000"
        env = os.environ.copy()
        # uvicorn command
        cmd = [sys.executable, "-m", "uvicorn", "server.main:app", "--host", host, "--port", port]
        if self.reload.get(): cmd.append("--reload")
        self._log("$ " + " ".join(cmd))
        self.api_proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        open(PID_API,"w").write(str(self.api_proc.pid))
        self._read_thread(self.api_proc, prefix="[API] ")
        self._update_url_label()

    def stop_api(self):
        self._stop_proc(self.api_proc, PID_API); self.api_proc = None

    def start_ui(self):
        if self.ui_proc and self.ui_proc.poll() is None:
            messagebox.showinfo("안내", "Web UI 이미 실행 중"); return
        host = self._host(); port = self.ui_port.get().strip() or "5173"
        cmd = [sys.executable, "-m", "uvicorn", "ui_web.app:app", "--host", host, "--port", port]
        if self.reload.get(): cmd.append("--reload")
        self._log("$ " + " ".join(cmd))
        self.ui_proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        open(PID_UI,"w").write(str(self.ui_proc.pid))
        self._read_thread(self.ui_proc, prefix="[WEB] ")
        self._update_url_label()

    def stop_ui(self):
        self._stop_proc(self.ui_proc, PID_UI); self.ui_proc = None

    def _stop_proc(self, proc, pidfile):
        if proc and proc.poll() is None:
            self._log("Stopping...")
            try:
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill()
            except Exception as e:
                self._log(f"terminate error: {e}")
        try:
            if os.path.exists(pidfile): os.remove(pidfile)
        except Exception: pass

    def _read_thread(self, proc, prefix=""):
        def run():
            for line in proc.stdout:
                self.log_q.put(prefix + line.rstrip())
        threading.Thread(target=run, daemon=True).start()

    def _drain_logs(self):
        try:
            while True: self._log(self.log_q.get_nowait())
        except queue.Empty: pass

    def _update_url_label(self):
        ip = self._ip_hint() if self.external.get() else "127.0.0.1"
        api = f"http://{ip}:{self.api_port.get()}"
        web = f"http://{ip}:{self.ui_port.get()}"
        self.url_lbl.configure(text=f"URL — API: {api} | Web UI: {web}")

    def open_ui(self):
        ip = self._ip_hint() if self.external.get() else "127.0.0.1"
        web = f"http://{ip}:{self.ui_port.get()}"
        webbrowser.open(web)

    def on_close(self):
        if messagebox.askyesno("확인", "종료하시겠습니까? 서버도 중단합니다."):
            self.stop_ui(); self.stop_api(); self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = Launcher(root); root.mainloop()
