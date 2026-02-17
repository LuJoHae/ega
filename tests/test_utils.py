"""
Shared test utilities and fixtures for EGA ega.

Contains common functionality used across multiple test files.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock

import pytest


# Shared fixtures

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def temp_dirs():
    """Create multiple temporary directories for multi-dir testing."""
    temps = [tempfile.mkdtemp() for _ in range(3)]
    yield [Path(t) for t in temps]
    for temp in temps:
        shutil.rmtree(temp)


@pytest.fixture
def mock_credentials_file(temp_dir):
    """Create a mock credentials file."""
    creds_file = temp_dir / "credentials.json"
    creds_file.write_text(json.dumps({"username": "test", "password": "test"}))
    return creds_file


# Mock data generators

def create_mock_dataset(dataset_id: str, num_files: int = 3) -> Dict:
    """Create mock dataset metadata."""
    return {
        "datasetId": dataset_id,
        "title": f"Test Dataset {dataset_id}",
        "description": "Mock dataset for testing"
    }


def create_mock_file(file_id: str, size_bytes: int = 1000) -> Dict:
    """Create mock file metadata."""
    return {
        "fileId": file_id,
        "fileName": f"{file_id}.txt",
        "fileSize": size_bytes,
        "checksum": "abc123def456",
        "checksumType": "MD5"
    }


def create_mock_datasets(count: int = 3) -> List[Dict]:
    """Create multiple mock datasets."""
    return [
        create_mock_dataset(f"EGAD0000100{6630 + i}", 5)
        for i in range(count)
    ]


def create_mock_files(dataset_id: str, count: int = 3) -> List[Dict]:
    """Create multiple mock files for a dataset."""
    base_id = int(dataset_id.replace("EGAD", ""))
    return [
        create_mock_file(f"EGAF0000{base_id + i}", 1000 * (i + 1))
        for i in range(count)
    ]


# Test data structure helpers

def create_dataset_structure(base_dir: Path, dataset_id: str, file_ids: List[str]):
    """
    Create a complete dataset directory structure.

    Creates: base_dir/dataset_id/file_id/{data.txt, data.txt.md5}
    """
    dataset_dir = base_dir / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    for file_id in file_ids:
        file_dir = dataset_dir / file_id
        file_dir.mkdir(parents=True, exist_ok=True)

        # Create data file
        data_file = file_dir / "data.txt"
        data_file.write_text(f"Mock data for {file_id}")

        # Create MD5 file
        md5_file = file_dir / "data.txt.md5"
        md5_file.write_text("5d41402abc4b2a76b9719d911017c592  data.txt")


def create_download_result_structure(temp_dir: Path, file_id: str):
    """
    Create structure that pyega3 would create after download.

    Creates: temp_dir/file_id/{downloaded files}
    """
    file_dir = temp_dir / file_id
    file_dir.mkdir(parents=True, exist_ok=True)

    # Simulate downloaded files
    (file_dir / "data.cip").write_text(f"Encrypted data for {file_id}")
    (file_dir / "data.cip.md5").write_text("abc123def456")

    return file_dir


# Mock subprocess helpers

def create_mock_subprocess_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Create a mock subprocess.CompletedProcess result."""
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


def create_mock_pyega3_datasets_response(datasets: List[Dict]) -> str:
    """Create mock JSON response for pyega3 datasets command."""
    return json.dumps(datasets)


def create_mock_pyega3_files_response(files: List[Dict]) -> str:
    """Create mock JSON response for pyega3 files command."""
    return json.dumps(files)


# Assertion helpers

def assert_directory_structure(base_dir: Path, dataset_id: str, file_ids: List[str]):
    """Assert that directory structure exists as expected."""
    dataset_dir = base_dir / dataset_id
    assert dataset_dir.exists(), f"Dataset directory {dataset_dir} does not exist"

    for file_id in file_ids:
        file_dir = dataset_dir / file_id
        assert file_dir.exists(), f"File directory {file_dir} does not exist"
        assert file_dir.is_dir(), f"File path {file_dir} is not a directory"


def assert_file_exists(base_dir: Path, dataset_id: str, file_id: str, filename: str):
    """Assert that a specific file exists in the expected location."""
    file_path = base_dir / dataset_id / file_id / filename
    assert file_path.exists(), f"File {file_path} does not exist"
    assert file_path.is_file(), f"Path {file_path} is not a file"


# Disk space simulation

class MockDiskUsage:
    """Mock object for shutil.disk_usage results."""

    def __init__(self, total: int, used: int, free: int):
        self.total = total
        self.used = used
        self.free = free


def create_mock_disk_usage(free_gb: float = 100.0, used_gb: float = 50.0) -> MockDiskUsage:
    """Create mock disk usage statistics."""
    bytes_per_gb = 1024 ** 3
    total = int((free_gb + used_gb) * bytes_per_gb)
    used = int(used_gb * bytes_per_gb)
    free = int(free_gb * bytes_per_gb)
    return MockDiskUsage(total, used, free)
