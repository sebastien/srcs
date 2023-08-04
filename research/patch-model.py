from typing import NamedTuple, Optional, Generic, TypeVar, Iterator
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha512
from uuid import uuid4
import re, os

T = TypeVar("T")

# --
# # Simple Structured Version Control
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


class Symbol(NamedTuple):
    name: list[str]


class HashType(Enum):
    SHA512 = 1


class Signature(NamedTuple):
    hashtype: int
    signature: bytes


@dataclass
class Chunk:
    location: Location
    scope: Symbol
    range: Range
    signature: Signature


# class MetaData:
#     location: Location
#     attributes: dict[str, bool | int | float | str]


# --
# ## Changes
#
# We're going to leave the task of cataloguing the chunks for later. Instead,
# let's focus on defining operations that determine what we do with the chunk.


@dataclass
class ChunkContext:
    next: Optional[Chunk]
    previous: Optional[Chunk]


@dataclass
class Create(Generic[T]):
    data: T
    chunk: Chunk
    context: ChunkContext


@dataclass
class Delete:
    chunk: Chunk
    context: ChunkContext


@dataclass
class Update(Generic[T]):
    data: T
    chunk: Chunk
    origin: Chunk
    context: ChunkContext


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


def isBinary(path: Path) -> bool:
    """Checks if the given path has binary contents or not"""
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            if b"\0" in chunk:
                return True
            if any(b < 0x09 or (0x0E <= b <= 0x1F) for b in chunk):
                return True
    return False


def signature(
    path: Path, start: Optional[int] = None, end: Optional[int] = None
) -> Signature:
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


def makeID() -> str:
    """Wrapper function to generate a UUID string identifier suitable"""
    return str(uuid4())


def isEmptyContent(chunk: bytes) -> bool:
    """Tells if the chunk only has empty content."""
    return all(c in (b" ", b"\n", b"\t") for c in chunk)


def getLocation(path: Path, base: Path) -> Location:
    """Creates a location object from a local path and a base."""
    return Location(path.resolve().relative_to(base.resolve()).parts)


# NOTE: We probably want to implement per-file-format chunk iterator. We
# should have simple ones like this one, then use ctypes, then use tree
# sitter, then use AST like `python.ast`.
RE_SEPARATOR_BYTES = re.compile(b"\r?\n([\t ]*\r?\n)+")


def iterChunks(path: Path, base: Path = Path.cwd()) -> Iterator[Chunk]:
    """Iterates on the chunks available at the given `path`. This is typically
    what would be specialized with specific parsers to extract the structure."""
    loc = getLocation(path, base)
    sym = Symbol([makeID()])
    if isBinary(path):
        yield Chunk(
            location=loc,
            scope=sym,
            range=Range(Position(0), Position(path.stat().st_size)),
            signature=signature(path),
        )
    else:
        offset: int = 0
        line: int = 0
        column: int = 0

        def makeChunk(
            offset: int, line: int, column: int, text: bytes
        ) -> tuple[Chunk, int, int, int]:
            n: int = len(text)
            l: int = line + text.count(b"\n")
            c: int = len(text) - max(0, text.rfind(b"\n"))
            o: int = offset + n
            return (
                Chunk(
                    location=loc,
                    scope=Symbol([makeID()]),
                    range=Range(
                        TextPosition(offset, line, column),
                        TextPosition(o, l, c),
                    ),
                    signature=signature(path, offset, o),
                ),
                o,
                l,
                c,
            )

        with open(path, "rb") as f:
            for match in RE_SEPARATOR_BYTES.finditer(text := f.read()):
                # We generate the previous chunk
                if (o := match.start()) > offset:
                    chunk, offset, line, column = makeChunk(
                        offset, line, column, text[offset:o]
                    )
                    yield chunk
                    assert offset == o
                chunk, offset, line, column = makeChunk(
                    offset, line, column, text[o : match.end()]
                )
                assert offset == match.end()
                yield chunk
            if offset < len(text):
                chunk, offset, line, column = makeChunk(
                    offset, line, column, text[offset:]
                )
                yield chunk


def loadChunk(chunk: Chunk) -> bytes:
    fd = os.open("/".join(chunk.location.path), os.O_RDONLY)
    os.lseek(fd, chunk.range.start.offset, os.SEEK_SET)
    data = os.read(fd, chunk.range.end.offset - chunk.range.start.offset)
    os.close(fd)
    return data


# We iterate on the chunks on this specific file, and we make sure we got
# the whole thing right.
chunks: list[bytes] = []
for chunk in iterChunks(path := Path(__file__)):
    print(chunk)
    data = loadChunk(chunk)
    print("-->", data)
    chunks.append(data)
assert path.read_bytes() == b"".join(chunks)

# EOF
