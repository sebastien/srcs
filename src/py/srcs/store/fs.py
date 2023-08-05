# --
# Here we want to find a way to store, query, and recreate a file structure
# base on chunks.
from typing import Iterator, Type
from srcs.model import Chunk
from srcs.parsers import BlockParser
from srcs.utils.ids import strchunks
from srcs.utils.files import Files
from pathlib import Path
from math import ceil
import os
import base64


TKey = list[str]


# --
# The ChunkStore stores chunks organised by signature. This is the physical
# view of the repository. Now these chunks need to be assembled in a
# logical view of the project: chunks assembled in files, and then
# symbols mapped to files.


class ChunkStore:
    def __init__(self, path: Path | str):
        self.root = (Path(path) if isinstance(path, str) else path).absolute()

    def put(self, chunk: Chunk):
        path = self.path(chunk)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.save(chunk, path=self.path(chunk))
        pass

    def key(self, chunk: Chunk) -> TKey:
        return strchunks(self.encodeSignature(chunk.signature.hash))

    def path(self, chunk: Chunk) -> Path:
        return self.root / f"{('/'.join(self.key(chunk)))}.chunk"

    def list(self) -> Iterator[tuple[Type[Chunk], bytes]]:
        for path in Files.Walk(self.root):
            if path.name.endswith(".chunk"):
                key = [_ for _ in path._parts]
                key[-1] = key[-1].rstrip(".chunk")
                yield (Chunk, self.decodeSignature("".join(key)))

    # TODO: Load/Save should be orthogonal, I think we should probably have
    # an LZMA option?
    def load(
        self, chunk: Chunk, cwd: Path = Path.cwd(), *, path: Path | None = None
    ) -> bytes:
        fd = os.open(
            str(path or (cwd / "/".join(chunk.location.path))), os.O_RDONLY | os.O_RSYNC
        )
        os.lseek(fd, chunk.range.start.offset, os.SEEK_SET)
        data = os.read(fd, chunk.range.end.offset - chunk.range.start.offset)
        os.close(fd)
        return data

    def save(self, chunk: Chunk, *, path: Path | None = None) -> bool:
        # We try a direct write so that we ensure it's committed properly
        fd = os.open(
            str(path or self.path(chunk)), os.O_WRONLY | os.O_CREAT | os.O_SYNC
        )
        os.write(fd, self.load(chunk))
        os.close(fd)
        return True

    def encodeSignature(self, data: bytes) -> str:
        return str(base64.b32encode(data), "ascii")

    def decodeSignature(self, data: str) -> bytes:
        return base64.b32decode(data)


# EOF
