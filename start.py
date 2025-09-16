# One-File GUI Dev Launcher (Tkinter)
# - 버튼으로 서버 실행/중단/헬스 체크/테스트 호출
# - 의존성 자동 설치/점검 (pip)
# - 서버는 UI를 서빙하지 않음 (분리 프로세스)

import os, sys, subprocess, threading, queue, time, webbrowser, json, urllib.request, urllib.error, signal
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

ROOT = os.path.dirname(os.path.abspath(__file__))
PIDFILE = os.path.join(ROOT, ".server.pid")
HOST = "127.0.0.1"
PORT = 8000

class LauncherApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Modular Framework — GUI Launcher")
        self.server_proc = None
        self.log_q = queue.Queue()
        self.reader_thread = None
        self.reload = tk.BooleanVar(value=True)  # dev 편의: 파일 변경 자동 반영
        self._build_ui()
        self._try_attach_existing()

    # ---------- UI ----------
    def _build_ui(self):
        frm = ttk.Frame(self.master, padding=10)
        frm.pack(fill="both", expand=True)

        row1 = ttk.Frame(frm); row1.pack(fill="x", pady=(0,8))
        ttk.Button(row1, text="의존성 설치/점검", command=self.install_deps).pack(side="left")
        ttk.Checkbutton(row1, text="파일 변경 자동 반영(--reload)", variable=self.reload).pack(side="right")

        row2 = ttk.Frame(frm); row2.pack(fill="x", pady=(0,8))
        ttk.Button(row2, text="서버 실행", command=self.start_server).pack(side="left", padx=(0,6))
        ttk.Button(row2, text="서버 중단", command=self.stop_server).pack(side="left")
        ttk.Button(row2, text="/health 열기", command=self.open_health).pack(side="right")

        row3 = ttk.Frame(frm); row3.pack(fill="x", pady=(0,8))
        ttk.Button(row3, text="PING 테스트 호출", command=self.call_ping).pack(side="left")
        self.status_lbl = ttk.Label(row3, text="Status: STOPPED ⏹️")
        self.status_lbl.pack(side="right")

        # 로그
        self.log = tk.Text(frm, height=18, width=100)
        self.log.configure(state="disabled")
        self.log.pack(fill="both", expand=True)
        self._log("Launcher ready. One-file GUI. No CLI needed.")

        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

        # periodic log drain
        self.master.after(150, self._drain_logs)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------- Dependency ----------
    def install_deps(self):
        req = os.path.join(ROOT, "requirements.txt")
        if not os.path.exists(req):
            messagebox.showerror("오류", "requirements.txt가 없습니다.")
            return
        cmd = [sys.executable, "-m", "pip", "install", "-r", req]
        self._log(f"$ {' '.join(cmd)}")
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            for line in out.splitlines():
                self._log(line)
            messagebox.showinfo("완료", "의존성 설치/점검 완료")
        except subprocess.CalledProcessError as e:
            self._log(e.output)
            messagebox.showerror("오류", "pip 설치 중 오류가 발생했습니다. 로그를 확인하세요.")

    # ---------- Server control ----------
    def _uvicorn_cmd(self):
        args = [sys.executable, "-m", "uvicorn", "server.main:app", "--host", HOST, "--port", str(PORT)]
        if self.reload.get():
            args.append("--reload")
        return args

    def start_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            messagebox.showinfo("안내", "이미 실행 중입니다.")
            return
        cmd = self._uvicorn_cmd()
        self._log(f"$ {' '.join(cmd)}")
        try:
            self.server_proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        except FileNotFoundError:
            messagebox.showerror("오류", "uvicorn(및 의존성)이 설치되지 않았습니다. [의존성 설치/점검]을 먼저 눌러주세요.")
            return
        with open(PIDFILE, "w") as f:
            f.write(str(self.server_proc.pid))
        self.status_lbl.configure(text="Status: RUNNING ✅")
        self.reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self.reader_thread.start()
        self._log("Server starting...")

    def _read_stdout(self):
        assert self.server_proc and self.server_proc.stdout
        for line in self.server_proc.stdout:
            self.log_q.put(line.rstrip("\n"))
        # process ended
        self.log_q.put("** server process ended **")

    def _drain_logs(self):
        try:
            while True:
                line = self.log_q.get_nowait()
                self._log(line)
        except queue.Empty:
            pass
        # status check
        if self.server_proc and self.server_proc.poll() is not None:
            self.status_lbl.configure(text="Status: STOPPED ⏹️")
            try:
                if os.path.exists(PIDFILE):
                    os.remove(PIDFILE)
            except Exception:
                pass
        self.master.after(150, self._drain_logs)

    def stop_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            self._log("Stopping server...")
            try:
                self.server_proc.terminate()
                try:
                    self.server_proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.server_proc.kill()
            except Exception as e:
                self._log(f"terminate error: {e}")
            finally:
                self.server_proc = None
                try:
                    if os.path.exists(PIDFILE):
                        os.remove(PIDFILE)
                except Exception:
                    pass
                self.status_lbl.configure(text="Status: STOPPED ⏹️")
        else:
            # try pidfile
            if os.path.exists(PIDFILE):
                try:
                    pid = int(open(PIDFILE).read().strip())
                    if os.name == "nt":
                        subprocess.call(["taskkill", "/PID", str(pid), "/F"])
                    else:
                        os.kill(pid, signal.SIGTERM)
                    self._log(f"Sent SIGTERM to pid {pid}")
                except Exception as e:
                    self._log(f"pidfile kill failed: {e}")
                finally:
                    try: os.remove(PIDFILE)
                    except Exception: pass
            else:
                messagebox.showinfo("안내", "실행 중인 서버가 없습니다.")

    def _try_attach_existing(self):
        # when GUI 재시작 시 남아있는 pidfile 처리(최소한의 방어)
        if os.path.exists(PIDFILE):
            self.status_lbl.configure(text="Status: (unknown) PID file exists")
            self._log("주의: 이전 서버 PID 파일이 남아있습니다. [서버 중단]을 눌러 정리하세요.")

    # ---------- Utilities ----------
    def open_health(self):
        webbrowser.open(f"http://{HOST}:{PORT}/health")

    def call_ping(self):
        url = f"http://{HOST}:{PORT}/run?name=modules.common.ping"
        data = {
            "action": "PING",
            "mode": "SINGLE",
            "input": {"echo": "hello"}
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                self._log(f"[PING] {body}")
                messagebox.showinfo("PING 결과", body)
        except urllib.error.URLError as e:
            self._log(f"[PING] 실패: {e}")
            messagebox.showerror("오류", f"PING 실패: {e}")

    def on_close(self):
        if self.server_proc and self.server_proc.poll() is None:
            if not messagebox.askyesno("확인", "서버가 실행 중입니다. 종료하시겠습니까?"):
                return
            self.stop_server()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()
