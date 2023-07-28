from pathlib import Path


def isBinary(path: Path) -> bool:
    """Checks if the given path has binary contents or not"""
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            if b"\0" in chunk:
                return True
            if any(b < 0x09 or (0x0E <= b <= 0x1F) for b in chunk):
                return True
    return False


# EOF
