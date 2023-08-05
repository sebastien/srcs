from typing import NamedTuple, Optional, TypeVar
from enum import Enum
from pathlib import Path
from hashlib import sha512
import os

T = TypeVar("T")

# --
# # Chunks
#
# The idea that we're exploring here is to create a version control system
# that is focused on code. The assumption is that a program is a tree defining
# symbols. VCS like git or mercurial primarily work on text files, and do not
# have a notion of the overall program structure.
#
# Obviously, working with text files in general, as well as binary files
# is a baseline requirement for a VCS, but using a more structured representation
# of a subset of files may have the potential of simplifying the design,
# implementation and operation of a VCS.

# --
# ## Positions
#
# We introduce the notion of _position_ that can point to a specific part
# of a file, or a specific part of a semantic representation of a program
# (ie. a symbol).
class Position(NamedTuple):
    """Represents a position in a binary data."""

    offset: int


class TextPosition(NamedTuple):
    """Represents a position in  a binary data, extended with line and
    column information."""

    offset: int
    line: Optional[int] = None
    column: Optional[int] = None


# --
# ## Ranges
#
# For text and binary data, we introduce the notion of _range_ that delimits
# a start and an end.


class Range(NamedTuple):
    """A range in an asset"""

    start: Position | TextPosition
    end: Position | TextPosition


# --
# ## Chunks
#
# We consider that a project is made out of chunks. Chunks are bits of
# data (binary or text) that are at a specific location. Chunks can be
# combined into symbols. which represents the semantic components of a
# program.


class Location(NamedTuple):
    path: tuple[str, ...]

    @staticmethod
    def Get(path: Path, base: Path) -> "Location":
        """Creates a location object from a local path and a base."""
        return Location(path.resolve().relative_to(base.resolve()).parts)

    @staticmethod
    def Path(location: "Location", base: Path = Path.cwd()) -> Path:
        return base / "/".join(location.path)


class HashType(Enum):
    SHA512 = 1


class Signature(NamedTuple):
    hashtype: int
    hash: bytes


def signatureFromFile(
    path: Path, start: Optional[int] = None, end: Optional[int] = None
) -> "Signature":
    """Returns the SHA512 signature for the file at the given path, optionally taking
    offsets to calculate the signature of a subset"""
    h = sha512()
    with path.open("rb") as file:
        if start:
            file.seek(start)
        if end is None:
            for chunk in iter(lambda: file.read(1024), b""):
                h.update(chunk)
        else:
            to_read = end - (start or 0)
            while to_read > 0:
                chunk = file.read(min(1024, to_read))
                h.update(chunk)
                to_read -= len(chunk)
    return Signature(HashType.SHA512.value, h.digest())


class Chunk(NamedTuple):
    location: Location
    range: Range
    signature: Signature

    @staticmethod
    def Read(chunk: "Chunk", path: Path = Path.cwd()) -> bytes:
        fd = os.open(str(Location.Path(chunk.location, path)), os.O_RDONLY)
        os.lseek(fd, chunk.range.start.offset, 0)
        data = os.read(fd, chunk.range.end.offset - chunk.range.start.offset)
        os.close(fd)
        return data


# --
# ## Catalogue
#
# The next step is to create a catalogue of chunks. We can imagine a smart
# cataloguer that would use something like `ctypes` or TreeSitter to build
# a catalogue of chunks with semantic information. For now, we're going
# to take a simple approach:
#
# - Binary files are considered a whole chunk
# - Text files chunks are separated by one or more empty new lines.


# EOF
