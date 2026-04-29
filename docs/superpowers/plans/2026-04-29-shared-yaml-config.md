# Shared YAML Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `rustdesk_pubg_afk.py` and `uu_pubg_afk.py` load all timing/random/action defaults from a single shared `config.yaml`, and auto-exit after 6h5m.

**Architecture:** Add a shared `config_loader.py` that loads `config.yaml` (or `PUBG_AFK_CONFIG`) via `PyYAML`, merges with built-in defaults, and exposes a simple dict. Both scripts consume config values instead of hard-coded constants.

**Tech Stack:** Python, PyYAML, existing input backends (`xdotool` on Linux, `pydirectinput` on Windows).

---

## File Map

**Create**
- `/workspace/config.yaml`
- `/workspace/config_loader.py`
- `/workspace/requirements_rustdesk.txt`
- `/workspace/docs/superpowers/plans/2026-04-29-shared-yaml-config.md` (this file)

**Modify**
- `/workspace/requirements.txt`
- `/workspace/rustdesk_pubg_afk.py`
- `/workspace/uu_pubg_afk.py`
- `/workspace/README.md` (optional but recommended: document config usage)

---

### Task 1: Add Shared YAML Dependencies

**Files:**
- Modify: [requirements.txt](file:///workspace/requirements.txt)
- Modify/Create: [requirements_rustdesk.txt](file:///workspace/requirements_rustdesk.txt)

- [ ] **Step 1: Update Windows requirements**

Edit `requirements.txt` to include `PyYAML` (keep existing packages):

```txt
pygetwindow
pydirectinput
PyYAML
```

- [ ] **Step 2: Update Linux requirements**

Replace the empty `requirements_rustdesk.txt` with:

```txt
PyYAML
```

- [ ] **Step 3: Sanity check**

Run (Linux sandbox):

```bash
python3 -c "import yaml; print('ok')"
```

Expected: prints `ok` after dependencies are installed (this step is typically run after Task 2 Step 3).

- [ ] **Step 4: Commit**

```bash
git add requirements.txt requirements_rustdesk.txt
git commit -m "chore: add PyYAML for shared config"
```

---

### Task 2: Create Shared `config.yaml`

**Files:**
- Create: `/workspace/config.yaml`

- [ ] **Step 1: Add `config.yaml`**

Create `config.yaml` with no comments:

```yaml
run:
  auto_exit_after_seconds: 21900

loop:
  interval_seconds:
    min: 280
    max: 320
  window_init_wait_seconds: 15

movement:
  mouse:
    offset_x:
      min: -60
      max: 60
    offset_y:
      min: -20
      max: 20
    move_duration_seconds: 0.1
    right_click:
      hold_seconds: 0.1
      double_click_interval_seconds:
        min: 2
        max: 4

  keyboard:
    wasd_keys: ["w", "s", "a", "d"]
    hold_seconds:
      min: 0.1
      max: 0.18
    opp_sleep_seconds: 0.05

    qe_keys: ["q", "e"]
    qe_times:
      min: 2
      max: 5
    qe_hold_seconds:
      min: 0.03
      max: 0.07
    qe_interval_seconds:
      min: 0.05
      max: 0.15

rustdesk:
  connection:
    connect_timeout_seconds: 30
    connect_retries: 3
```

- [ ] **Step 2: Commit**

```bash
git add config.yaml
git commit -m "feat: add shared config.yaml defaults"
```

---

### Task 3: Implement `config_loader.py`

**Files:**
- Create: `/workspace/config_loader.py`

- [ ] **Step 1: Add loader module**

Create `config_loader.py`:

```python
import os

try:
    import yaml
except Exception as e:
    yaml = None
    _yaml_import_error = e


DEFAULT_CONFIG = {
    "run": {
        "auto_exit_after_seconds": 21900,
    },
    "loop": {
        "interval_seconds": {"min": 280, "max": 320},
        "window_init_wait_seconds": 15,
    },
    "movement": {
        "mouse": {
            "offset_x": {"min": -60, "max": 60},
            "offset_y": {"min": -20, "max": 20},
            "move_duration_seconds": 0.1,
            "right_click": {
                "hold_seconds": 0.1,
                "double_click_interval_seconds": {"min": 2, "max": 4},
            },
        },
        "keyboard": {
            "wasd_keys": ["w", "s", "a", "d"],
            "hold_seconds": {"min": 0.1, "max": 0.18},
            "opp_sleep_seconds": 0.05,
            "qe_keys": ["q", "e"],
            "qe_times": {"min": 2, "max": 5},
            "qe_hold_seconds": {"min": 0.03, "max": 0.07},
            "qe_interval_seconds": {"min": 0.05, "max": 0.15},
        },
    },
    "rustdesk": {
        "connection": {"connect_timeout_seconds": 30, "connect_retries": 3},
    },
}


def deep_merge(base, overlay):
    if not isinstance(base, dict) or not isinstance(overlay, dict):
        return overlay
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(default_path=None):
    path = os.environ.get("PUBG_AFK_CONFIG") or default_path or os.path.join(
        os.path.dirname(__file__),
        "config.yaml",
    )

    if yaml is None:
        return DEFAULT_CONFIG, f"PyYAML import failed: {_yaml_import_error}"

    if not os.path.isfile(path):
        return DEFAULT_CONFIG, f"config not found: {path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            return DEFAULT_CONFIG, f"invalid config type: {type(loaded).__name__}"
        return deep_merge(DEFAULT_CONFIG, loaded), None
    except Exception as e:
        return DEFAULT_CONFIG, f"failed to read config: {e}"
```

- [ ] **Step 2: Quick import test**

```bash
python3 -c "from config_loader import load_config; cfg, err = load_config(); print(bool(cfg), err is None or isinstance(err, str))"
```

Expected: prints `True True`.

- [ ] **Step 3: Commit**

```bash
git add config_loader.py
git commit -m "feat: add shared YAML config loader"
```

---

### Task 4: Wire Config Into `rustdesk_pubg_afk.py`

**Files:**
- Modify: [rustdesk_pubg_afk.py](file:///workspace/rustdesk_pubg_afk.py)

- [ ] **Step 1: Load config once at startup**

Add near the top (after stdlib imports are fine):

```python
from config_loader import load_config

config, config_error = load_config()
if config_error:
    print(f"[config] {config_error}, using built-in defaults")
```

- [ ] **Step 2: Replace hard-coded timing constants**

Remove:
- `CONNECT_TIMEOUT_SECONDS = 30`
- `CONNECT_RETRIES = 3`

And replace usages with:

```python
CONNECT_TIMEOUT_SECONDS = int(config["rustdesk"]["connection"]["connect_timeout_seconds"])
CONNECT_RETRIES = int(config["rustdesk"]["connection"]["connect_retries"])
```

- [ ] **Step 3: Apply window init delay and loop interval from config**

Replace `time.sleep(15)` with:

```python
time.sleep(float(config["loop"]["window_init_wait_seconds"]))
```

Replace:

```python
wait_time = random.randint(280, 320)
```

with:

```python
wait_time = random.randint(
    int(config["loop"]["interval_seconds"]["min"]),
    int(config["loop"]["interval_seconds"]["max"]),
)
```

- [ ] **Step 4: Update `safety_movement()` to use config**

Replace all hard-coded ranges with config-driven ones:

```python
dx = random.randint(int(config["movement"]["mouse"]["offset_x"]["min"]), int(config["movement"]["mouse"]["offset_x"]["max"]))
dy = random.randint(int(config["movement"]["mouse"]["offset_y"]["min"]), int(config["movement"]["mouse"]["offset_y"]["max"]))

move_duration = float(config["movement"]["mouse"]["move_duration_seconds"])

xdotool_mouse_down(3)
time.sleep(float(config["movement"]["mouse"]["right_click"]["hold_seconds"]))
xdotool_mouse_up(3)

xdotool_mouse_click(3)
time.sleep(random.uniform(
    float(config["movement"]["mouse"]["right_click"]["double_click_interval_seconds"]["min"]),
    float(config["movement"]["mouse"]["right_click"]["double_click_interval_seconds"]["max"]),
))
xdotool_mouse_click(3)

keys = list(config["movement"]["keyboard"]["wasd_keys"])
k = random.choice(keys)
hold_time = random.uniform(
    float(config["movement"]["keyboard"]["hold_seconds"]["min"]),
    float(config["movement"]["keyboard"]["hold_seconds"]["max"]),
)

opp_sleep = float(config["movement"]["keyboard"]["opp_sleep_seconds"])
time.sleep(opp_sleep)

extra_times = random.randint(
    int(config["movement"]["keyboard"]["qe_times"]["min"]),
    int(config["movement"]["keyboard"]["qe_times"]["max"]),
)
qe_keys = list(config["movement"]["keyboard"]["qe_keys"])
qe_hold_min = float(config["movement"]["keyboard"]["qe_hold_seconds"]["min"])
qe_hold_max = float(config["movement"]["keyboard"]["qe_hold_seconds"]["max"])
qe_gap_min = float(config["movement"]["keyboard"]["qe_interval_seconds"]["min"])
qe_gap_max = float(config["movement"]["keyboard"]["qe_interval_seconds"]["max"])
```

Then use the above variables in the existing key/mouse logic.

- [ ] **Step 5: Add auto-exit timer**

In `main()` record:

```python
start_ts = time.time()
auto_exit_after = float(config["run"]["auto_exit_after_seconds"])
```

At the top of each `while True` iteration:

```python
if auto_exit_after > 0 and (time.time() - start_ts) >= auto_exit_after:
    print(f"[{time.strftime('%H:%M:%S')}] Auto exit after {int(auto_exit_after)} seconds.")
    break
```

Ensure the `finally:` that disconnects RustDesk still runs when breaking. One safe pattern:
- Use `should_exit = False` flag
- Set `should_exit = True` then `break` after the `finally` block completes, or restructure to check exit condition right after the `finally`.

- [ ] **Step 6: Syntax check**

```bash
python3 -m py_compile /workspace/rustdesk_pubg_afk.py
```

Expected: exit code 0.

- [ ] **Step 7: Commit**

```bash
git add rustdesk_pubg_afk.py
git commit -m "feat(rustdesk): load shared YAML config for timings and actions"
```

---

### Task 5: Wire Config Into `uu_pubg_afk.py` (and add right-click actions)

**Files:**
- Modify: [uu_pubg_afk.py](file:///workspace/uu_pubg_afk.py)

- [ ] **Step 1: Load config once at startup**

Add near top:

```python
from config_loader import load_config

config, config_error = load_config()
if config_error:
    print(f"[config] {config_error}, using built-in defaults")
```

- [ ] **Step 2: Replace loop interval with config**

Replace:

```python
wait_time = random.randint(120, 180)
```

with:

```python
wait_time = random.randint(
    int(config["loop"]["interval_seconds"]["min"]),
    int(config["loop"]["interval_seconds"]["max"]),
)
```

- [ ] **Step 3: Apply window init delay before action**

Right after window is successfully focused, add:

```python
time.sleep(float(config["loop"]["window_init_wait_seconds"]))
```

- [ ] **Step 4: Update `safety_movement()` to use config and add right-click sequence**

Use config values for:
- `dx/dy` ranges
- `moveTo(..., duration=...)`
- WASD hold range and opposite sleep
- Q/E extra presses ranges and delays
- Add right-click hold + double-right-click (same as Linux behavior)

Concrete snippet to embed inside `safety_movement()`:

```python
dx = random.randint(int(config["movement"]["mouse"]["offset_x"]["min"]), int(config["movement"]["mouse"]["offset_x"]["max"]))
dy = random.randint(int(config["movement"]["mouse"]["offset_y"]["min"]), int(config["movement"]["mouse"]["offset_y"]["max"]))
center_x = win.left + win.width // 2
center_y = win.top + win.height // 2

pydirectinput.moveTo(
    center_x + dx,
    center_y + dy,
    duration=float(config["movement"]["mouse"]["move_duration_seconds"]),
)

pydirectinput.mouseDown(button="right")
time.sleep(float(config["movement"]["mouse"]["right_click"]["hold_seconds"]))
pydirectinput.mouseUp(button="right")

pydirectinput.click(button="right")
time.sleep(random.uniform(
    float(config["movement"]["mouse"]["right_click"]["double_click_interval_seconds"]["min"]),
    float(config["movement"]["mouse"]["right_click"]["double_click_interval_seconds"]["max"]),
))
pydirectinput.click(button="right")
```

- [ ] **Step 5: Add auto-exit timer**

In `main()` before `while True`:

```python
start_ts = time.time()
auto_exit_after = float(config["run"]["auto_exit_after_seconds"])
```

At the top of each iteration (before searching for windows):

```python
if auto_exit_after > 0 and (time.time() - start_ts) >= auto_exit_after:
    print(f"[{time.strftime('%H:%M:%S')}] Auto exit after {int(auto_exit_after)} seconds.")
    break
```

This preserves existing `finally` behavior per-iteration.

- [ ] **Step 6: Syntax check**

```bash
python3 -m py_compile /workspace/uu_pubg_afk.py
```

Expected: exit code 0.

- [ ] **Step 7: Commit**

```bash
git add uu_pubg_afk.py
git commit -m "feat(uu): load shared YAML config and align mouse actions"
```

---

### Task 6: Update Documentation

**Files:**
- Modify: [README.md](file:///workspace/README.md)

- [ ] **Step 1: Document config usage**

Add a short section (no screenshots) describing:
- default `config.yaml`
- optional override `PUBG_AFK_CONFIG`
- `run.auto_exit_after_seconds` and the default `21900`

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document shared config.yaml and auto-exit"
```

---

### Task 7: Final Verification and Push

**Files:**
- Verify: `rustdesk_pubg_afk.py`, `uu_pubg_afk.py`, `config_loader.py`, `config.yaml`

- [ ] **Step 1: Compile all Python files**

```bash
python3 -m py_compile /workspace/config_loader.py /workspace/rustdesk_pubg_afk.py /workspace/uu_pubg_afk.py
```

Expected: exit code 0.

- [ ] **Step 2: Smoke-load config**

```bash
python3 -c "from config_loader import load_config; cfg, err = load_config(); print('err=', err); print(cfg['loop']['interval_seconds'])"
```

Expected: prints `err= None` (or an informational string if file missing), plus `{'min': 280, 'max': 320}`.

- [ ] **Step 3: Push**

```bash
git push origin HEAD:main
```

---

## Plan Self-Review

**Spec coverage check**
- Shared YAML defaults: Task 2
- Loader with env override + defaults: Task 3
- Rust reads all constants from YAML: Task 4
- UU reads all constants from YAML + adds right-click ops: Task 5
- Auto-exit 6h5m: Task 2 + Task 4 Step 5 + Task 5 Step 5
- Dependency wiring for both OS: Task 1

**Placeholder scan**
- No TODO/TBD markers.
- Every code-edit step contains concrete code.

