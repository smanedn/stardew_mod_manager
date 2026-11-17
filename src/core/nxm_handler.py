"""Windows HKCU nxm:// URI protocol registration for Mod Manager Download links."""

from __future__ import annotations

import sys
from pathlib import Path


def build_nxm_command(is_frozen: bool, project_root: Path, executable: str | None = None) -> str:
    """Build the shell open command string for handling nxm:// links."""
    exe = executable or sys.executable
    if is_frozen:
        return f'"{exe}" "%1"'
    venv_pythonw = project_root / ".venv" / "Scripts" / "pythonw.exe"
    python_bin = str(venv_pythonw) if venv_pythonw.is_file() else exe
    main_script = (project_root / "main.py").resolve()
    return f'"{python_bin}" "{main_script}" "%1"'


def register_nxm_protocol(command: str) -> None:
    """Register the current user (HKCU) nxm:// URI handler on Windows."""
    if sys.platform != "win32":
        raise OSError("nxm:// registry registration is only supported on Windows.")

    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\nxm") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Nexus Mod Manager Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, r"Software\Classes\nxm\shell\open\command"
    ) as cmd_key:
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
