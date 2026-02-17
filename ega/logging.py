import logging
from typing import Dict, Tuple, Union, Literal

from ega.storage_manager import StorageManager


def setup_logging(log_file):
    log_handlers = [logging.StreamHandler()]
    if log_file:
        log_handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=log_handlers
    )


def log_results(results: Dict[str, bool]) -> Tuple[Union[int, Literal[0]], int]:
    logging.info("=" * 60)
    logging.info("DOWNLOAD SUMMARY")
    logging.info("=" * 60)
    success = sum(1 for v in results.values() if v)
    total = len(results)
    logging.info(f"Successful: {success}/{total}")
    logging.info(f"Failed: {total - success}/{total}")
    return success, total


def log_preamble(primary_dir: str, secondary: str, max_usage: Union[int, float], connections: int):
    logging.info("=" * 60)
    logging.info("EGA Dataset Download Manager")
    logging.info("=" * 60)
    logging.info(f"Primary directory: {primary_dir}")
    if secondary:
        logging.info(f"Secondary directory: {secondary}")
    logging.info(f"Max usage for primary: {max_usage} GB")
    logging.info(f"Connections: {connections}")
    logging.info("=" * 60)


def log_summary(results: Dict[str, bool], storage: StorageManager) -> bool:
    for dataset_id, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        logging.info(f"  {dataset_id}: {status}")
    logging.info(f"\n{storage.get_storage_summary()}")
    return
