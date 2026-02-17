import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Union

from ega.utils import DEFAULT_CONNECTIONS, DATASET_ID_PATTERN, FILE_ID_PATTERN, download_file_dry_run


class PyEGA3Client:
    """Wrapper for pyega3 commands."""

    def __init__(self, credentials_file: Optional[Path] = None, connections: int = DEFAULT_CONNECTIONS,
                 dry_run: bool = False):
        """
        Initialize pyega3 client.

        Args:
            credentials_file: Path to credentials JSON file
            connections: Number of parallel connections for downloads
            dry_run: If True, create test files instead of downloading
        """
        self.credentials_file = credentials_file
        self.connections = connections
        self.dry_run = dry_run

    def _run_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run pyega3 command and return output."""
        cmd = ["pyega3"]
        if self.credentials_file:
            cmd.extend(["-cf", str(self.credentials_file)])
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logging.error(f"pyega3 command failed: {' '.join(cmd)}")
            logging.error(f"Error: {e.stderr}")
            raise

    def get_datasets(self) -> List[str]:
        """Get list of authorized datasets."""
        result = self._run_command(["datasets"])
        matches = re.findall(DATASET_ID_PATTERN, result.stderr)
        return matches

    def get_dataset_files(self, dataset_id: str) -> List[str]:
        """Get list of files in a dataset."""
        result = self._run_command(["files", dataset_id])
        matches = re.findall(FILE_ID_PATTERN, result.stderr)
        logging.debug(f"Dataset contains {len(matches)} files")
        if not matches:
            logging.warning(f"No files found in dataset {dataset_id}")
        return matches

    def download_file(self, file_id: str, output_dir: Path) -> Union[Path, Exception]:
        """
        Download a file using pyega3.

        Args:
            file_id: File ID to download
            output_dir: Directory to save file

        Returns:
            file_path, or error
        """
        start_time = time.time()
        logging.debug(f"Downloading file {file_id}")
        if self.dry_run:
            return download_file_dry_run(file_id, output_dir, start_time)

        cmd = self.construct_pyega3_command(file_id, output_dir)
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            elapsed_time = time.time() - start_time
            logging.debug(f"Downloaded {file_id} in {elapsed_time:.2f} seconds")
            return output_dir / file_id
        except subprocess.CalledProcessError as e:
            elapsed_time = time.time() - start_time
            logging.error(f"Failed to download {file_id} after {elapsed_time:.2f} seconds")
            logging.error(f"Error: {e.stderr}")
            return e

    def construct_pyega3_command(self, file_id: str, output_dir: Path) -> List[str]:
        cmd = ["pyega3"]
        if self.credentials_file:
            cmd.extend(["-cf", str(self.credentials_file)])
        cmd.extend(["-c", str(self.connections)])
        cmd.extend(["fetch", file_id, "--output-dir", str(output_dir)])
        return cmd
