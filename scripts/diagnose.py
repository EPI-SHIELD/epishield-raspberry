"""Read-only diagnostics: never opens camera, installs packages or changes permissions."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def diagnose():
    return {
        "system": platform.platform(), "architecture": platform.machine(),
        "python": sys.version, "os_release": read("/etc/os-release"),
        "memory": read("/proc/meminfo"), "free_bytes": shutil.disk_usage(Path.home()).free,
        "temperature_millidegrees": read("/sys/class/thermal/thermal_zone0/temp"),
        "webcams": [{"path": str(p), "read_write": os.access(p, os.R_OK | os.W_OK)}
                    for p in Path("/dev").glob("video*")],
        "modules": {name: importlib.util.find_spec(name) is not None
                    for name in ("venv", "cv2", "requests", "edge_impulse_linux")},
    }


if __name__ == "__main__":
    print(json.dumps(diagnose(), indent=2))
