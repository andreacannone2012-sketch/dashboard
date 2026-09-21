#!/usr/bin/env python3
"""Dashboard NAS: un solo container che serve la pagina e le statistiche.

Endpoint:
  /                 pagina index.html
  /services.json    elenco servizi (da /config se presente, altrimenti quello incluso)
  /api/stats        JSON con CPU, RAM, dischi, temperatura, uptime
  /api/health       controllo di salute

Variabili d'ambiente:
  PORT        porta di ascolto (default 8080)
  CONFIG_DIR  cartella modificabile con services.json (default /config)
  DISKS       elenco "Nome=percorso" separato da virgole
"""

import json
import os
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8080"))
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DISKS_SPEC = os.environ.get("DISKS", "Sistema=/host/root,Storage=/host/storage")

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8", "no-cache"),
    "/index.html": ("index.html", "text/html; charset=utf-8", "no-cache"),
}


def parse_disks(spec):
    disks = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, path = part.partition("=")
        name, path = name.strip(), path.strip()
        if name and path:
            disks.append((name, path))
    return disks


DISKS = parse_disks(DISKS_SPEC)
state = {"cpu": 0.0}


def prepare_config():
    """Al primo avvio copia services.json di esempio nella cartella di configurazione."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        target = os.path.join(CONFIG_DIR, "services.json")
        if not os.path.exists(target):
            shutil.copyfile(os.path.join(APP_DIR, "services.json"), target)
    except Exception as exc:  # noqa: BLE001
        print(f"config non scrivibile, uso il file incluso: {exc}", flush=True)


def services_path():
    custom = os.path.join(CONFIG_DIR, "services.json")
    return custom if os.path.isfile(custom) else os.path.join(APP_DIR, "services.json")


def read_cpu_times():
    with open("/proc/stat") as f:
        fields = f.readline().split()[1:]
    values = [int(x) for x in fields]
    idle = values[3] + (values[4] if len(values) > 4 else 0)  # idle + iowait
    total = sum(values[:8])  # user..steal (guest già incluso in user)
    return idle, total


def cpu_sampler():
    prev_idle, prev_total = read_cpu_times()
    while True:
        time.sleep(2)
        try:
            idle, total = read_cpu_times()
        except Exception:
            continue
        d_total = total - prev_total
        d_idle = idle - prev_idle
        if d_total > 0:
            state["cpu"] = round(max(0.0, min(100.0, 100.0 * (1 - d_idle / d_total))), 1)
        prev_idle, prev_total = idle, total


def read_memory():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, _, rest = line.partition(":")
            info[key] = int(rest.split()[0]) * 1024
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0))
    used = max(0, total - available)
    percent = round(100.0 * used / total, 1) if total else 0.0
    return {"total": total, "used": used, "percent": percent}


def read_disks():
    result = []
    for name, path in DISKS:
        try:
            st = os.statvfs(path)
            used = (st.f_blocks - st.f_bfree) * st.f_frsize
            total = used + st.f_bavail * st.f_frsize  # stesso criterio di `df`
            percent = round(100.0 * used / total, 1) if total else 0.0
            result.append({"name": name, "total": total, "used": used, "percent": percent})
        except Exception:
            result.append({"name": name, "error": True})
    return result


def read_temperature():
    base = "/sys/class/thermal"
    try:
        temps = []
        for zone in os.listdir(base):
            if not zone.startswith("thermal_zone"):
                continue
            try:
                with open(os.path.join(base, zone, "temp")) as f:
                    temps.append(int(f.read().strip()) / 1000.0)
            except Exception:
                continue
        return round(max(temps), 1) if temps else None
    except Exception:
        return None


def read_uptime():
    with open("/proc/uptime") as f:
        return int(float(f.read().split()[0]))


def read_load():
    try:
        with open("/proc/loadavg") as f:
            return [float(x) for x in f.read().split()[:3]]
    except Exception:
        return None


def collect():
    return {
        "cpu": {"percent": state["cpu"], "temp": read_temperature(), "load": read_load()},
        "memory": read_memory(),
        "disks": read_disks(),
        "uptime": read_uptime(),
        "time": int(time.time()),
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype, cache):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, obj):
        self._send(status, json.dumps(obj).encode("utf-8"),
                   "application/json; charset=utf-8", "no-store")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/stats":
            try:
                self._json(200, collect())
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"error": str(exc)})
        elif path in ("/health", "/api/health"):
            self._json(200, {"ok": True})
        elif path == "/services.json":
            try:
                with open(services_path(), "rb") as f:
                    self._send(200, f.read(), "application/json; charset=utf-8", "no-store")
            except Exception:
                self._json(404, {"error": "services.json non trovato"})
        elif path in STATIC:
            name, ctype, cache = STATIC[path]
            try:
                with open(os.path.join(APP_DIR, name), "rb") as f:
                    self._send(200, f.read(), ctype, cache)
            except Exception:
                self._json(404, {"error": "not found"})
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):  # niente log per ogni richiesta
        pass


def main():
    prepare_config()
    threading.Thread(target=cpu_sampler, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"dashboard in ascolto sulla porta {PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
