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

