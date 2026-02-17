#!/usr/bin/env python3
"""
Common functionality shared between EGA ega.
"""

import hashlib
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Optional

# Constants
DEFAULT_CONNECTIONS = 20
BYTES_PER_GB = 1024 ** 3

# Regex patterns
DATASET_ID_PATTERN = r'EGAD\d{11}'
FILE_ID_PATTERN = r'EGAF\d{11}'


def extract_dataset_ids(text: str) -> list:
    """Extract dataset IDs from text using regex."""
    return re.findall(DATASET_ID_PATTERN, text)


def extract_file_ids(text: str) -> list:
    """Extract file IDs from text using regex."""
    return re.findall(FILE_ID_PATTERN, text)


def download_file_dry_run(file_id: str, output_dir: Path, start_time: float) -> Path:
    file_dir = output_dir / file_id
    file_dir.mkdir(parents=True, exist_ok=True)
    test_file = file_dir / "test_file.txt"
    test_file.write_text("TEST_FILE")
    md5_hash = hashlib.md5(b"TEST_FILE").hexdigest()
    md5_file = file_dir / "test_file.txt.md5"
    md5_file.write_text(md5_hash)
    elapsed_time = time.time() - start_time
    logging.debug(f"Created test files for {file_id} in {elapsed_time:.2f} seconds")
    logging.debug(f"Filepath: {test_file.absolute()}")
    return file_dir


def move_dir_content(source_dir: Path, target_dir: Path) -> Optional[Exception]:
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        assert isinstance(source_dir, Path) and source_dir.is_dir()
        assert isinstance(source_dir, Path)
        logging.debug(f"Moving {source_dir} to {target_dir}")
        shutil.move(str(source_dir.absolute()), str(target_dir.absolute()))
    except Exception as e:
        return e


def get_dataset_directory(target_dir: Path, dataset_id: str) -> Path:
    dataset_dir = target_dir / dataset_id
    return dataset_dir


def create_dataset_directory(target_dir: Path, dataset_id: str) -> Path:
    # Create dataset directory in primary
    dataset_dir = get_dataset_directory(target_dir, dataset_id)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    logging.debug(f"Dataset directory: {dataset_dir}")
    return dataset_dir


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    except (PermissionError, OSError) as e:
        logging.warning(f"Error calculating directory size for {path}: {e}")
    return total


def validate_credentials(credentials_file: Path):
    if credentials_file and not credentials_file.exists():
        return f"Credentials file not found: {credentials_file}"
    return None
