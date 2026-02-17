#!/usr/bin/env python3
"""
Validation script for EGA dataset directory structure and MD5 checksums.

Validates that:
- Dataset directories exist
- File ID subdirectories exist
- Exactly 2 files exist per file ID (data file + .md5 checksum)
- Optional: MD5 checksums match

Uses pyega3 to fetch dataset and file information.
Supports both local and remote (SSH) directories.
"""

import argparse
import sys
from argparse import Namespace
from pathlib import Path, PurePosixPath
from typing import List, Tuple, Optional
from ega.remote_directory import RemoteDirectory
from ega.pyega3_client import PyEGA3Client


def read_md5_file(base_dir: RemoteDirectory, file_path: str) -> Optional[str]:
    """Read MD5 checksum from .md5 file. Returns first word on first line."""
    try:
        content = base_dir.read_file(file_path)
        if content:
            content = content.strip()
            # MD5 is typically the first word (32 hex chars)
            return content.split()[0] if content else None
        return None
    except Exception as e:
        print(f"  WARNING: Error reading MD5 file {file_path}: {e}")
        return None


def validate_file_directory(base_dir: RemoteDirectory, file_path: str, verify_md5: bool) -> Tuple[bool, str]:
    """
    Validate a single file ID directory.
    Returns (success, error_message).
    """
    if not base_dir.dir_exists(file_path):
        return False, f"Directory does not exist: {file_path}"

    # Get all files in directory (not subdirectories)
    files = base_dir.list_files(file_path)

    if len(files) != 2:
        return False, f"Expected 2 files, found {len(files)}: {file_path}"

    # Identify MD5 file and data file
    md5_files = [f for f in files if f.endswith('.md5')]
    data_files = [f for f in files if not f.endswith('.md5')]

    if len(md5_files) != 1:
        return False, f"Expected 1 .md5 file, found {len(md5_files)}: {file_path}"

    if len(data_files) != 1:
        return False, f"Expected 1 data file, found {len(data_files)}: {file_path}"

    # Optional MD5 verification
    if verify_md5:
        md5_file = str(PurePosixPath(file_path) / md5_files[0])
        data_file = str(PurePosixPath(file_path) / data_files[0])

        expected_md5 = read_md5_file(base_dir, md5_file)
        if expected_md5 is None:
            return False, f"Could not read MD5 from {md5_file}"

        actual_md5 = base_dir.calculate_md5(data_file)
        if actual_md5 is None:
            return False, f"Could not calculate MD5 for {data_file}"

        if expected_md5.lower() != actual_md5.lower():
            return False, f"MD5 mismatch for {data_file}: expected {expected_md5}, got {actual_md5}"

    return True, ""


def validate_dataset(dataset_id: str, base_dirs: List[RemoteDirectory], verify_md5: bool, pyega3_client: PyEGA3Client) -> Tuple[int, int]:
    """
    Validate a single dataset.
    Searches through base_dirs to find the dataset directory.
    Returns (success_count, total_count).
    """
    # Get file IDs from pyega3
    print(f"\nFetching file list for dataset {dataset_id}...")
    file_ids = pyega3_client.get_dataset_files(dataset_id)
    print(f"Dataset: {dataset_id} ({len(file_ids)} files)")

    # Find which base directory contains this dataset
    found_base_dir = None
    for base_dir in base_dirs:
        if base_dir.dir_exists(dataset_id):
            found_base_dir = base_dir
            if base_dir.is_remote:
                print(f"  Found in: {base_dir.host}:{base_dir.path}")
            else:
                print(f"  Found in: {base_dir.path}")
            break

    if found_base_dir is None:
        # Try to provide helpful error message
        locations = []
        for bd in base_dirs:
            if bd.is_remote:
                locations.append(f"{bd.host}:{bd.path}")
            else:
                locations.append(str(bd.path))
        print(f"  ERROR: Dataset directory not found in any of: {', '.join(locations)}")
        return 0, len(file_ids)

    success_count = 0

    for file_id in file_ids:
        file_path = str(PurePosixPath(dataset_id) / file_id)
        success, error_msg = validate_file_directory(found_base_dir, file_path, verify_md5)

        if success:
            success_count += 1
        else:
            print(f"  ERROR: {file_id}: {error_msg}")

    print(f"  SUCCESS: {success_count}/{len(file_ids)} files validated successfully")

    return success_count, len(file_ids)


def validate(args: Namespace):
    # Parse base directories (local or remote)
    base_dirs = [RemoteDirectory(bd) for bd in args.base_dirs]

    # Validate base directories exist
    for i, base_dir in enumerate(base_dirs):
        if not base_dir.exists():
            print(f"ERROR: Base directory not found: {args.base_dirs[i]}")
            sys.exit(1)

    # Validate credentials file if provided
    if args.credentials_file and not args.credentials_file.exists():
        print(f"ERROR: Credentials file not found: {args.credentials_file}")
        sys.exit(1)

    # Initialize PyEGA3 client
    pyega3_client = PyEGA3Client(args.credentials_file)

    # Get dataset list
    if args.datasets:
        dataset_ids = args.datasets
        print(f"Validating {len(dataset_ids)} specified datasets")
    else:
        print("Fetching authorized datasets from pyega3...")
        dataset_ids = pyega3_client.get_datasets()
        print(f"Found {len(dataset_ids)} authorized datasets")

    print(f"Base directories ({len(base_dirs)}):")
    for bd in base_dirs:
        if bd.is_remote:
            print(f"  - {bd.host}:{bd.path}")
        else:
            print(f"  - {bd.path}")

    if args.verify_md5:
        print("MD5 verification: ENABLED")
    else:
        print("MD5 verification: DISABLED")

    # Validate each dataset
    total_success = 0
    total_files = 0

    for dataset_id in dataset_ids:
        try:
            success, count = validate_dataset(dataset_id, base_dirs, args.verify_md5, pyega3_client)
            total_success += success
            total_files += count
        except Exception as e:
            print(f"ERROR: Failed to validate dataset {dataset_id}: {e}")

    # Summary
    print("\n" + "=" * 50)
    print(f"SUMMARY")
    print(f"  Total files: {total_files}")
    print(f"  Successful: {total_success}")
    print(f"  Failed: {total_files - total_success}")

    if total_success == total_files:
        print("\nSUCCESS: All validations passed!")
        sys.exit(0)
    else:
        print("\nERROR: Some validations failed")
        sys.exit(1)
