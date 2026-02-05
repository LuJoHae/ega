import logging
from typing import Tuple, Optional, List
from pathlib import Path
import subprocess
import shutil
import time


def get_uuids(uuid_file_path) -> List[str]:
    uuid_file_path = Path(uuid_file_path)
    if not uuid_file_path.exists():
        logging.error(f"UUID file not found at {uuid_file_path}")
        return []

    with open(uuid_file_path, 'r') as f:
        uuids = [line.strip() for line in f if line.strip()]

    if not uuids:
        logging.warning(f"No UUIDs found in {uuid_file_path}")
    return uuids


def delete_file(file_path: Path):
    """Delete a single file or directory"""
    if file_path.exists():
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        logging.info(f"Deleted {file_path}")


def download_file(uuid: str, credentials_file: Path, download_path: Path) -> Tuple[Optional[Path], Optional[Exception]]:
    """Download a file using pyega3 and return (path, error)."""
    start_time = time.time()
    logging.info(f"Downloading {uuid}")
    try:
        subprocess.run([
            "pyega3",
            "-cf", str(credentials_file),
            "-c", str(20),
            "fetch",
            uuid,
            "--output-dir", str(download_path)
        ], check=True, capture_output=True, text=True)
        elapsed_time = time.time() - start_time
        logging.info(f"download_file completed in {elapsed_time:.2f} seconds")
        return download_path / uuid, None
    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        logging.info(f"download_file completed in {elapsed_time:.2f} seconds")
        return None, e


def copy_to_eiger(file_path: Path, remote_path: Path):
    """Copy a file or directory to eiger remote"""
    start_time = time.time()
    logging.info(f"Pushing file {file_path.name} to eiger")

    # Make directory on remote at remote_path
    try:
        subprocess.run([
            "ssh",
            "eiger",
            "mkdir",
            "-p",
            str(remote_path)
        ], check=True, capture_output=True, text=True)
        logging.info(f"Created remote directory {remote_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error creating remote directory {remote_path}: {e}")
        return

    if file_path.is_dir():
        try:
            logging.info(f"Copying directory {file_path} to eiger remote")
            subprocess.run([
                "scp",
                "-r",
                str(file_path),
                f"eiger:{remote_path}/{file_path.name}"
            ], check=True, capture_output=True, text=True)
            logging.info(f"Successfully copied {file_path} to eiger")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error copying {file_path} to eiger: {e}")

    elapsed_time = time.time() - start_time
    logging.info(f"copy_to_eiger completed in {elapsed_time:.2f} seconds")


def main(
        tsv_file_path,
        remote_path,
        download_dir="downloads",
        credentials_file="./secrets/credentials.json"
):
    """
    Read TSV file, extract UUIDs from specified column, and download files one by one.

    Args:
        tsv_file_path: Path to the TSV file
        remote_path: Path on the remote to copy files to
        download_dir: Directory to download files to (default: "downloads")
        credentials_file: Path to credentials file
    """
    credentials_path = Path(credentials_file)
    if not credentials_path.exists():
        logging.error(f"Credentials file not found at {credentials_path}")
        credentials_path = None

    uuids = get_uuids(tsv_file_path)

    # Create download directory
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)

    # Process files one by one
    for i, uuid in enumerate(uuids, 1):
        logging.info(f"Processing file {i}/{len(uuids)}: {uuid}")

        # Download file
        file_path, err = download_file(uuid, credentials_path, download_path)
        if err:
            logging.warning(f"Error downloading {uuid}: {err}")
            continue

        if not file_path:
            continue

        # Copy to eiger
        copy_to_eiger(file_path=file_path, remote_path=remote_path)

        # Delete local file after copying
        delete_file(file_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    # Example usage - update these parameters as needed
    main(
        tsv_file_path="data/EGAD00001006632.txt",
        remote_path="/capstor/scratch/cscs/lhaeuser/EGAD00001006632"
    )
