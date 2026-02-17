#!/usr/bin/env python3
"""
Tests for download.py script using pytest.

Tests storage management, pyega3 client, and download orchestration.
"""
import subprocess

import ega
from tests.test_utils import (
    temp_dir,
    temp_dirs,
    mock_credentials_file,
    create_mock_files,
    create_mock_disk_usage,
    create_mock_subprocess_result,
    create_download_result_structure,
    assert_directory_structure
)


# Tests for StorageManager

class TestStorageManager:
    """Test StorageManager class."""

    def test_initialization_single_directory(self, temp_dir):
        """Test initialization with primary directory only."""
        sm = ega.storage_manager.StorageManager(temp_dir, max_usage_gb=50)

        assert sm.primary_dir == temp_dir
        assert sm.secondary_dir is None
        assert sm.max_usage_bytes == 50 * (1024 ** 3)
        assert temp_dir.exists()

    def test_initialization_multiple_directories(self, temp_dirs):
        """Test initialization with primary and secondary directories."""
        sm = ega.storage_manager.StorageManager(temp_dirs[0], temp_dirs[1], max_usage_gb=100)

        assert sm.primary_dir == temp_dirs[0]
        assert sm.secondary_dir is not None
        assert sm.secondary_dir.path == temp_dirs[1]
        assert sm.max_usage_bytes == 100 * (1024 ** 3)


    def test_get_directory_size_empty(self, temp_dir):
        """Test get_directory_size for empty directory."""
        size = ega.utils.get_directory_size(temp_dir)
        assert size == 0

    def test_get_directory_size_with_files(self, temp_dir):
        """Test get_directory_size calculates correctly."""
        # Create some files
        (temp_dir / "file1.txt").write_text("hello")  # 5 bytes
        (temp_dir / "file2.txt").write_text("world")  # 5 bytes
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("test")  # 4 bytes
        size = ega.utils.get_directory_size(temp_dir)
        assert size == 14  # 5 + 5 + 4


    def test_get_storage_summary(self, temp_dirs, mocker):
        """Test get_storage_summary generates report."""
        sm = ega.storage_manager.StorageManager(temp_dirs[0], temp_dirs[1], max_usage_gb=100)

        # Mock disk usage
        mock_disk_usage = create_mock_disk_usage(free_gb=50, used_gb=50)
        mocker.patch('shutil.disk_usage', return_value=mock_disk_usage)

        summary = sm.get_storage_summary()

        assert "Storage Summary" in summary
        assert "Primary" in summary
        assert "Secondary" in summary
        assert str(temp_dirs[0]) in summary
        assert "GB" in summary


# Tests for PyEGA3Client

class TestPyEGA3Client:
    """Test PyEGA3Client class."""

    def test_initialization(self, mock_credentials_file):
        """Test client initialization."""
        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file, connections=30)

        assert client.credentials_file == mock_credentials_file
        assert client.connections == 30

    def test_get_datasets(self, mocker, mock_credentials_file):
        """Test get_datasets fetches and parses dataset list."""
        # Create stderr output with dataset IDs (pyega3 outputs to stderr)
        stderr_output = "EGAD00001006630\nEGAD00001006631\nEGAD00001006632\n"
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = create_mock_subprocess_result(
            stderr=stderr_output
        )

        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        datasets = client.get_datasets()

        assert len(datasets) == 3
        assert datasets[0] == 'EGAD00001006630'
        assert datasets[1] == 'EGAD00001006631'
        assert datasets[2] == 'EGAD00001006632'
        mock_run.assert_called_once()

        # Verify pyega3 command structure (no -j flag for non-JSON mode)
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "pyega3"
        assert "-cf" in call_args
        assert "datasets" in call_args

    def test_get_dataset_files(self, mocker, mock_credentials_file):
        """Test get_dataset_files fetches file list."""
        dataset_id = "EGAD00001006630"
        # Create stderr output with file IDs (pyega3 outputs to stderr)
        stderr_output = "EGAF00001006630\nEGAF00001006631\nEGAF00001006632\nEGAF00001006633\nEGAF00001006634\n"
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = create_mock_subprocess_result(
            stderr=stderr_output
        )

        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        files = client.get_dataset_files(dataset_id)

        assert len(files) == 5
        assert files[0].startswith('EGAF')
        assert files[0] == 'EGAF00001006630'

        # Verify command
        call_args = mock_run.call_args[0][0]
        assert "files" in call_args
        assert dataset_id in call_args

    def test_download_file_success(self, mocker, temp_dir, mock_credentials_file):
        """Test successful file download."""
        file_id = "EGAF00001873329"
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = create_mock_subprocess_result()

        # Create expected download result
        result_dir = create_download_result_structure(temp_dir, file_id)

        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file, connections=20)
        file_path = client.download_file(file_id, temp_dir)

        assert file_path == temp_dir / file_id

        # Verify command
        call_args = mock_run.call_args[0][0]
        assert "pyega3" in call_args
        assert "-c" in call_args
        assert "20" in call_args
        assert "fetch" in call_args
        assert file_id in call_args

    def test_download_file_failure(self, mocker, temp_dir, mock_credentials_file):
        """Test failed file download."""
        file_id = "EGAF00001873329"
        mock_run = mocker.patch('subprocess.run')
        # Simulate CalledProcessError
        error = subprocess.CalledProcessError(1, ['pyega3'], stderr="Download failed")
        mock_run.side_effect = error

        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        file_path = client.download_file(file_id, temp_dir)

        assert isinstance(file_path, Exception)


# Tests for DownloadManager

class TestDownloadManager:
    """Test DownloadManager class."""

    def test_initialization(self, temp_dir, mock_credentials_file):
        """Test download manager initialization."""
        storage = ega.storage_manager.StorageManager(temp_dir)
        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        manager = ega.download_manager.DownloadManager(storage, client, temp_dir / "temp")

        assert manager.storage == storage
        assert manager.pyega3 == client
        assert manager.temp_dir.exists()

    def test_download_dataset_resume_skip_existing(self, mocker, temp_dir, mock_credentials_file):
        """Test download skips already downloaded files."""
        dataset_id = "EGAD00001006630"
        file_id = "EGAF00001873329"
        mock_file_ids = [file_id]

        # Create pre-existing file structure
        file_dir = temp_dir / dataset_id / file_id
        file_dir.mkdir(parents=True)
        (file_dir / "existing.txt").write_text("already here")

        storage = ega.storage_manager.StorageManager(temp_dir, max_usage_gb=100)
        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        manager = ega.download_manager.DownloadManager(storage, client, temp_dir / "temp")

        mocker.patch.object(client, 'get_dataset_files', return_value=mock_file_ids)
        mock_download = mocker.patch.object(client, 'download_file')

        # Mock disk usage
        mock_disk_usage = create_mock_disk_usage(free_gb=100, used_gb=10)
        mocker.patch('shutil.disk_usage', return_value=mock_disk_usage)

        success = manager.download_dataset(dataset_id)

        assert success
        # download_file should not be called since file exists
        mock_download.assert_not_called()

    def test_download_dataset_no_storage(self, mocker, temp_dir, mock_credentials_file):
        """Test download fails when no storage available."""
        dataset_id = "EGAD00001006630"
        mock_files = create_mock_files(dataset_id, 2)

        storage = ega.storage_manager.StorageManager(temp_dir, max_usage_gb=0.00001)
        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        manager = ega.download_manager.DownloadManager(storage, client, temp_dir / "temp")

        mocker.patch.object(client, 'get_dataset_files', return_value=mock_files)

        # Fill directory to exceed threshold
        (temp_dir / "large.txt").write_text("x" * 100000)

        # Mock disk usage
        mock_disk_usage = create_mock_disk_usage(free_gb=100, used_gb=10)
        mocker.patch('shutil.disk_usage', return_value=mock_disk_usage)

        success = manager.download_dataset(dataset_id)

        assert not success

    def test_download_datasets_all(self, mocker, temp_dir, mock_credentials_file):
        """Test downloading all authorized datasets."""
        mock_dataset_ids = ["EGAD00001006630", "EGAD00001006631"]

        storage = ega.storage_manager.StorageManager(temp_dir, max_usage_gb=100)
        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        manager = ega.download_manager.DownloadManager(storage, client, temp_dir / "temp")

        mocker.patch.object(client, 'get_datasets', return_value=mock_dataset_ids)

        # Mock download_dataset to always succeed
        mocker.patch.object(manager, 'download_dataset', return_value=True)

        # Mock disk usage
        mock_disk_usage = create_mock_disk_usage(free_gb=100, used_gb=10)
        mocker.patch('shutil.disk_usage', return_value=mock_disk_usage)

        results = manager.download_datasets(dataset_ids=None)

        assert len(results) == 2
        assert all(results.values())

    def test_download_datasets_specific(self, mocker, temp_dir, mock_credentials_file):
        """Test downloading specific datasets."""
        dataset_ids = ["EGAD00001006630", "EGAD00001006631"]

        storage = ega.storage_manager.StorageManager(temp_dir, max_usage_gb=100)
        client = ega.pyega3_client.PyEGA3Client(mock_credentials_file)
        manager = ega.download_manager.DownloadManager(storage, client, temp_dir / "temp")

        mocker.patch.object(manager, 'download_dataset', return_value=True)

        # Mock disk usage
        mock_disk_usage = create_mock_disk_usage(free_gb=100, used_gb=10)
        mocker.patch('shutil.disk_usage', return_value=mock_disk_usage)

        results = manager.download_datasets(dataset_ids=dataset_ids)

        assert len(results) == 2
        assert all(results.values())
