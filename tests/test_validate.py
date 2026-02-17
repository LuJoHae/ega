#!/usr/bin/env python3
"""
Tests for validate.py script using pytest.

Tests both local and remote directory operations with mocked SSH and pyega3.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import shutil

import pytest

import ega


# Fixtures

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def temp_dataset(temp_dir):
    """Create a complete test dataset structure."""
    # dataset1/file1/{data.txt, data.txt.md5}
    # dataset1/file2/{data.txt, data.txt.md5}
    dataset1 = temp_dir / "dataset1"
    dataset1.mkdir()

    file1_dir = dataset1 / "file1"
    file1_dir.mkdir()
    (file1_dir / "data.txt").write_text("test data 1")
    (file1_dir / "data.txt.md5").write_text("abc123")

    file2_dir = dataset1 / "file2"
    file2_dir.mkdir()
    (file2_dir / "data.txt").write_text("test data 2")
    (file2_dir / "data.txt.md5").write_text("def456")

    return temp_dir


@pytest.fixture
def temp_dirs():
    """Create two temporary directories for multi-dir testing."""
    temp1 = tempfile.mkdtemp()
    temp2 = tempfile.mkdtemp()
    yield Path(temp1), Path(temp2)
    shutil.rmtree(temp1)
    shutil.rmtree(temp2)


# Tests for RemoteDirectory - Local operations

class TestRemoteDirectoryLocal:
    """Test RemoteDirectory with local paths."""

    def test_local_directory_detection(self, temp_dir):
        """Test that local paths are detected correctly."""
        rd = ega.remote_directory.RemoteDirectory(temp_dir)
        assert not rd.is_remote
        assert rd.host is None
        assert rd.path == temp_dir

    def test_local_exists(self, temp_dir):
        """Test exists() for local directories."""
        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        assert rd.exists()

        rd_nonexistent = ega.remote_directory.RemoteDirectory("/nonexistent/path")
        assert not rd_nonexistent.exists()

    def test_local_dir_exists(self, temp_dataset):
        """Test dir_exists() for local subdirectories."""
        rd = ega.remote_directory.RemoteDirectory(str(temp_dataset))
        assert rd.dir_exists("dataset1")
        assert rd.dir_exists("dataset1/file1")
        assert not rd.dir_exists("nonexistent")

    def test_local_list_files(self, temp_dataset):
        """Test list_files() for local directories."""
        rd = ega.remote_directory.RemoteDirectory(str(temp_dataset))
        files = rd.list_files("dataset1/file1")
        assert len(files) == 2
        assert "data.txt" in files
        assert "data.txt.md5" in files

    def test_local_read_file(self, temp_dataset):
        """Test read_file() for local files."""
        rd = ega.remote_directory.RemoteDirectory(str(temp_dataset))
        content = rd.read_file("dataset1/file1/data.txt")
        assert content == "test data 1"

        content_md5 = rd.read_file("dataset1/file1/data.txt.md5")
        assert content_md5 == "abc123"

    def test_local_calculate_md5(self, temp_dir):
        """Test calculate_md5() for local files."""
        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        # Write known content and verify MD5
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello")

        # MD5 of "hello" is 5d41402abc4b2a76b9719d911017c592
        md5 = rd.calculate_md5("test.txt")
        assert md5 == "5d41402abc4b2a76b9719d911017c592"


# Tests for RemoteDirectory - Remote operations

class TestRemoteDirectoryRemote:
    """Test RemoteDirectory with remote (SSH) paths."""

    def test_remote_directory_detection(self):
        """Test that remote paths are detected correctly."""
        rd = ega.remote_directory.RemoteDirectory("user@host:/path/to/data")
        assert rd.is_remote
        assert rd.host == "user@host"
        assert rd.path == Path("/path/to/data")

        rd2 = ega.remote_directory.RemoteDirectory("eiger:/capstor/data")
        assert rd2.is_remote
        assert rd2.host == "eiger"
        assert rd2.path == Path("/capstor/data")

    def test_remote_exists(self, mocker):
        """Test exists() for remote directories."""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="1\n")

        rd = ega.remote_directory.RemoteDirectory("host:/path")
        result = rd.exists()

        assert result
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ssh"
        assert call_args[1] == "host"
        assert "test -d /path" in call_args[2]

    def test_remote_dir_exists(self, mocker):
        """Test dir_exists() for remote subdirectories."""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="1\n")

        rd = ega.remote_directory.RemoteDirectory("host:/base")
        result = rd.dir_exists("dataset1")

        assert result
        call_args = mock_run.call_args[0][0]
        assert "test -d /base/dataset1" in call_args[2]

    def test_remote_list_files(self, mocker):
        """Test list_files() for remote directories."""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="data.txt\ndata.txt.md5\n")

        rd = ega.remote_directory.RemoteDirectory("host:/base")
        files = rd.list_files("dataset1/file1")

        assert len(files) == 2
        assert "data.txt" in files
        assert "data.txt.md5" in files
        call_args = mock_run.call_args[0][0]
        assert "find /base/dataset1/file1" in call_args[2]

    def test_remote_read_file(self, mocker):
        """Test read_file() for remote files."""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="test content", returncode=0)

        rd = ega.remote_directory.RemoteDirectory("host:/base")
        content = rd.read_file("dataset1/file.txt")

        assert content == "test content"
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ssh"
        assert call_args[1] == "host"
        assert "cat /base/dataset1/file.txt" in call_args[2]

    def test_remote_calculate_md5(self, mocker):
        """Test calculate_md5() for remote files."""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(stdout="5d41402abc4b2a76b9719d911017c592  /path/file.txt")

        rd = ega.remote_directory.RemoteDirectory("host:/base")
        md5 = rd.calculate_md5("file.txt")

        assert md5 == "5d41402abc4b2a76b9719d911017c592"
        call_args = mock_run.call_args[0][0]
        assert "md5sum /base/file.txt" in call_args[2]


# Tests for pyega3 integration

class TestPyega3Integration:
    """Test PyEGA3Client integration."""

    def test_get_datasets(self, mocker):
        """Test get_datasets() via PyEGA3Client."""


        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(
            stderr='EGAD00001006630\nEGAD00001006631\nEGAD00001006632\n',
            returncode=0
        )

        client = ega.pyega3_client.PyEGA3Client()
        datasets = client.get_datasets()

        assert len(datasets) == 3
        assert datasets[0] == "EGAD00001006630"
        assert datasets[1] == "EGAD00001006631"
        assert datasets[2] == "EGAD00001006632"

    def test_get_dataset_files(self, mocker):
        """Test get_dataset_files() via PyEGA3Client."""

        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(
            stderr='EGAF00001873329\nEGAF00001873208\nEGAF00001873209\n',
            returncode=0
        )

        client = ega.pyega3_client.PyEGA3Client()
        files = client.get_dataset_files("EGAD00001006630")

        assert len(files) == 3
        assert files[0] == "EGAF00001873329"
        assert files[1] == "EGAF00001873208"
        assert files[2] == "EGAF00001873209"


# Tests for validation functions

class TestValidationFunctions:
    """Test validation functions."""

    def test_read_md5_file(self, temp_dir):
        """Test reading MD5 from .md5 file."""
        # Create test structure
        dataset_dir = temp_dir / "dataset1" / "file1"
        dataset_dir.mkdir(parents=True)
        md5_file = dataset_dir / "data.txt.md5"
        md5_file.write_text("abc123def456  data.txt\n")

        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        md5 = ega.validate.read_md5_file(rd, "dataset1/file1/data.txt.md5")

        assert md5 == "abc123def456"

    def test_validate_file_directory_success(self, temp_dir):
        """Test validation of valid file directory."""
        # Create valid structure
        file_dir = temp_dir / "dataset1" / "file1"
        file_dir.mkdir(parents=True)
        (file_dir / "data.txt").write_text("test data")
        (file_dir / "data.txt.md5").write_text("abc123")

        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        success, msg = ega.validate.validate_file_directory(rd, "dataset1/file1", verify_md5=False)

        assert success
        assert msg == ""

    def test_validate_file_directory_missing(self, temp_dir):
        """Test validation fails for missing directory."""
        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        success, msg = ega.validate.validate_file_directory(rd, "nonexistent", verify_md5=False)

        assert not success
        assert "does not exist" in msg

    def test_validate_file_directory_wrong_file_count(self, temp_dir):
        """Test validation fails with wrong number of files."""
        # Create directory with 3 files
        file_dir = temp_dir / "dataset1" / "file1"
        file_dir.mkdir(parents=True)
        (file_dir / "data.txt").write_text("test")
        (file_dir / "data.txt.md5").write_text("abc")
        (file_dir / "extra.txt").write_text("extra")

        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        success, msg = ega.validate.validate_file_directory(rd, "dataset1/file1", verify_md5=False)

        assert not success
        assert "Expected 2 files, found 3" in msg

    def test_validate_file_directory_missing_md5(self, temp_dir):
        """Test validation fails when .md5 file is missing."""
        # Create directory with 2 non-md5 files
        file_dir = temp_dir / "dataset1" / "file1"
        file_dir.mkdir(parents=True)
        (file_dir / "data.txt").write_text("test")
        (file_dir / "other.txt").write_text("other")

        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        success, msg = ega.validate.validate_file_directory(rd, "dataset1/file1", verify_md5=False)

        assert not success
        assert "Expected 1 .md5 file, found 0" in msg

    def test_validate_file_directory_md5_verification(self, temp_dir):
        """Test MD5 verification."""
        # Create valid structure with known MD5
        file_dir = temp_dir / "dataset1" / "file1"
        file_dir.mkdir(parents=True)
        data_file = file_dir / "data.txt"
        data_file.write_text("hello")
        md5_file = file_dir / "data.txt.md5"
        md5_file.write_text("5d41402abc4b2a76b9719d911017c592")

        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        success, msg = ega.validate.validate_file_directory(rd, "dataset1/file1", verify_md5=True)

        assert success
        assert msg == ""

    def test_validate_file_directory_md5_mismatch(self, temp_dir):
        """Test MD5 verification fails on mismatch."""
        # Create structure with wrong MD5
        file_dir = temp_dir / "dataset1" / "file1"
        file_dir.mkdir(parents=True)
        data_file = file_dir / "data.txt"
        data_file.write_text("hello")
        md5_file = file_dir / "data.txt.md5"
        md5_file.write_text("wrongmd5hash")

        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))
        success, msg = ega.validate.validate_file_directory(rd, "dataset1/file1", verify_md5=True)

        assert not success
        assert "MD5 mismatch" in msg


# Tests for validate_dataset function

class TestValidateDataset:
    """Test validate_dataset function with multiple directories."""

    def test_validate_dataset_found_in_first_dir(self, mocker, temp_dirs):
        """Test dataset found in first directory."""

        temp_dir1, temp_dir2 = temp_dirs

        # Create mock client
        mock_client = mocker.MagicMock(spec=ega.pyega3_client.PyEGA3Client)
        mock_client.get_dataset_files.return_value = ["file1", "file2"]

        # Create dataset in first directory
        dataset_dir = temp_dir1 / "EGAD00001006630"
        dataset_dir.mkdir()
        for file_id in ["file1", "file2"]:
            file_dir = dataset_dir / file_id
            file_dir.mkdir()
            (file_dir / "data.txt").write_text("test")
            (file_dir / "data.txt.md5").write_text("abc123")

        rd1 = ega.remote_directory.RemoteDirectory(str(temp_dir1))
        rd2 = ega.remote_directory.RemoteDirectory(str(temp_dir2))

        success, total = ega.validate.validate_dataset(
            "EGAD00001006630",
            [rd1, rd2],
            verify_md5=False,
            pyega3_client=mock_client
        )

        assert success == 2
        assert total == 2

    def test_validate_dataset_found_in_second_dir(self, mocker, temp_dirs):
        """Test dataset found in second directory when not in first."""

        temp_dir1, temp_dir2 = temp_dirs

        # Create mock client
        mock_client = mocker.MagicMock(spec=ega.pyega3_client.PyEGA3Client)
        mock_client.get_dataset_files.return_value = ["file1"]

        # Create dataset only in second directory
        dataset_dir = temp_dir2 / "EGAD00001006630"
        dataset_dir.mkdir()
        file_dir = dataset_dir / "file1"
        file_dir.mkdir()
        (file_dir / "data.txt").write_text("test")
        (file_dir / "data.txt.md5").write_text("abc123")

        rd1 = ega.remote_directory.RemoteDirectory(str(temp_dir1))
        rd2 = ega.remote_directory.RemoteDirectory(str(temp_dir2))

        success, total = ega.validate.validate_dataset(
            "EGAD00001006630",
            [rd1, rd2],
            verify_md5=False,
            pyega3_client=mock_client
        )

        assert success == 1
        assert total == 1

    def test_validate_dataset_not_found(self, mocker, temp_dirs):
        """Test dataset not found in any directory."""

        temp_dir1, temp_dir2 = temp_dirs

        # Create mock client
        mock_client = mocker.MagicMock(spec=ega.pyega3_client.PyEGA3Client)
        mock_client.get_dataset_files.return_value = ["file1"]

        rd1 = ega.remote_directory.RemoteDirectory(str(temp_dir1))
        rd2 = ega.remote_directory.RemoteDirectory(str(temp_dir2))

        success, total = ega.validate.validate_dataset(
            "EGAD00001006630",
            [rd1, rd2],
            verify_md5=False,
            pyega3_client=mock_client
        )

        assert success == 0
        assert total == 1


# Integration tests

class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_validation_workflow(self, mocker, temp_dir):
        """Test complete validation workflow."""

        # Create mock client
        mock_client = mocker.MagicMock(spec=ega.pyega3_client.PyEGA3Client)
        mock_client.get_datasets.return_value = ["EGAD00001006630"]
        mock_client.get_dataset_files.return_value = ["EGAF00001873329", "EGAF00001873208"]

        # Create complete dataset structure
        dataset1 = temp_dir / "EGAD00001006630"
        dataset1.mkdir()

        for file_id in ["EGAF00001873329", "EGAF00001873208"]:
            file_dir = dataset1 / file_id
            file_dir.mkdir()
            (file_dir / "data.txt").write_text("test data")
            (file_dir / "data.txt.md5").write_text("5d41402abc4b2a76b9719d911017c592")

        rd = ega.remote_directory.RemoteDirectory(str(temp_dir))

        success, total = ega.validate.validate_dataset(
            "EGAD00001006630",
            [rd],
            verify_md5=False,
            pyega3_client=mock_client
        )

        assert success == 2
        assert total == 2
