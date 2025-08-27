import os
import threading
import time
import subprocess
import uvicorn


if not os.path.exists("core/.chroma_store"):
    print("[INFO] Running initial ingest...")
    subprocess.run(["python", "-m", "core.ingest"], check=True)


def run_backend():
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=False)

backend_thread = threading.Thread(target=run_backend, daemon=True)
backend_thread.start()


import requests
def wait_for_backend():
    for _ in range(20):
        try:
            r = requests.get("http://127.0.0.1:8000/ping", timeout=2)
            if r.status_code == 200:
                print("[INFO] Backend ready.")
                return
        except:
            pass
        print("[INFO] Waiting for backend to start...")
        time.sleep(1)
    print("[ERROR] Backend did not start.")
    exit(1)

wait_for_backend()


print("[INFO] Launching frontend (Flask)...")
os.chdir("frontend")
os.environ["FLASK_APP"] = "app.py"
os.environ["FLASK_RUN_PORT"] = "5000"
subprocess.run(["flask", "run"])
