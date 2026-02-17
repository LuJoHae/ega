import argparse
from pathlib import Path

DEFAULT_MAX_DISK_USAGE_GB = 100
DEFAULT_CONNECTIONS = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download EGA datasets with intelligent multi-directory storage management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all datasets to primary directory
  python download.py /data/ega -cf credentials.json

  # Download specific datasets to primary directory
  python download.py /data/ega -cf credentials.json -d EGAD00001006630 EGAD00001006631

  # Download to primary and move completed datasets to remote secondary
  python download.py /data/ega -cf credentials.json --secondary user@server:/archive/ega

  # Download to primary and move to local secondary
  python download.py /tmp/ega -cf credentials.json --secondary /archive/ega --max-usage 1

  # Download with custom temp directory
  python download.py /data/ega -cf credentials.json --temp-dir /fast/temp
"""
    )

    parser.add_argument(
        "primary_dir",
        type=Path,
        help="Primary directory for downloads (local directory)"
    )
    parser.add_argument(
        "--secondary",
        type=str,
        help="Optional secondary directory for completed datasets. "
             "Can be local path or remote (user@host:/path)"
    )
    parser.add_argument(
        "-cf", "--credentials-file",
        type=Path,
        help="Path to pyega3 credentials file (JSON format)"
    )
    parser.add_argument(
        "-d", "--datasets",
        nargs="+",
        help="Specific dataset IDs to download (default: all authorized datasets)"
    )
    parser.add_argument(
        "--max-usage",
        type=float,
        default=DEFAULT_MAX_DISK_USAGE_GB,
        help=f"Maximum disk usage for primary directory in GB (default: {DEFAULT_MAX_DISK_USAGE_GB})"
    )
    parser.add_argument(
        "--connections",
        type=int,
        default=DEFAULT_CONNECTIONS,
        help=f"Number of parallel connections for downloads (default: {DEFAULT_CONNECTIONS})"
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        help="Temporary directory for downloads (default: /tmp/ega_downloads)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file (default: stdout only)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Create test files instead of downloading actual data"
    )
    parser.add_argument(
        "--verify-md5",
        action="store_true",
        help="Verify MD5 checksums (slower)"
    )

    args = parser.parse_args()
    return args
