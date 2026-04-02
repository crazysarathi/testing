from __future__ import annotations

import configparser
import json
import platform
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="App Lunch API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LaunchRequest(BaseModel):
    name: str


def current_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def unique_apps(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []

    for app_info in sorted(apps, key=lambda item: item["name"].lower()):
        key = normalize_name(app_info["name"])
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(app_info)

    return unique


def read_linux_desktop_file(path: Path) -> dict[str, Any] | None:
    parser = configparser.ConfigParser(interpolation=None)

    try:
        parser.read(path, encoding="utf-8")
    except (configparser.Error, OSError, UnicodeDecodeError):
        return None

    if "Desktop Entry" not in parser:
        return None

    section = parser["Desktop Entry"]
    if section.get("Type") != "Application":
        return None
    if section.getboolean("NoDisplay", fallback=False):
        return None
    if section.getboolean("Hidden", fallback=False):
        return None

    name = (section.get("Name") or "").strip()
    exec_line = (section.get("Exec") or "").strip()
    if not name or not exec_line:
        return None

    return {
        "name": name,
        "launch_ref": path.name,
        "command": exec_line,
        "source": str(path),
        "platform": "linux",
    }


def discover_linux_apps() -> list[dict[str, Any]]:
    locations = [
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path.home() / ".local/share/applications",
        Path("/var/lib/flatpak/exports/share/applications"),
    ]

    apps: list[dict[str, Any]] = []
    for location in locations:
        if not location.exists():
            continue
        for desktop_file in location.rglob("*.desktop"):
            app_info = read_linux_desktop_file(desktop_file)
            if app_info:
                apps.append(app_info)

    return unique_apps(apps)


def discover_windows_apps() -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-StartApps | Sort-Object Name | Select-Object Name, AppID | ConvertTo-Json -Compress",
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []

    if completed.returncode != 0 or not completed.stdout.strip():
        return []

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        payload = [payload]

    apps = []
    for entry in payload:
        name = (entry.get("Name") or "").strip()
        app_id = (entry.get("AppID") or "").strip()
        if not name or not app_id:
            continue
        apps.append(
            {
                "name": name,
                "launch_ref": app_id,
                "command": None,
                "source": "Get-StartApps",
                "platform": "windows",
            }
        )

    return unique_apps(apps)


def discover_macos_apps() -> list[dict[str, Any]]:
    locations = [Path("/Applications"), Path.home() / "Applications"]
    apps: list[dict[str, Any]] = []

    for location in locations:
        if not location.exists():
            continue
        for app_bundle in location.rglob("*.app"):
            apps.append(
                {
                    "name": app_bundle.stem,
                    "launch_ref": app_bundle.stem,
                    "command": None,
                    "source": str(app_bundle),
                    "platform": "macos",
                }
            )

    return unique_apps(apps)


def discover_apps() -> list[dict[str, Any]]:
    system_name = current_platform()
    if system_name == "windows":
        return discover_windows_apps()
    if system_name == "macos":
        return discover_macos_apps()
    return discover_linux_apps()


def clean_exec_tokens(exec_line: str) -> list[str]:
    tokens = shlex.split(exec_line, posix=True)
    return [token for token in tokens if not token.startswith("%")]


def find_best_match(name: str, apps: list[dict[str, Any]]) -> dict[str, Any] | None:
    query = normalize_name(name)
    if not query:
        return None

    for app_info in apps:
        if normalize_name(app_info["name"]) == query:
            return app_info

    for app_info in apps:
        if query in normalize_name(app_info["name"]):
            return app_info

    return None


def launch_linux_app(app_info: dict[str, Any]) -> None:
    launch_ref = app_info.get("launch_ref")
    command = app_info.get("command")

    if launch_ref and shutil.which("gtk-launch"):
        subprocess.Popen(
            ["gtk-launch", launch_ref],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    if not command:
        raise FileNotFoundError("No Linux launch command found for this app.")

    subprocess.Popen(
        clean_exec_tokens(command),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_windows_app(app_info: dict[str, Any]) -> None:
    launch_ref = app_info.get("launch_ref")
    if not launch_ref:
        raise FileNotFoundError("No Windows application ID found for this app.")

    subprocess.Popen(
        ["explorer.exe", f"shell:AppsFolder\\{launch_ref}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_macos_app(app_info: dict[str, Any]) -> None:
    launch_ref = app_info.get("launch_ref")
    if not launch_ref:
        raise FileNotFoundError("No macOS application name found for this app.")

    subprocess.Popen(
        ["open", "-a", launch_ref],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_app_by_platform(app_info: dict[str, Any]) -> None:
    system_name = current_platform()
    if system_name == "windows":
        launch_windows_app(app_info)
        return
    if system_name == "macos":
        launch_macos_app(app_info)
        return
    launch_linux_app(app_info)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "platform": current_platform()}


@app.get("/apps")
def list_apps(q: str = "") -> dict[str, Any]:
    apps = discover_apps()
    query = normalize_name(q)
    if query:
        apps = [app_info for app_info in apps if query in normalize_name(app_info["name"])]

    return {
        "platform": current_platform(),
        "count": len(apps),
        "apps": apps[:200],
    }


@app.post("/launch")
def launch(request: LaunchRequest) -> dict[str, Any]:
    apps = discover_apps()
    app_info = find_best_match(request.name, apps)

    if not app_info:
        raise HTTPException(
            status_code=404,
            detail=f'No installed app matched "{request.name}".',
        )

    try:
        launch_app_by_platform(app_info)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "message": f'Opened "{app_info["name"]}".',
        "app": app_info,
    }
