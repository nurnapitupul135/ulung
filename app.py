#!/usr/bin/env python3
"""Minimal HTTP service for checking NVIDIA GPU availability on Vita Serverless."""
import json
import os
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone

PORT = int(os.environ.get("PORT", "8000"))

def gpu_info():
    smi = shutil.which("nvidia-smi")
    if not smi:
        return {
            "ok": False,
            "error": "nvidia-smi was not found in the container. Check that Vita Serverless attaches NVIDIA driver utilities and GPU access."
        }, 503

    commands = [
        [smi],
        [smi, "-L"],
        [smi, "--query-gpu=name,driver_version,memory.total,memory.free,utilization.gpu",
         "--format=csv,noheader"]
    ]
    results = []
    for cmd in commands:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            results.append({
                "command": " ".join(cmd),
                "returncode": p.returncode,
                "stdout": p.stdout.strip(),
                "stderr": p.stderr.strip()
            })
        except subprocess.TimeoutExpired:
            results.append({"command": " ".join(cmd), "error": "Timed out after 25 seconds"})
        except Exception as exc:
            results.append({"command": " ".join(cmd), "error": str(exc)})

    ok = any(x.get("returncode") == 0 for x in results)
    return {
        "ok": ok,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "gpu": results
    }, (200 if ok else 503)

class Handler(BaseHTTPRequestHandler):
    def respond(self, payload, status=200):
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            if self.path == "/health":
                self.respond({"status": "ok", "service": "vita-nvidia-smi"})
            elif self.path == "/healthz":
                self.respond({"status": "ok"})
            else:
                payload, status = gpu_info()
                self.respond(payload, status)
        elif self.path == "/gpu":
            payload, status = gpu_info()
            self.respond(payload, status)
        else:
            self.respond({
                "service": "vita-nvidia-smi",
                "endpoints": ["/", "/gpu", "/health", "/healthz"]
            }, 404)

    def log_message(self, fmt, *args):
        print("[http] " + (fmt % args), flush=True)

if __name__ == "__main__":
    print("===== VITA NVIDIA-SMI SERVICE STARTING =====", flush=True)
    print("Listening on 0.0.0.0:%s" % PORT, flush=True)
    smi = shutil.which("nvidia-smi")
    print("nvidia-smi path: %s" % (smi or "NOT FOUND"), flush=True)
    if smi:
        try:
            p = subprocess.run([smi], capture_output=True, text=True, timeout=25)
            print("===== NVIDIA-SMI STARTUP OUTPUT =====", flush=True)
            print(p.stdout or p.stderr or "(no output)", flush=True)
            print("nvidia-smi exit code: %s" % p.returncode, flush=True)
        except Exception as exc:
            print("nvidia-smi startup error: %s" % exc, flush=True)
    else:
        print("nvidia-smi unavailable at startup; GPU details will show in /gpu response.", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
