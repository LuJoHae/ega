import logging
import shutil
import subprocess
from pathlib import Path
from typing import Union, Optional

from ega.utils import BYTES_PER_GB, get_dataset_directory, get_directory_size
from ega.remote_directory import RemoteDirectory


class StorageManager:
    """Manages primary local directory and optional secondary remote directory.

    Downloads go to the primary directory. Completed datasets can be moved
    to the secondary directory (which can be remote via SSH).
    """

    def __init__(
        self,
        primary_dir: Union[Path, str],
        secondary_dir: Optional[Union[RemoteDirectory, Path, str]] = None,
        max_usage_gb: float = 100
    ):
        """
        Initialize storage manager.

        Args:
            primary_dir: Primary local directory for downloads
            secondary_dir: Optional secondary directory (can be remote) for completed datasets
            max_usage_gb: Maximum disk usage for primary directory in GB
        """
        # Primary directory must be local
        self.primary_dir = Path(primary_dir)

        # Create primary directory if it doesn't exist
        self.primary_dir.mkdir(parents=True, exist_ok=True)

        # Secondary directory (optional, can be remote)
        if secondary_dir is not None:
            if isinstance(secondary_dir, RemoteDirectory):
                self.secondary_dir = secondary_dir
            else:
                self.secondary_dir = RemoteDirectory(str(secondary_dir))
        else:
            self.secondary_dir = None

        self.max_usage_bytes = int(max_usage_gb * BYTES_PER_GB)

    def move_to_secondary(self, dataset_id: str) -> bool:
        """
        Move a completed dataset from primary to secondary directory.

        Args:
            dataset_id: Dataset ID to move

        Returns:
            True if successful, False otherwise
        """
        if self.secondary_dir is None:
            logging.warning("No secondary directory configured")
            return False

        source_path = get_dataset_directory(self.primary_dir, dataset_id)
        if not source_path.exists():
            logging.error(f"Source dataset not found: {source_path}")
            return False

        try:
            logging.info(f"Moving current batch of {dataset_id} to secondary...")
            if self.secondary_dir.is_remote:
                # Use rsync for remote copy
                dest = f"{self.secondary_dir.host}:{self.secondary_dir.path}/{dataset_id}"
                subprocess.run(
                    ["ssh", self.secondary_dir.host, f"mkdir -p {self.secondary_dir.path}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logging.debug(f"Moving {dataset_id} to remote: {dest}")
                result = subprocess.run(
                    ["rsync", "-avz", "--remove-source-files", str(source_path) + "/", dest + "/"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logging.debug(f"Successfully moved {dataset_id} to secondary (remote)")
            else:
                # Local move
                dest_path = Path(self.secondary_dir.path) / dataset_id
                logging.debug(f"Moving {dataset_id} to local: {dest_path}")
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                for file_path in source_path.iterdir():
                    shutil.move(str(file_path), str(dest_path))
                    logging.debug(f"Successfully moved {file_path} to secondary (local)")
                logging.debug(f"Successfully moved batch of {dataset_id} to secondary (local)")

            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"rsync failed for {dataset_id}: exit code {e.returncode}")
            logging.error(f"stdout: {e.stdout}")
            logging.error(f"stderr: {e.stderr}")
            return False
        except Exception as e:
            logging.error(f"Failed to move {dataset_id} to secondary: {e}")
            return False

    def get_storage_summary(self) -> str:
        """Get summary of storage usage."""
        lines = ["Storage Summary:"]

        # Primary directory
        if self.primary_dir.exists():
            usage = shutil.disk_usage(self.primary_dir)
            dir_size = get_directory_size(self.primary_dir)
            lines.append(
                f"  Primary: {self.primary_dir}\n"
                f"    Used by downloads: {dir_size / BYTES_PER_GB:.2f} GB / {self.max_usage_bytes / BYTES_PER_GB:.2f} GB\n"
                f"    Disk free: {usage.free / BYTES_PER_GB:.2f} GB"
            )
        else:
            lines.append(f"  Primary: {self.primary_dir} (not found)")

        # Secondary directory
        if self.secondary_dir is not None:
            if self.secondary_dir.is_remote:
                lines.append(f"  Secondary (remote): {self.secondary_dir.host}:{self.secondary_dir.path}")
            else:
                lines.append(f"  Secondary (local): {self.secondary_dir.path}")
        else:
            lines.append("  Secondary: Not configured")

        return "\n".join(lines)

    def disk_usage_exceeded(self, dataset_id: str) -> bool:
        disk_usage = get_directory_size(get_dataset_directory(self.primary_dir, dataset_id))
        logging.info(f"Disk usage of {dataset_id}: {disk_usage}/{self.max_usage_bytes}")
        return disk_usage > self.max_usage_bytes
