from typing import Generator, Union, Optional, ContextManager
from pathlib import Path
from sys import getdefaultencoding
import os
import json
import tempfile
import shutil
import hashlib


ENCODING = getdefaultencoding()


def sha256sum(path: Union[Path, str], buffer=64_000) -> str:
    res = hashlib.sha256()
    with open(path, "rb") as file:
        for byte_block in iter(
            lambda: file.read(buffer), b""
        ):  # read and update hash string value in blocks of 4K
            res.update(byte_block)
        return res.hexdigest()


class mkdtemp(ContextManager):
    """Crates a temporary the given contents."""

    def __init__(self):
        super().__init__()
        self.path = Path(tempfile.mkdtemp(prefix="ss-", suffix=".cry"))

    def cleanup(self):
        if self.path and self.path.exists():
            shutil.rmtree(self.path)

    def __enter__(self):
        return self.path

    def __exit__(self, type, value, traceback):
        self.cleanup()


class mkstemp(ContextManager):
    """Crates a secure temporary file with the given contents."""

    def __init__(self, content: Optional[Union[str, bytes]] = None):
        super().__init__()
        self.content = content.encode(ENCODING) if isinstance(content, str) else content
        fd, path = tempfile.mkstemp(prefix="ss-", suffix=".cry")
        if content is not None:
            os.write(
                fd, bytes(content, "utf8") if isinstance(content, str) else content
            )
            os.close(fd)
        self.path: Path = Path(path)

    def __enter__(self):
        return self.path

    def __exit__(self, type, value, traceback):
        if self.path and self.path.exists():
            self.path.unlink()


# NOTE: This is borrowed and adapted from  <https://github.com/sebastien/sink>
class Files:
    """An abstraction of key operations involved in snapshotting filesystems"""

    @staticmethod
    def Write(path: Union[str, Path], content: Union[bytes, str, dict]) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb" if isinstance(content, bytes) else "wt") as f:
            if isinstance(content, str) or isinstance(content, bytes):
                f.write(content)
            else:
                json.dump(content, f)
        return p

    @staticmethod
    def Walk(
        path: Union[str, Path],
        followLinks: bool = False,
        includeDir: bool = False,
    ) -> Generator[Path, bool, None]:
        """Does a breadth-first walk of the filesystem, yielding non-directory
        paths that match the `accepts` and `rejects` filters."""
        queue: list[Path | str] = ["."]
        root = Path(path).absolute()
        while queue:
            local_path = queue.pop()
            abs_path = root / local_path
            # TODO: It may be better to use os.walk there...
            for name in os.listdir(abs_path):
                item_abs_path = abs_path / name
                item_rel_path = item_abs_path.relative_to(root)
                is_link = os.path.islink(item_abs_path)
                is_dir = item_abs_path.resolve().is_dir()
                if not (is_dir and includeDir is False):
                    continues = yield item_rel_path
                else:
                    continues = True
                if continues is False:
                    continue
                elif is_link and not followLinks:
                    pass
                elif is_dir:
                    queue.append(item_rel_path)


def isBinary(path: Path) -> bool:
    """Checks if the given path has binary contents or not"""
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            if b"\0" in chunk:
                return True
            if any(b < 0x09 or (0x0E <= b <= 0x1F) for b in chunk):
                return True
    return False


def dotfile(name: str, base: Optional[Path] = None) -> Optional[Path]:
    """Looks for the file `name` in the current directory or its ancestors"""
    user_home: Optional[str] = os.getenv("HOME")
    path = Path(base or ".").absolute()
    while path != path.parent:
        if (loc := path / name).exists():
            return loc
        if path != user_home:
            path = path.parent
        else:
            break
    return None


# EOF
