from typing import NamedTuple
from pathlib import Path
from enum import Enum
import grp, pwd, os, mimetypes
import magic
from srcs.utils.files import Files, isBinary

# --
# What we want to do here is to represent a source tree as a set of chunks.


TPath = list[str]


# --
# ## File Attributes


class FilePermission(NamedTuple):
    read: bool
    write: bool
    execute: bool

    @staticmethod
    def FromMode(mode: int) -> "FilePermission":
        # Extract the permission bits from the file mode (9-bit value)
        # The permission bits are in the following order: owner-group-other
        # Each set of 3 bits represents read-write-execute permissions.
        # 0b100 (4) = Read permission
        # 0b010 (2) = Write permission
        # 0b001 (1) = Execute permission
        # 0b000 (0) = No permission

        return FilePermission(bool(mode & 0o4), bool(mode & 0o2), bool(mode & 0o1))


class FilePermissions(NamedTuple):
    owner: FilePermission
    group: FilePermission
    other: FilePermission

    @classmethod
    def FromPath(cls, path: Path) -> "FilePermissions":
        return cls.FromMode(path.stat().st_mode)

    @staticmethod
    def FromMode(mode: int) -> "FilePermissions":
        # Get the file mode using the stat method
        return FilePermissions(
            owner=FilePermission.FromMode(mode >> 6),
            group=FilePermission.FromMode((mode >> 3) & 0o7),
            other=FilePermission.FromMode(mode & 0o7),
        )


class FileUser(NamedTuple):
    userId: int
    userName: str


class FileAttributes(NamedTuple):
    owner: FileUser
    group: FileUser
    permissions: FilePermissions
    createdTime: float
    updatedTime: float

    @staticmethod
    def FromPath(path: Path) -> "FileAttributes":
        stat = os.stat(path)
        return FileAttributes(
            owner=FileUser(
                userId=(uid := stat.st_uid), userName=pwd.getpwuid(uid).pw_name
            ),
            group=FileUser(
                userId=(gid := stat.st_gid), userName=grp.getgrgid(gid).gr_name
            ),
            permissions=FilePermissions.FromPath(path),
            createdTime=stat.st_ctime,
            updatedTime=stat.st_mtime,
        )


# --
# ## File Entries


class FilePath(NamedTuple):
    parent: TPath
    name: str


class FileType(Enum):
    File = "F"
    Dir = "D"
    Link = "L"


class FileEntry(NamedTuple):
    path: FilePath
    type: FileType
    ext: str
    mimeType: str
    attr: FileAttributes

    @staticmethod
    def Type(path: Path) -> FileType:
        if path.is_file():
            return FileType.File
        elif path.is_dir():
            return FileType.Dir
        elif path.is_symlink():
            return FileType.Link
        else:
            raise ValueError(f"Unsupported file type for path: {path}")

    @staticmethod
    def MimeType(path: Path) -> str:
        # Try to guess the MIME type using the file extension
        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type:
            return mime_type
        else:
            # If the file extension does not provide the MIME type, try to read the content.
            # Note: Install the `python-magic` library first using `pip install python-magic`.
            try:
                with magic.Magic() as magic_instance:
                    detected_mime_type = magic_instance.from_file(str(path))
                return detected_mime_type
            except magic.MagicException:
                return "application/octet-stream" if isBinary(path) else "text/plain"

    @classmethod
    def FromPath(cls, path: Path) -> "FileEntry":
        return FileEntry(
            path=FilePath(parent=list(map(str, path.parents)), name=path.name),
            type=cls.Type(path),
            ext=path.suffix,
            mimeType="",  # You may fill in the MIME type if available.
            attr=FileAttributes.FromPath(path),
        )


class FileTree(NamedTuple):
    entry: FileEntry
    dirs: dict[str, FileEntry]
    files: dict[str, FileEntry]


def fileEntry(path: Path) -> FileEntry:
    return FileEntry.FromPath(path)


def filePredicate(path: Path) -> bool:
    if path.name.startswith(".") or path.name.endswith(".pyc"):
        return False
    else:
        return True


def fileTree(base: Path) -> "FileTree":
    for atom in Files.Walk(base, predicate=filePredicate):
        print(fileEntry(atom))


# --
#

if __name__ == "__main__":
    print(fileTree(Path(".")))

# EOF
