import hashlib
import subprocess
from pathlib import Path
from typing import Union, List, Optional
from copy import copy
import logging

class RemoteDirectory:
    """Helper class for remote directory operations via SSH."""

    def __init__(self, location: Union[str, Path, "RemoteDirectory"]) -> None:
        """
        Parse location in format: [user@]host:path or just path for local.
        """
        if isinstance(location, str):
            if ':' in location:
                # Remote path
                host_part, path_part = location.split(':', 1)
                self.host = host_part
                self.path = Path(path_part)
                self.is_remote = True
            else:
                # Local path
                self.host = None
                self.path = Path(location)
                self.is_remote = False
        elif isinstance(location, Path):
            self.host = None
            self.path = Path(location)
            self.is_remote = False

    def _ssh_command(self, cmd: str) -> str:
        """Execute a command via SSH and return output."""
        result = subprocess.run(
            ["ssh", self.host, cmd],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def exists(self) -> bool:
        """Check if directory exists."""
        if self.is_remote:
            result = subprocess.run(
                ["ssh", self.host, f"test -d {self.path} && echo 1 || echo 0"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() == "1"
        else:
            return self.path.is_dir()

    def list_files(self, subpath: str) -> List[str]:
        """List files (not directories) in a directory."""
        full_path = str(self.path / subpath)

        if self.is_remote:
            # Use find to list only files
            output = self._ssh_command(
                f"test -d {full_path} && find {full_path} -maxdepth 1 -type f -printf '%f\\n' || true"
            )
            return [line for line in output.split('\n') if line]
        else:
            dir_path = Path(full_path)
            if not dir_path.is_dir():
                return []
            return [f.name for f in dir_path.iterdir() if f.is_file()]

    def dir_exists(self, subpath: Optional[Path] = None) -> bool:
        """Check if a subdirectory exists."""
        if subpath is None:
            full_path = str(self.path)
        else:
            full_path = str(self.path / subpath)
        logging.debug(f"Checking if directory {full_path} exists")
        if self.is_remote:
            logging.debug(f"Checking if remote dir {full_path} exists")
            result = subprocess.run(
                ["ssh", self.host, f"test -d {full_path} && echo 1 || echo 0"],
                capture_output=True,
                text=True
            )
            logging.debug(f"SSH result: {result.stdout.strip()}")
            return result.stdout.strip() == "1"
        else:
            logging.debug(f"Checking if local dir {full_path} exists")
            return Path(full_path).is_dir()

    def read_file(self, subpath: str) -> Optional[str]:
        """Read a file and return its contents."""
        full_path = str(self.path / subpath)

        if self.is_remote:
            result = subprocess.run(
                ["ssh", self.host, f"cat {full_path}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout
            return None
        else:
            try:
                with open(Path(full_path), 'r') as f:
                    return f.read()
            except Exception:
                return None

    def calculate_md5(self, subpath: str) -> Optional[str]:
        """Calculate MD5 checksum of a file."""
        full_path = str(self.path / subpath)

        if self.is_remote:
            # Use md5sum on remote
            output = self._ssh_command(f"md5sum {full_path} 2>/dev/null || true")
            if output:
                # md5sum output format: "hash  filename"
                return output.split()[0]
            return None
        else:
            try:
                md5_hash = hashlib.md5()
                with open(Path(full_path), 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        md5_hash.update(chunk)
                return md5_hash.hexdigest()
            except Exception:
                return None

    def __truediv__(self, other):
        """Implement the / operator"""
        new_remote_dir = copy(self)
        new_remote_dir.path = self.path / other
        return new_remote_dir
