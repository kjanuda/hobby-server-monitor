import re


SIZE_UNITS = {
    "B": 1,
    "KB": 1000,
    "MB": 1000 ** 2,
    "GB": 1000 ** 3,
    "TB": 1000 ** 4,
    "KIB": 1024,
    "MIB": 1024 ** 2,
    "GIB": 1024 ** 3,
    "TIB": 1024 ** 4,
}


def parse_size_to_bytes(value):
    if isinstance(value, int):
        if value < 0:
            raise ValueError("Size cannot be negative.")
        return value

    if not isinstance(value, str):
        raise ValueError("Size must be a string or integer.")

    value = value.strip().upper()

    match = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*([KMGT]?I?B)",
        value,
    )

    if not match:
        raise ValueError(
            f"Invalid size value: {value}"
        )

    number = float(match.group(1))
    unit = match.group(2)

    return int(
        number * SIZE_UNITS[unit]
    )


def bytes_to_lxd_size(value):
    if not isinstance(value, int) or value <= 0:
        raise ValueError(
            "Size must be a positive integer."
        )

    return f"{value}B"