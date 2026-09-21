import os
import subprocess
import sys
from pathlib import Path


def pick_folder() -> str | None:
    if sys.platform == "darwin":
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'set f to choose folder with prompt "Choose where to save downloads"',
                "-e",
                "POSIX path of f",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    if sys.platform == "win32":
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$b = New-Object System.Windows.Forms.FolderBrowserDialog; "
            "$b.Description = 'Choose where to save downloads'; "
            "if ($b.ShowDialog() -eq 'OK') { $b.SelectedPath }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    for cmd in (
        ["zenity", "--file-selection", "--directory", "--title=Choose where to save downloads"],
        ["kdialog", "--getexistingdirectory", os.path.expanduser("~")],
    ):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            return result.stdout.strip() or None
        return None
    return None


def resolve_writable_dir(path: str) -> Path:
    if not path or not path.strip():
        raise ValueError("Choose a download folder.")
    directory = Path(path.strip()).expanduser()
    if not directory.is_absolute():
        directory = directory.resolve()
    else:
        directory = directory.resolve()
    if not directory.exists():
        raise ValueError("That folder does not exist.")
    if not directory.is_dir():
        raise ValueError("That path is not a folder.")
    if not os.access(directory, os.W_OK):
        raise ValueError("That folder is not writable.")
    return directory
