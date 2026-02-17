from ..ega.validate import validate
from ..ega.parse import parse_args


def main():
    args = parse_args()
    validate(args)


if __name__ == "__main__":
    main()
