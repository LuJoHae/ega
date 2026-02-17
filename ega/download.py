#!/usr/bin/env python3
"""
EGA Dataset Download Manager

Automatically downloads datasets from EGA using pyega3 with intelligent
multi-directory storage management and disk space monitoring.

Features:
- Auto-discover datasets from pyega3
- Multi-directory support with automatic spillover
- Disk space monitoring and threshold management
- Resume capability for interrupted downloads
- Organized storage by dataset
"""

import logging

from ega.logging import setup_logging, log_results, log_preamble, log_summary
from ega.pyega3_client import PyEGA3Client
from ega.download_manager import DownloadManager
from ega.storage_manager import StorageManager
from ega.utils import validate_credentials

DEFAULT_MAX_DISK_USAGE_GB = 100


def download(
        datasets, primary_dir, secondary, max_usage, credentials_file, log_file, connections, temp_dir, dry_run
) -> int:
    setup_logging(log_file)
    err = validate_credentials(credentials_file)
    if err:
        logging.error(f"Invalid credentials file: {credentials_file} lead to error:\n{err}")
        return 1

    # Initialize components
    storage = StorageManager(primary_dir, secondary, max_usage)
    pyega3 = PyEGA3Client(credentials_file, connections, dry_run)
    manager = DownloadManager(storage, pyega3, temp_dir)

    # Start downloads
    log_preamble(primary_dir, secondary, max_usage, connections)
    try:
        results = manager.download_datasets(datasets)
        success, total = log_results(results)
        log_summary(results, storage)
        return 0 if success == total else 1
    except KeyboardInterrupt:
        logging.warning("\n\nDownload interrupted by user")
        return 130
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        return 1
