import asyncio
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from config_loader import DEFAULT_CONFIG, deep_merge


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("PUBG_AFK_DATA_DIR", str(ROOT_DIR / "data"))).resolve()
DEVICES_FILE = DATA_DIR / "devices.yaml"
RUNTIME_DIR = DATA_DIR / "runtime"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", (text or "").strip()).strip("-").lower()
    return slug or f"device-{int(time.time())}"


class DeviceUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=64)
    target_password: str = Field(min_length=1, max_length=128)
    display: str = Field(default=":99", max_length=32)
    override_config_yaml: str = Field(default="", max_length=20000)
    note: str = Field(default="", max_length=2000)


class Device(DeviceUpsert):
    key: str


class StartRequest(BaseModel):
    hours: int = Field(ge=0, le=999, default=6)
    minutes: int = Field(ge=0, le=59, default=5)


class DeviceStatus(BaseModel):
    key: str
    status: str
    pid: int | None
    started_at: float | None
    expected_end_at: float | None
    exit_code: int | None
    last_error: str | None


@dataclass
class RuntimeState:
    process: subprocess.Popen | None = None
    started_at: float | None = None
    expected_end_at: float | None = None
    exit_code: int | None = None
    last_error: str | None = None

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.process else None

    def status(self) -> str:
        if self.process is None:
            return "stopped"
        rc = self.process.poll()
        if rc is None:
            return "running"
        self.exit_code = rc
        return "exited" if rc == 0 else "error"


ensure_dirs()

app = FastAPI(title="PUBG Anti-AFK WebUI")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_runtime: dict[str, RuntimeState] = {}


def load_devices() -> dict[str, Device]:
    if not DEVICES_FILE.exists():
        return {}
    raw = DEVICES_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, Device] = {}
    items = data.get("devices", [])
    if not isinstance(items, list):
        return {}
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            d = Device(**it)
            out[d.key] = d
        except Exception:
            continue
    return out


def save_devices(devices: dict[str, Device]) -> None:
    payload = {"devices": [devices[k].model_dump() for k in sorted(devices.keys())]}
    DEVICES_FILE.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def get_device_or_404(key: str) -> Device:
    devices = load_devices()
    if key not in devices:
        raise HTTPException(status_code=404, detail="device not found")
    return devices[key]


def runtime_for(key: str) -> RuntimeState:
    st = _runtime.get(key)
    if st is None:
        st = RuntimeState()
        _runtime[key] = st
    return st


def parse_override_yaml(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    if not t:
        return {}
    loaded = yaml.safe_load(t)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("override_config_yaml must be a YAML mapping")
    return loaded


def effective_config_for(device: Device, duration_seconds: int) -> dict[str, Any]:
    base = DEFAULT_CONFIG
    override = parse_override_yaml(device.override_config_yaml)
    run_override = {"run": {"auto_exit_after_seconds": int(duration_seconds)}}
    return deep_merge(deep_merge(base, override), run_override)


def device_paths(key: str) -> dict[str, Path]:
    base = RUNTIME_DIR / key
    return {
        "base": base,
        "config": base / "effective_config.yaml",
        "screenshots": base / "screenshots",
        "logs": base / "logs",
        "log_file": base / "logs" / "run.log",
    }


def list_screenshots(key: str) -> list[dict[str, Any]]:
    paths = device_paths(key)
    d = paths["screenshots"]
    if not d.exists():
        return []
    items = []
    for p in sorted(d.glob("*.png"), reverse=True):
        items.append({"name": p.name, "ts": p.stat().st_mtime})
    return items[:10]


async def _watch_process(key: str) -> None:
    st = runtime_for(key)
    proc = st.process
    if proc is None:
        return
    while True:
        rc = proc.poll()
        if rc is not None:
            st.exit_code = rc
            st.process = None
            return
        await asyncio.sleep(1)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    devices = load_devices()
    rows = []
    now = time.time()
    for key, dev in sorted(devices.items(), key=lambda x: x[1].name.lower()):
        st = runtime_for(key)
        status = st.status()
        remaining = None
        if status == "running" and st.expected_end_at:
            remaining = max(0, int(st.expected_end_at - now))
        rows.append(
            {
                "device": dev,
                "status": status,
                "pid": st.pid,
                "remaining": remaining,
                "expected_end_at": st.expected_end_at,
            }
        )
    return templates.TemplateResponse("index.html", {"request": request, "rows": rows})


@app.get("/devices/{key}", response_class=HTMLResponse)
def device_detail(key: str, request: Request):
    dev = get_device_or_404(key)
    st = runtime_for(key)
    shots = list_screenshots(key)
    return templates.TemplateResponse(
        "device.html",
        {
            "request": request,
            "device": dev,
            "status": st.status(),
            "pid": st.pid,
            "started_at": st.started_at,
            "expected_end_at": st.expected_end_at,
            "exit_code": st.exit_code,
            "last_error": st.last_error,
            "screenshots": shots,
        },
    )


@app.get("/devices/{key}/edit", response_class=HTMLResponse)
def device_edit(key: str, request: Request):
    dev = get_device_or_404(key)
    return templates.TemplateResponse("edit.html", {"request": request, "device": dev})


@app.get("/devices/new", response_class=HTMLResponse)
def device_new(request: Request):
    blank = Device(
        key="",
        name="",
        target_id="",
        target_password="",
        display=":99",
        override_config_yaml="",
        note="",
    )
    return templates.TemplateResponse("edit.html", {"request": request, "device": blank})


@app.get("/api/devices")
def api_list_devices():
    devices = load_devices()
    now = time.time()
    out = []
    for key, dev in devices.items():
        st = runtime_for(key)
        status = st.status()
        remaining = None
        if status == "running" and st.expected_end_at:
            remaining = max(0, int(st.expected_end_at - now))
        out.append(
            {
                **dev.model_dump(exclude={"target_password"}),
                "status": status,
                "pid": st.pid,
                "remaining_seconds": remaining,
                "expected_end_at": st.expected_end_at,
            }
        )
    return {"devices": out}


@app.post("/api/devices")
def api_create_device(req: DeviceUpsert):
    devices = load_devices()
    key_base = safe_slug(req.name)
    key = key_base
    n = 1
    while key in devices:
        n += 1
        key = f"{key_base}-{n}"
    dev = Device(key=key, **req.model_dump())
    devices[key] = dev
    save_devices(devices)
    return {"device": dev.model_dump(exclude={"target_password"})}


@app.put("/api/devices/{key}")
def api_update_device(key: str, req: DeviceUpsert):
    devices = load_devices()
    if key not in devices:
        raise HTTPException(status_code=404, detail="device not found")
    dev = Device(key=key, **req.model_dump())
    devices[key] = dev
    save_devices(devices)
    return {"device": dev.model_dump(exclude={"target_password"})}


@app.delete("/api/devices/{key}")
def api_delete_device(key: str):
    devices = load_devices()
    if key not in devices:
        raise HTTPException(status_code=404, detail="device not found")
    st = runtime_for(key)
    if st.status() == "running":
        raise HTTPException(status_code=409, detail="device is running")
    devices.pop(key, None)
    save_devices(devices)
    return {"ok": True}


@app.get("/api/devices/{key}/status", response_model=DeviceStatus)
def api_device_status(key: str):
    get_device_or_404(key)
    st = runtime_for(key)
    return DeviceStatus(
        key=key,
        status=st.status(),
        pid=st.pid,
        started_at=st.started_at,
        expected_end_at=st.expected_end_at,
        exit_code=st.exit_code,
        last_error=st.last_error,
    )


@app.post("/api/devices/{key}/start", response_model=DeviceStatus)
def api_device_start(key: str, req: StartRequest):
    dev = get_device_or_404(key)
    st = runtime_for(key)
    if st.status() == "running":
        raise HTTPException(status_code=409, detail="already running")

    duration_seconds = int(req.hours) * 3600 + int(req.minutes) * 60
    if duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="duration must be > 0")

    paths = device_paths(key)
    paths["screenshots"].mkdir(parents=True, exist_ok=True)
    paths["logs"].mkdir(parents=True, exist_ok=True)
    paths["base"].mkdir(parents=True, exist_ok=True)

    try:
        cfg = effective_config_for(dev, duration_seconds)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    paths["config"].write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    env = os.environ.copy()
    env["PUBG_AFK_CONFIG"] = str(paths["config"])
    env["PUBG_AFK_SCREENSHOT_DIR"] = str(paths["screenshots"])
    env["PUBG_AFK_DEVICE_KEY"] = key

    cmd = [
        "python3",
        str(ROOT_DIR / "rustdesk_pubg_afk.py"),
        "--display",
        dev.display,
        "--target-id",
        dev.target_id,
        "--target-password",
        dev.target_password,
    ]

    log_fp = open(paths["log_file"], "ab", buffering=0)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT_DIR),
            env=env,
            stdout=log_fp,
            stderr=log_fp,
            start_new_session=True,
        )
    except Exception as e:
        log_fp.close()
        raise HTTPException(status_code=500, detail=f"failed to start: {e}")

    st.process = proc
    st.started_at = time.time()
    st.expected_end_at = st.started_at + duration_seconds
    st.exit_code = None
    st.last_error = None
    asyncio.create_task(_watch_process(key))

    return DeviceStatus(
        key=key,
        status=st.status(),
        pid=st.pid,
        started_at=st.started_at,
        expected_end_at=st.expected_end_at,
        exit_code=st.exit_code,
        last_error=st.last_error,
    )


@app.post("/api/devices/{key}/stop", response_model=DeviceStatus)
def api_device_stop(key: str):
    get_device_or_404(key)
    st = runtime_for(key)
    if st.process is None:
        return DeviceStatus(
            key=key,
            status=st.status(),
            pid=None,
            started_at=st.started_at,
            expected_end_at=st.expected_end_at,
            exit_code=st.exit_code,
            last_error=st.last_error,
        )

    proc = st.process
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass

    deadline = time.time() + 5
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.2)

    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    st.exit_code = proc.poll()
    st.process = None

    return DeviceStatus(
        key=key,
        status=st.status(),
        pid=None,
        started_at=st.started_at,
        expected_end_at=st.expected_end_at,
        exit_code=st.exit_code,
        last_error=st.last_error,
    )


@app.get("/api/devices/{key}/screenshots")
def api_device_screenshots(key: str):
    get_device_or_404(key)
    return {"screenshots": list_screenshots(key)}


@app.get("/screenshots/{key}/{name}")
def screenshot_file(key: str, name: str):
    get_device_or_404(key)
    p = device_paths(key)["screenshots"] / name
    if not p.exists():
        raise HTTPException(status_code=404, detail="not found")
    return Response(p.read_bytes(), media_type="image/png")
