import logging
from pathlib import Path
from typing import Optional, List, Dict

from ega.pyega3_client import PyEGA3Client
from ega.storage_manager import StorageManager
from ega.utils import create_dataset_directory, move_dir_content


class DownloadManager:
    """Manages dataset downloads with storage management."""

    def __init__(self, storage_manager: StorageManager, pyega3_client: PyEGA3Client, temp_dir: Optional[Path] = None):
        """
        Initialize download manager.

        Args:
            storage_manager: Storage manager instance
            pyega3_client: PyEGA3 client instance
            temp_dir: Temporary directory for downloads (default: system temp)
        """
        self.storage = storage_manager
        self.pyega3 = pyega3_client
        self.temp_dir = Path(temp_dir) if temp_dir else Path("/tmp/ega_downloads")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = pyega3_client.dry_run

    def download_dataset(self, dataset_id: str) -> bool:
        """
        Download all files in a dataset.

        Args:
            dataset_id: Dataset ID to download

        Returns:
            True if successful, False otherwise
        """
        logging.debug(f"{'='*60}")
        logging.debug(f"Processing dataset: {dataset_id}")
        logging.debug(f"{'='*60}")

        try:
            files = self.pyega3.get_dataset_files(dataset_id)
            dataset_dir = create_dataset_directory(self.storage.primary_dir, dataset_id)

            # Download each file
            success_count = 0
            using_secondary = False
            for i, file_id in enumerate(files, 1):
                logging.info(f"File {i}/{len(files)}: {file_id}")

                # Check if already downloaded
                # Check if already downloaded in primary
                file_dir = dataset_dir / file_id
                if file_dir.exists() and any(file_dir.iterdir()):
                    logging.debug(f"File {file_id} already exists in primary, skipping")
                    success_count += 1
                    continue

                # Check if already exists in secondary
                if self.storage.secondary_dir is not None:
                    secondary_dataset_dir = self.storage.secondary_dir / dataset_id
                    secondary_file_dir = secondary_dataset_dir / file_id

                    # Handle both local and remote secondary directories
                    file_exists_in_secondary = False
                    if hasattr(secondary_file_dir, 'dir_exists'):  # RemoteDirectory
                        logging.debug(f"Checking if {file_id} exists in remote secondary storage")
                        file_exists_in_secondary = secondary_file_dir.dir_exists()
                        logging.debug(f"File {file_id} exists in remote secondary storage: {file_exists_in_secondary}")
                    elif isinstance(secondary_file_dir, Path):  # Local Path
                        logging.info(f"Checking if {file_id} exists in local secondary storage")
                        file_exists_in_secondary = secondary_file_dir.exists() and any(secondary_file_dir.iterdir())
                    else:
                        logging.error(f"Unexpected secondary directory type: {type(secondary_file_dir)}")
                    if file_exists_in_secondary:
                        logging.debug(f"File {file_id} already exists in secondary storage, skipping")
                        success_count += 1
                        continue

                # Download to temp directory
                assert isinstance(file_dir, Path)
                assert isinstance(self.temp_dir, Path)
                download = self.pyega3.download_file(file_id, self.temp_dir)
                if isinstance(download, Exception):
                    logging.error(f"Failed to download {file_id}: {download}")
                    continue


                err = move_dir_content(download, dataset_dir)
                if err:
                    logging.error(f"Failed to move {file_id}: {err}")
                    continue
                else:
                    logging.debug(f"Moved {file_id} successfully")
                    success_count += 1

                if self.storage.disk_usage_exceeded(dataset_id):
                    logging.debug("Disk usage exceeded, moving to secondary")
                    using_secondary = True
                    self.storage.move_to_secondary(dataset_id)
            if using_secondary:
                logging.info(f"Moving final batch of dataset {dataset_id} to secondary storage")
                self.storage.move_to_secondary(dataset_id)

            logging.debug(f"\nDataset {dataset_id} complete: {success_count}/{len(files)} files downloaded")
            return success_count == len(files)

        except Exception as e:
            logging.error(f"Error processing dataset {dataset_id}: {e}")
            return False



    def download_datasets(self, dataset_ids: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Download multiple datasets.

        Args:
            dataset_ids: List of dataset IDs to download (None = all authorized)

        Returns:
            Dict mapping dataset IDs to success status
        """
        # Get dataset list if not provided
        if dataset_ids is None:
            logging.debug("Fetching authorized datasets from pyega3...")
            dataset_ids = self.pyega3.get_datasets()
            logging.info(f"Found {len(dataset_ids)} authorized datasets")

        logging.debug(f"\n{self.storage.get_storage_summary()}\n")

        # Download each dataset
        results = {}
        for i, dataset_id in enumerate(dataset_ids, 1):
            logging.info(f"Dataset {i}/{len(dataset_ids)}")
            success = self.download_dataset(dataset_id)
            results[dataset_id] = success
            # Show storage summary after each dataset
            logging.debug(f"\n{self.storage.get_storage_summary()}")

        return results
