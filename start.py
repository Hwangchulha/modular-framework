# start.py — One‑File GUI with "이체" 메인 화면 (Tkinter)
import os, sys, subprocess, threading, queue, time, webbrowser, json, urllib.request, urllib.error, signal, zipfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

ROOT = os.path.dirname(os.path.abspath(__file__))
PIDFILE = os.path.join(ROOT, ".server.pid")
HOST = "127.0.0.1"
PORT = 8000

def fmt_money(v: int) -> str:
    try:
        return f"{int(v):,} 원"
    except Exception:
        return str(v)

class LauncherApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Modular Framework — GUI")
        self.server_proc = None
        self.log_q = queue.Queue()
        self.reader_thread = None
        self.reload = tk.BooleanVar(value=True)

        # Transfer form state
        self.sel_from_acc = tk.StringVar()
        self.sel_bank = tk.StringVar()
        self.to_acct = tk.StringVar()
        self.receiver = tk.StringVar()
        self.amount = tk.StringVar()
        self.memo = tk.StringVar()

        self._build_ui()
        self._try_attach_existing()

    # ---------- UI ----------
    def _build_ui(self):
        nb = ttk.Notebook(self.master)
        nb.pack(fill="both", expand=True)

        # Tab 1: 운영/서버
        tab_ops = ttk.Frame(nb, padding=10)
        nb.add(tab_ops, text="운영/서버")

        top = ttk.Frame(tab_ops); top.pack(fill="x", pady=(0,8))
        ttk.Button(top, text="의존성 설치/점검", command=self.install_deps).pack(side="left")
        ttk.Checkbutton(top, text="파일 변경 자동 반영(--reload)", variable=self.reload).pack(side="right")

        row = ttk.Frame(tab_ops); row.pack(fill="x", pady=(0,8))
        ttk.Button(row, text="서버 실행", command=self.start_server).pack(side="left", padx=(0,6))
        ttk.Button(row, text="서버 중단", command=self.stop_server).pack(side="left")
        ttk.Button(row, text="/health 열기", command=self.open_health).pack(side="right")

        row2 = ttk.Frame(tab_ops); row2.pack(fill="x", pady=(0,8))
        ttk.Button(row2, text="PING 테스트", command=self.call_ping).pack(side="left")
        ttk.Button(row2, text="Ops Snapshot", command=self.ops_snapshot).pack(side="left", padx=(6,0))
        ttk.Button(row2, text="모듈 설치(.zip)", command=self.install_module_zip).pack(side="right")

        self.log = tk.Text(tab_ops, height=16, width=100, state="disabled"); self.log.pack(fill="both", expand=True)
        self.status_lbl = ttk.Label(tab_ops, text="Status: STOPPED ⏹️"); self.status_lbl.pack(anchor="e")

        # Tab 2: 이체
        tab_tr = ttk.Frame(nb, padding=12)
        nb.add(tab_tr, text="이체")

        head = ttk.Frame(tab_tr); head.pack(fill="x")
        ttk.Button(head, text="데모 데이터 초기화", command=self.demo_init).pack(side="right")

        form = ttk.Frame(tab_tr); form.pack(fill="x", pady=(8,8))

        # 출금계좌
        ttk.Label(form, text="출금계좌").grid(row=0, column=0, sticky="w", padx=(0,8), pady=4)
        self.cmb_from = ttk.Combobox(form, textvariable=self.sel_from_acc, state="readonly", width=38)
        self.cmb_from.grid(row=0, column=1, sticky="we", pady=4)
        ttk.Button(form, text="잔액조회", command=self.query_balance).grid(row=0, column=2, padx=6, pady=4)
        self.lbl_balance = ttk.Label(form, text="—")
        self.lbl_balance.grid(row=0, column=3, padx=6, pady=4)

        # 입금은행/계좌
        ttk.Label(form, text="입금은행").grid(row=1, column=0, sticky="w", padx=(0,8), pady=4)
        self.cmb_bank = ttk.Combobox(form, textvariable=self.sel_bank, state="readonly", width=24)
        self.cmb_bank.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(form, text="입금계좌").grid(row=2, column=0, sticky="w", padx=(0,8), pady=4)
        ttk.Entry(form, textvariable=self.to_acct, width=30).grid(row=2, column=1, sticky="w", pady=4)

        # 금액/받는분/메모
        ttk.Label(form, text="금액").grid(row=3, column=0, sticky="w", padx=(0,8), pady=4)
        ttk.Entry(form, textvariable=self.amount, width=18).grid(row=3, column=1, sticky="w", pady=4)

        ttk.Label(form, text="받는분").grid(row=4, column=0, sticky="w", padx=(0,8), pady=4)
        ttk.Entry(form, textvariable=self.receiver, width=18).grid(row=4, column=1, sticky="w", pady=4)

        ttk.Label(form, text="메모").grid(row=5, column=0, sticky="w", padx=(0,8), pady=4)
        ttk.Entry(form, textvariable=self.memo, width=40).grid(row=5, column=1, sticky="we", columnspan=2, pady=4)

        # 액션 버튼
        actions = ttk.Frame(tab_tr); actions.pack(fill="x", pady=(6,6))
        ttk.Button(actions, text="수수료 미리보기", command=self.transfer_quote).pack(side="left")
        ttk.Button(actions, text="이체 실행", command=self.transfer_submit).pack(side="left", padx=(6,0))

        # 결과 박스
        self.tr_out = tk.Text(tab_tr, height=10, state="disabled")
        self.tr_out.pack(fill="both", expand=True)

        # 초기 로드
        self.load_accounts()
        self.load_banks()

        # schedule log drain
        self.master.after(150, self._drain_logs)

    # ---------- Utils ----------
    def _try_attach_existing(self):
        if os.path.exists(PIDFILE):
            self.status_lbl.configure(text="Status: (unknown) PID file exists")
            self._log("주의: 이전 서버 PID 파일이 남아있습니다. [서버 중단]으로 정리하세요.")
        else:
            self.status_lbl.configure(text="Status: STOPPED ⏹️")

    def _log(self, msg):
        self.log.configure(state="normal"); self.log.insert("end", msg+"\n"); self.log.see("end"); self.log.configure(state="disabled")

    def _api_post(self, path, body):
        url = f"http://{HOST}:{PORT}{path}"
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ---------- Server ops ----------
    def install_deps(self):
        req = os.path.join(ROOT, "requirements.txt")
        if not os.path.exists(req):
            messagebox.showerror("오류", "requirements.txt가 없습니다."); return
        cmd = [sys.executable, "-m", "pip", "install", "-r", req]
        self._log(f"$ {' '.join(cmd)}")
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            for line in out.splitlines(): self._log(line)
            messagebox.showinfo("완료", "의존성 설치/점검 완료")
        except subprocess.CalledProcessError as e:
            self._log(e.output); messagebox.showerror("오류", "pip 설치 중 오류가 발생했습니다.")

    def _uvicorn_cmd(self):
        args = [sys.executable, "-m", "uvicorn", "server.main:app", "--host", HOST, "--port", str(PORT)]
        if self.reload.get(): args.append("--reload")
        return args

    def start_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            messagebox.showinfo("안내", "이미 실행 중입니다."); return
        cmd = self._uvicorn_cmd(); self._log(f"$ {' '.join(cmd)}")
        try:
            self.server_proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        except FileNotFoundError:
            messagebox.showerror("오류", "uvicorn이 설치되지 않았습니다. [의존성 설치/점검]을 먼저 눌러주세요."); return
        open(PIDFILE, "w").write(str(self.server_proc.pid))
        self.status_lbl.configure(text="Status: RUNNING ✅")
        self.reader_thread = threading.Thread(target=self._read_stdout, daemon=True); self.reader_thread.start()
        self._log("Server starting...")

    def _read_stdout(self):
        assert self.server_proc and self.server_proc.stdout
        for line in self.server_proc.stdout:
            self.log_q.put(line.rstrip("\n"))
        self.log_q.put("** server process ended **")

    def _drain_logs(self):
        try:
            while True: self._log(self.log_q.get_nowait())
        except queue.Empty: pass
        if self.server_proc and self.server_proc.poll() is not None:
            self.status_lbl.configure(text="Status: STOPPED ⏹️")
            try:
                if os.path.exists(PIDFILE): os.remove(PIDFILE)
            except Exception: pass
        self.master.after(150, self._drain_logs)

    def stop_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            self._log("Stopping server...")
            try:
                self.server_proc.terminate()
                try: self.server_proc.wait(timeout=3)
                except subprocess.TimeoutExpired: self.server_proc.kill()
            except Exception as e:
                self._log(f"terminate error: {e}")
            finally:
                self.server_proc = None
                try:
                    if os.path.exists(PIDFILE): os.remove(PIDFILE)
                except Exception: pass
                self.status_lbl.configure(text="Status: STOPPED ⏹️")
        else:
            if os.path.exists(PIDFILE):
                try:
                    pid = int(open(PIDFILE).read().strip())
                    if os.name == "nt": subprocess.call(["taskkill", "/PID", str(pid), "/F"])
                    else: os.kill(pid, signal.SIGTERM)
                    self._log(f"Sent SIGTERM to pid {pid}")
                except Exception as e:
                    self._log(f"pidfile kill failed: {e}")
                finally:
                    try: os.remove(PIDFILE)
                    except Exception: pass
            else:
                messagebox.showinfo("안내", "실행 중인 서버가 없습니다.")

    def open_health(self): webbrowser.open(f"http://{HOST}:{PORT}/health")

    def call_ping(self):
        try:
            body = {"action":"PING","mode":"SINGLE","input":{"echo":"hello"}}
            res = self._api_post("/run?name=modules.common.ping", body)
            self._log(f"[PING] {res}")
            messagebox.showinfo("PING 결과", json.dumps(res, ensure_ascii=False, indent=2))
        except Exception as e:
            self._log(f"[PING] 실패: {e}"); messagebox.showerror("오류", f"PING 실패: {e}")

    def ops_snapshot(self):
        try:
            body = {"action":"SNAPSHOT","mode":"SINGLE","input":{}}
            res = self._api_post("/run?name=modules.ops.snapshot", body)
            self._log(f"[OPS] {res}")
            messagebox.showinfo("Ops Snapshot", json.dumps(res, ensure_ascii=False, indent=2))
        except Exception as e:
            self._log(f"[OPS] 실패: {e}"); messagebox.showerror("오류", f"Ops 실패: {e}")

    # ---------- Transfer UI logic ----------
    def load_accounts(self):
        try:
            body = {"action":"LIST","mode":"SINGLE","input":{}}
            res = self._api_post("/run?name=modules.demo.accounts", body)
            accts = res.get("data",{}).get("accounts",[])
            items = [f'{a.get("id")} | {a.get("acct_no")} ({a.get("alias","")}) — {fmt_money(a.get("balance",0))}' for a in accts]
            self.cmb_from["values"] = items
            if items: self.cmb_from.current(0); self.sel_from_acc.set(accts[0].get("id"))
        except Exception as e:
            self._log(f"[ACCOUNTS] 로드 실패: {e}")

    def load_banks(self):
        try:
            body = {"action":"LIST","mode":"SINGLE","input":{}}
            res = self._api_post("/run?name=modules.demo.banks", body)
            banks = res.get("data",{}).get("banks",[])
            items = [f'{b.get("code")} | {b.get("name")}' for b in banks]
            self.cmb_bank["values"] = items
            if items: self.cmb_bank.current(0)
        except Exception as e:
            self._log(f"[BANKS] 로드 실패: {e}")

    def _parse_from_account_id(self):
        v = self.cmb_from.get()
        # Either id is in sel_from_acc or we parse from string
        if " | " in v:
            return v.split(" | ",1)[0]
        return self.sel_from_acc.get() or v

    def _parse_bank_code(self):
        v = self.cmb_bank.get()
        return v.split(" | ",1)[0] if " | " in v else v

    def query_balance(self):
        try:
            acc_id = self._parse_from_account_id()
            body = {"action":"BALANCE","mode":"SINGLE","input":{"account_id": acc_id}}
            res = self._api_post("/run?name=modules.demo.accounts", body)
            bal = res.get("data",{}).get("balance")
            self.lbl_balance.configure(text=fmt_money(bal))
        except Exception as e:
            self._log(f"[BAL] 실패: {e}")
            messagebox.showerror("오류", f"잔액 조회 실패: {e}")

    def transfer_quote(self):
        try:
            acc_id = self._parse_from_account_id()
            bank_code = self._parse_bank_code()
            body = {
                "action":"QUOTE","mode":"SINGLE",
                "input":{
                    "from_account_id": acc_id,
                    "to_bank_code": bank_code,
                    "to_account_no": self.to_acct.get().strip(),
                    "receiver_name": self.receiver.get().strip(),
                    "amount": int(self.amount.get() or 0),
                    "memo": self.memo.get().strip()
                }
            }
            res = self._api_post("/run?name=modules.demo.transfer", body)
            fee = res.get("data",{}).get("fee",0)
            self._write_tr_out({"수수료": fmt_money(fee)})
        except Exception as e:
            self._write_tr_out({"오류": str(e)})
            messagebox.showerror("오류", f"수수료 조회 실패: {e}")

    def transfer_submit(self):
        try:
            acc_id = self._parse_from_account_id()
            bank_code = self._parse_bank_code()
            payload = {
                "from_account_id": acc_id,
                "to_bank_code": bank_code,
                "to_account_no": self.to_acct.get().strip(),
                "receiver_name": self.receiver.get().strip(),
                "amount": int(self.amount.get() or 0),
                "memo": self.memo.get().strip()
            }
            # VALIDATE
            vres = self._api_post("/run?name=modules.demo.transfer", {"action":"VALIDATE","mode":"SINGLE","input": payload})
            if not vres.get("data",{}).get("valid", False):
                reasons = vres.get("data",{}).get("reasons", [])
                self._write_tr_out({"유효성": False, "사유": reasons})
                messagebox.showwarning("유효성 실패", "\n".join(reasons)); return
            # SUBMIT
            sres = self._api_post("/run?name=modules.demo.transfer", {"action":"SUBMIT","mode":"SINGLE","input": payload})
            if not sres.get("ok", False):
                self._write_tr_out({"오류": sres.get("error")}); messagebox.showerror("오류", str(sres.get("error"))); return
            data = sres.get("data",{})
            self._write_tr_out({
                "TX": data.get("tx_id"),
                "상태": data.get("status"),
                "수수료": fmt_money(data.get("fee",0)),
                "이체금액": fmt_money(data.get("amount",0)),
                "새 잔액": fmt_money(data.get("new_balance")) if data.get("new_balance") is not None else "—"
            })
            # 잔액 라벨 즉시 갱신
            self.query_balance()
        except Exception as e:
            self._write_tr_out({"오류": str(e)})
            messagebox.showerror("오류", f"이체 실패: {e}")

    def _write_tr_out(self, obj):
        self.tr_out.configure(state="normal")
        self.tr_out.delete("1.0","end")
        self.tr_out.insert("end", json.dumps(obj, ensure_ascii=False, indent=2))
        self.tr_out.configure(state="disabled")

    def demo_init(self):
        try:
            res = self._api_post("/run?name=modules.demo.accounts", {"action":"INIT","mode":"SINGLE","input":{}})
            if res.get("ok"):
                self._log("[DEMO] 계좌 상태 초기화 완료")
                self.load_accounts(); self.lbl_balance.configure(text="—")
                messagebox.showinfo("완료", "데모 데이터 초기화 완료")
            else:
                raise RuntimeError(res.get("error"))
        except Exception as e:
            self._log(f"[DEMO] 실패: {e}")
            messagebox.showerror("오류", f"데모 초기화 실패: {e}")

    # ---------- Boilerplate ----------
    def install_module_zip(self):
        path = filedialog.askopenfilename(title="모듈 zip 선택", filetypes=[("Zip files","*.zip")])
        if not path: return
        target_root = os.path.join(ROOT, "modules")
        os.makedirs(target_root, exist_ok=True)
        try:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(target_root)
            self._log(f"모듈 설치 완료: {path}")
            if messagebox.askyesno("확인", "설치 완료. 서버를 재시작할까요?"):
                self.stop_server(); time.sleep(0.5); self.start_server()
        except Exception as e:
            self._log(f"모듈 설치 실패: {e}")
            messagebox.showerror("오류", f"모듈 설치 실패: {e}")

    def open_health(self): webbrowser.open(f"http://{HOST}:{PORT}/health")

    def _read_stdout(self):
        assert self.server_proc and self.server_proc.stdout
        for line in self.server_proc.stdout:
            self.log_q.put(line.rstrip("\n"))
        self.log_q.put("** server process ended **")

    def _drain_logs(self):
        try:
            while True: self._log(self.log_q.get_nowait())
        except queue.Empty: pass
        if self.server_proc and self.server_proc.poll() is not None:
            self.status_lbl.configure(text="Status: STOPPED ⏹️")
            try:
                if os.path.exists(PIDFILE): os.remove(PIDFILE)
            except Exception: pass
        self.master.after(150, self._drain_logs)

    def _uvicorn_cmd(self):
        args = [sys.executable, "-m", "uvicorn", "server.main:app", "--host", HOST, "--port", str(PORT)]
        if self.reload.get(): args.append("--reload")
        return args

    def start_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            messagebox.showinfo("안내", "이미 실행 중입니다."); return
        cmd = self._uvicorn_cmd(); self._log(f"$ {' '.join(cmd)}")
        try:
            self.server_proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        except FileNotFoundError:
            messagebox.showerror("오류", "uvicorn이 설치되지 않았습니다. [의존성 설치/점검]을 먼저 눌러주세요."); return
        open(PIDFILE, "w").write(str(self.server_proc.pid))
        self.status_lbl.configure(text="Status: RUNNING ✅")
        self.reader_thread = threading.Thread(target=self._read_stdout, daemon=True); self.reader_thread.start()
        self._log("Server starting...")

    def stop_server(self):
        if self.server_proc and self.server_proc.poll() is None:
            self._log("Stopping server...")
            try:
                self.server_proc.terminate()
                try: self.server_proc.wait(timeout=3)
                except subprocess.TimeoutExpired: self.server_proc.kill()
            except Exception as e:
                self._log(f"terminate error: {e}")
            finally:
                self.server_proc = None
                try:
                    if os.path.exists(PIDFILE): os.remove(PIDFILE)
                except Exception: pass
                self.status_lbl.configure(text="Status: STOPPED ⏹️")
        else:
            if os.path.exists(PIDFILE):
                try:
                    pid = int(open(PIDFILE).read().strip())
                    if os.name == "nt": subprocess.call(["taskkill", "/PID", str(pid), "/F"])
                    else: os.kill(pid, signal.SIGTERM)
                    self._log(f"Sent SIGTERM to pid {pid}")
                except Exception as e:
                    self._log(f"pidfile kill failed: {e}")
                finally:
                    try: os.remove(PIDFILE)
                    except Exception: pass
            else:
                messagebox.showinfo("안내", "실행 중인 서버가 없습니다.")

if __name__ == "__main__":
    root = tk.Tk(); app = LauncherApp(root); root.mainloop()
