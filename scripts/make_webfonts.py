#!/usr/bin/env python3
"""
Build webfonts from the finished TTFs.

Run last in the build, after post-build fixes and autohinting, so the
webfonts match the TTFs exactly (gftools builder's own webfonts are made
before those steps, so config.yaml sets `buildWebfont: false`).

  - fonts/webfonts/<name>.woff2 for every static and variable TTF
  - fonts/variable/<name>.woff and .woff2 next to each variable TTF

Usage: make_webfonts.py [fonts_dir]   (default: fonts)
"""
import glob
import os
import sys

from fontTools.ttLib import TTFont


def save_flavor(src, dst, flavor):
    # Keep the TTF's head.modified so the webfont matches its source exactly
    tt = TTFont(src, recalcTimestamp=False)
    tt.flavor = flavor
    tt.save(dst)
    print(f"  {dst}")


def main():
    fonts_dir = sys.argv[1] if len(sys.argv) > 1 else "fonts"
    webfonts_dir = os.path.join(fonts_dir, "webfonts")
    os.makedirs(webfonts_dir, exist_ok=True)

    statics = sorted(glob.glob(os.path.join(fonts_dir, "ttf", "*.ttf")))
    variables = sorted(glob.glob(os.path.join(fonts_dir, "variable", "*.ttf")))

    for src in statics + variables:
        base = os.path.splitext(os.path.basename(src))[0]
        save_flavor(src, os.path.join(webfonts_dir, base + ".woff2"), "woff2")

    for src in variables:
        stem = src[: -len(".ttf")]
        save_flavor(src, stem + ".woff", "woff")
        save_flavor(src, stem + ".woff2", "woff2")


if __name__ == "__main__":
    sys.exit(main())
