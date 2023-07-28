# --
# Here we want to find a way to store, query, and recreate a file structure
# base on chunks.
from srcs.parsers import BlockParser
from pathlib import Path


for chunk in BlockParser.Chunks(
    Path(__file__).parent.parent / "src/py/srcs/model/chunks.py"
):
    print(chunk)
