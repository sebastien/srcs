from typing import NamedTuple
from pathlib import Path
from enum import Enum
from srcs.utils.files import Files

# --
# What we want to do here is to represent a source tree as a set of chunks.


TPath = list[str]


# --
# ## File Attributes


class FilePermission(NamedTuple):
    read: bool
    write: bool
    execute: bool


class FilePermissions(NamedTuple):
    owner: FilePermission
    group: FilePermission
    other: FilePermission


class FileUser(NamedTuple):
    userId: int
    userName: str


class FileAttributes(NamedTuple):
    owner: FileUser
    group: FileUser
    permissions: FilePermissions
    createdTime: float
    updatedTime: float


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


class FileTree(NamedTuple):
    entry: FileEntry
    dirs: dict[str, FileEntry]
    files: dict[str, FileEntry]

    @staticmethod
    def Make(base: Path) -> "FileTree":
        for atom in Files.Walk(base):
            print(atom)


# --
#

if __name__ == "__main__":
    print(FileTree.Make(Path(".")))

# EOF
