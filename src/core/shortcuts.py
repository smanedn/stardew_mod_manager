"""Desktop shortcut creation for one-click Stardew Valley modpack launching."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

_SAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def get_desktop_dir() -> Path:
    """Return the user's Desktop directory."""
    return Path.home() / "Desktop"


def _sanitize_filename(name: str) -> str:
    clean = _SAFE_FILENAME_RE.sub("_", name).strip(" .")
    return clean or "SVMM_Modpack"


def build_shortcut_target(
    profile_id: str,
    *,
    is_frozen: bool | None = None,
    executable: str | None = None,
    script_path: Path | None = None,
) -> tuple[str, list[str], str]:
    """Return (target_executable, args, working_dir) for launching a modpack directly."""
    frozen = getattr(sys, "frozen", False) if is_frozen is None else is_frozen
    exe = executable or sys.executable
    if frozen:
        exe_path = Path(exe).resolve()
        return str(exe_path), ["--launch-profile", profile_id], str(exe_path.parent)

    main_script = (script_path or Path(__file__).resolve().parents[2] / "main.py").resolve()
    exe_path = Path(exe)
    if sys.platform == "win32" and exe_path.name.lower() == "python.exe":
        pythonw = exe_path.with_name("pythonw.exe")
        if pythonw.is_file():
            exe_path = pythonw
    return (
        str(exe_path),
        [str(main_script), "--launch-profile", profile_id],
        str(main_script.parent),
    )


def create_modpack_shortcut(
    profile_id: str,
    shortcut_name: str | None = None,
    icon_path: Path | None = None,
    desktop_dir: Path | None = None,
) -> Path:
    """Create a Desktop shortcut that launches Stardew Valley with the given modpack."""
    desktop = desktop_dir or get_desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    safe_name = _sanitize_filename(shortcut_name or f"Stardew ({profile_id})")
    target_exe, args, workdir = build_shortcut_target(profile_id)

    if sys.platform == "win32":
        lnk_path = desktop / f"{safe_name}.lnk"
        arg_str = subprocess.list2cmdline(args)

        def _ps_quote(val: str) -> str:
            return val.replace("'", "''")

        ps_lines = [
            "$WshShell = New-Object -ComObject WScript.Shell",
            f"$Shortcut = $WshShell.CreateShortcut('{_ps_quote(str(lnk_path))}')",
            f"$Shortcut.TargetPath = '{_ps_quote(target_exe)}'",
            f"$Shortcut.Arguments = '{_ps_quote(arg_str)}'",
            f"$Shortcut.WorkingDirectory = '{_ps_quote(workdir)}'",
            f"$Shortcut.Description = 'Launch Stardew Valley with modpack {_ps_quote(profile_id)}'",
        ]
        if icon_path and icon_path.is_file():
            ps_lines.append(f"$Shortcut.IconLocation = '{_ps_quote(str(icon_path))},0'")
        ps_lines.append("$Shortcut.Save()")

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "; ".join(ps_lines)],
            capture_output=True,
            text=True,
            creationflags=flags,
            check=False,
        )
        if res.returncode != 0 or not lnk_path.is_file():
            raise OSError(res.stderr.strip() or "Failed to create Windows .lnk shortcut.")
        return lnk_path

    if sys.platform == "darwin":
        cmd_path = desktop / f"{safe_name}.command"
        quoted_args = " ".join(f'"{a}"' for a in args)
        cmd_path.write_text(
            f'#!/bin/bash\ncd "{workdir}"\n"{target_exe}" {quoted_args}\n',
            encoding="utf-8",
        )
        os.chmod(cmd_path, 0o755)
        return cmd_path

    desktop_file = desktop / f"{safe_name}.desktop"
    quoted_args = " ".join(f'"{a}"' for a in args)
    icon_line = f"Icon={icon_path}\n" if icon_path and icon_path.is_file() else ""
    desktop_file.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={safe_name}\n"
        f'Exec="{target_exe}" {quoted_args}\n'
        f"Path={workdir}\n"
        f"{icon_line}"
        "Terminal=false\n",
        encoding="utf-8",
    )
    os.chmod(desktop_file, 0o755)
    return desktop_file
