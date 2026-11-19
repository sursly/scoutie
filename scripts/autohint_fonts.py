#!/usr/bin/env python3
"""
Autohint static TTFs with ttfautohint, using our own options.

gftools builder runs ttfautohint with its defaults and has no setting for
passing options, so config.yaml sets `autohintTTF: false` and the Makefile
runs this script on the finished static TTFs instead.

Usage:
  autohint_fonts.py [--args "TTFAUTOHINT OPTIONS"] font.ttf [font2.ttf ...]

Options go straight to ttfautohint (same flags as the ttfautohint CLI), e.g.
  --args "-x 0 -a qsq"
A control file can be passed the same way: --args "-x 0 -m sources/ctrl.txt".

gftools adds a minimal `prep`/`gasp` to unhinted fonts; those are removed
first so ttfautohint gets a clean, unhinted input. Fonts are hinted in place.
"""
import argparse
import os
import shlex
import sys
import tempfile

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import ttProgram
from ttfautohint import ttfautohint
from ttfautohint.options import parse_args as ttfautohint_parse_args

HINTING_TABLES = ("fpgm", "prep", "cvt ", "gasp", "hdmx", "LTSH", "VDMX", "TTFA")


def strip_hinting(path, out_path):
    tt = TTFont(path)
    for tag in HINTING_TABLES:
        if tag in tt:
            del tt[tag]
    glyf = tt["glyf"]
    for name in tt.getGlyphOrder():
        glyph = glyf[name]
        if glyph.numberOfContours != 0 and hasattr(glyph, "program"):
            program = ttProgram.Program()
            program.fromBytecode(b"")
            glyph.program = program
    tt.save(out_path)


def autohint(path, ttfa_args):
    with tempfile.TemporaryDirectory() as tmp:
        clean = os.path.join(tmp, "unhinted.ttf")
        strip_hinting(path, clean)
        options = ttfautohint_parse_args([clean, path, *ttfa_args])
        if not options:
            raise SystemExit(f"Could not parse ttfautohint options: {ttfa_args}")
        ttfautohint(**options)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--args", default="", help="options passed to ttfautohint")
    parser.add_argument("fonts", nargs="+")
    args = parser.parse_args()
    ttfa_args = shlex.split(args.args)
    for path in args.fonts:
        print(f"Autohinting {path} {' '.join(ttfa_args)}".rstrip())
        autohint(path, ttfa_args)


if __name__ == "__main__":
    sys.exit(main())
