#!/usr/bin/env python3
"""
Post-build fixes for Google Fonts compliance.
Fixes issues that can't be handled in config.yaml or the glyphs source:
  - usWinAscent/Descent must cover the full glyph bounding box
  - nbsp advance width must match space
  - Copyright string format (removes "All rights reserved." and stray © placement)
"""
import re
import sys
from fontTools.ttLib import TTFont


def get_glyph_extents(tt):
    ymax, ymin = 0, 0
    glyf = tt.get("glyf")
    if not glyf:
        return ymax, ymin
    for name in tt.getGlyphOrder():
        try:
            g = glyf[name]
            if hasattr(g, "yMax") and g.yMax is not None:
                ymax = max(ymax, g.yMax)
            if hasattr(g, "yMin") and g.yMin is not None:
                ymin = min(ymin, g.yMin)
        except Exception:
            pass
    return ymax, ymin


def fix_win_metrics(tt):
    ymax, ymin = get_glyph_extents(tt)
    os2 = tt["OS/2"]
    changed = False
    if os2.usWinAscent != ymax:
        print(f"  usWinAscent: {os2.usWinAscent} → {ymax}")
        os2.usWinAscent = ymax
        changed = True
    if os2.usWinDescent != abs(ymin):
        print(f"  usWinDescent: {os2.usWinDescent} → {abs(ymin)}")
        os2.usWinDescent = abs(ymin)
        changed = True
    return changed


def fix_vertical_metrics(tt):
    # GF requires hhea.ascender + abs(hhea.descender) + lineGap >= 2400.
    # Align hhea and sTypo to the win metrics (which already cover actual glyph extents).
    os2 = tt["OS/2"]
    hhea = tt["hhea"]
    changed = False
    target_asc = os2.usWinAscent
    target_desc = -os2.usWinDescent
    for attr, current, target in [
        ("sTypoAscender", os2.sTypoAscender, target_asc),
        ("sTypoDescender", os2.sTypoDescender, target_desc),
        ("sTypoLineGap", os2.sTypoLineGap, 0),
    ]:
        if getattr(os2, attr) != target:
            print(f"  OS/2.{attr}: {getattr(os2, attr)} → {target}")
            setattr(os2, attr, target)
            changed = True
    for attr, current, target in [
        ("ascent", hhea.ascent, target_asc),
        ("descent", hhea.descent, target_desc),
        ("lineGap", hhea.lineGap, 0),
    ]:
        if getattr(hhea, attr) != target:
            print(f"  hhea.{attr}: {getattr(hhea, attr)} → {target}")
            setattr(hhea, attr, target)
            changed = True
    return changed


def fix_nbsp_width(tt):
    cmap = tt.getBestCmap()
    hmtx = tt["hmtx"]
    space_gn = cmap.get(0x0020)
    nbsp_gn = cmap.get(0x00A0)
    if not (space_gn and nbsp_gn):
        return False
    space_width = hmtx[space_gn][0]
    if hmtx[nbsp_gn][0] == space_width:
        return False
    print(f"  nbsp width: {hmtx[nbsp_gn][0]} → {space_width}")
    hmtx[nbsp_gn] = (space_width, hmtx[nbsp_gn][1])
    return True


def fix_copyright(tt):
    changed = False
    for record in tt["name"].names:
        if record.nameID != 0:
            continue
        original = record.toUnicode()
        fixed = original
        # Remove "All rights reserved." (OFL doesn't require it and GF flags it)
        fixed = re.sub(r"\s*All rights reserved\.?", "", fixed, flags=re.IGNORECASE)
        # Move stray © symbol: "Copyright © YEAR" → "Copyright YEAR"
        fixed = re.sub(r"Copyright\s+©\s+", "Copyright ", fixed)
        # Remove any leftover bare ©
        fixed = fixed.replace("©", "").strip()
        # Collapse multiple spaces
        fixed = re.sub(r"  +", " ", fixed)
        if fixed != original:
            print(f"  copyright: {original!r}")
            print(f"          → {fixed!r}")
            encoded = fixed.encode("utf-16-be") if record.isUnicode() else fixed.encode("latin-1", errors="replace")
            record.string = encoded
            changed = True
    return changed


def fix_font(path):
    print(f"Processing {path}")
    tt = TTFont(path)
    any_changed = False
    any_changed |= fix_win_metrics(tt)
    any_changed |= fix_vertical_metrics(tt)
    any_changed |= fix_nbsp_width(tt)
    any_changed |= fix_copyright(tt)
    if any_changed:
        tt.save(path)
        print(f"  Saved.")
    else:
        print(f"  No changes needed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} font.ttf [font2.ttf ...]")
        sys.exit(1)
    for path in sys.argv[1:]:
        fix_font(path)
