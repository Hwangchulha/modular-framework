# Dev Launcher (GUI First)
import streamlit as st
import subprocess, os, signal, time, pathlib, psutil, sys, webbrowser

PIDFILE = pathlib.Path('.server.pid')
UVICORN_CMD = [sys.executable, '-m', 'uvicorn', 'server.main:app', '--reload']

def is_running():
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            return psutil.pid_exists(pid)
        except Exception:
            return False
    return False

def start_server():
    if is_running():
        return
    p = subprocess.Popen(UVICORN_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    PIDFILE.write_text(str(p.pid))

def stop_server():
    if not PIDFILE.exists():
        return
    try:
        pid = int(PIDFILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
    except Exception:
        pass
    finally:
        try:
            PIDFILE.unlink()
        except Exception:
            pass

st.set_page_config(page_title='Dev Launcher', page_icon='🚀', layout='centered')
st.title('Modular Framework — Dev Launcher')

col1, col2, col3 = st.columns(3)
with col1:
    if st.button('Run server', disabled=is_running()):
        start_server()
        time.sleep(0.8)
with col2:
    if st.button('Stop server', disabled=not is_running()):
        stop_server()
with col3:
    if st.button('Open /health'):
        webbrowser.open('http://localhost:8000/health')

st.write('Status:', 'RUNNING ✅' if is_running() else 'STOPPED ⏹️')
st.caption('서버는 UI와 분리되어 동작합니다. 서버가 UI를 서빙하지 않습니다.')
