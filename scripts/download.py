from ega.parse import parse_args
from ega.download import download


def main():
    args = parse_args()
    download(
        args.datasets,
        args.primary_dir,
        args.secondary,
        args.max_usage,
        args.credentials_file,
        args.log_file,
        args.connections,
        args.temp_dir,
        args.dry_run
    )


if __name__ == "__main__":
    main()
