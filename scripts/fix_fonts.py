#!/usr/bin/env python3
"""
Post-build fixes for Google Fonts compliance.
Fixes issues that can't be set in the Glyphs source or config.yaml:
  - nbsp advance width must match space
  - Copyright string format (removes "All rights reserved." and stray © placement)
  - Inject identity avar table (fontmake skips it when mappings are linear)
  - Restore fvar named instances for non-GF weights in STAT (e.g. Book 350)

Vertical metrics and win metrics are set via Custom Parameters in the Glyphs
source files directly — no post-processing needed for those.
"""
import re
import sys
from fontTools.ttLib import TTFont


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


def add_avar_table(tt):
    # fontmake skips generating avar when mappings are linear/identity.
    # Inject a minimal identity avar so the mandatory_avar_table check passes.
    if "avar" in tt:
        return False
    from fontTools.ttLib import newTable
    avar = newTable("avar")
    avar.version = (1, 0)
    # Build identity segment for each axis: {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}
    fvar = tt.get("fvar")
    if not fvar:
        return False
    avar.segments = {
        axis.axisTag: {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}
        for axis in fvar.axes
    }
    tt["avar"] = avar
    print(f"  avar: added identity table for axes: {list(avar.segments.keys())}")
    return True


def add_missing_fvar_instances(tt):
    # gftools' fix step rewrites fvar instances to the Google Fonts standard
    # weights, dropping non-standard ones (e.g. Book 350). Add back a named
    # instance for every STAT weight value (from config.yaml) that lacks one.
    if "fvar" not in tt or "STAT" not in tt:
        return False
    fvar, name = tt["fvar"], tt["name"]
    axes = {a.axisTag: a for a in fvar.axes}
    if "wght" not in axes or not fvar.instances:
        return False
    stat = tt["STAT"].table
    if not stat.AxisValueArray:
        return False
    wght_index = [a.AxisTag for a in stat.DesignAxisRecord.Axis].index("wght")
    is_italic = bool(tt["head"].macStyle & 2)
    existing = {inst.coordinates["wght"] for inst in fvar.instances}
    ps_prefix = name.getDebugName(fvar.instances[0].postscriptNameID).split("-")[0]
    template = fvar.instances[0]

    added = []
    for av in stat.AxisValueArray.AxisValue:
        if av.Format not in (1, 3) or av.AxisIndex != wght_index:
            continue
        if av.Value in existing:
            continue
        if not axes["wght"].minValue <= av.Value <= axes["wght"].maxValue:
            continue
        weight = name.getDebugName(av.ValueNameID)
        style = f"{weight} Italic" if is_italic else weight
        inst = type(template)()
        inst.coordinates = {**template.coordinates, "wght": av.Value}
        inst.flags = 0
        inst.subfamilyNameID = name.addMultilingualName(
            {"en": style}, windows=True, mac=False, minNameID=256
        )
        inst.postscriptNameID = name.addMultilingualName(
            {"en": f"{ps_prefix}-{style.replace(' ', '')}"},
            windows=True, mac=False, minNameID=256,
        )
        fvar.instances.append(inst)
        existing.add(av.Value)
        added.append(f"{style} ({av.Value:g})")

    if not added:
        return False
    fvar.instances.sort(key=lambda i: i.coordinates["wght"])
    print(f"  fvar: added instances {', '.join(added)}")
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
    any_changed |= fix_nbsp_width(tt)
    any_changed |= fix_copyright(tt)
    any_changed |= add_avar_table(tt)
    any_changed |= add_missing_fvar_instances(tt)
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
