#! /usr/bin/env python

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--write-path", type=Path, required=True)
args = parser.parse_args()

with args.write_path.open("w") as f:
    f.write("Hello")
