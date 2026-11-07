"""Replace lowercase 'l' in Hurmit Nerd Font with Liberation Mono's 'l'.

Reads the Arch-packaged originals (otf-hermit-nerd, ttf-liberation) and writes
a custom family ("Hurmit Nerd Font Custom") so the packaged font is untouched.
"""
import argparse
import math
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

SRC_DIR = Path("/usr/share/fonts/OTF")
LIB_DIR = Path("/usr/share/fonts/liberation")
REPO_DIR = Path(__file__).resolve().parent.parent

FAMILY_OLD = "Hurmit Nerd Font"
FAMILY_NEW = "Hurmit Nerd Font Custom"
PS_OLD = "HurmitNF"
PS_NEW = "HurmitNFCustom"

# style -> (hurmit file, liberation file, italic angle in degrees)
STYLES = {
    "Regular": ("HurmitNerdFont-Regular.otf", "LiberationMono-Regular.ttf", 0.0),
    "Bold": ("HurmitNerdFont-Bold.otf", "LiberationMono-Bold.ttf", 0.0),
    "Italic": ("HurmitNerdFont-Italic.otf", "LiberationMono-Regular.ttf", 10.0),
    "BoldItalic": ("HurmitNerdFont-BoldItalic.otf", "LiberationMono-Bold.ttf", 10.0),
}


def transformed_bounds(glyph, glyphset, matrix):
    bp = BoundsPen(glyphset)
    glyph.draw(TransformPen(bp, matrix))
    return bp.bounds


def patch(style, hurmit_file, lib_file, italic_angle, out_dir):
    dst = TTFont(SRC_DIR / hurmit_file)
    src = TTFont(LIB_DIR / lib_file)
    src_gs = src.getGlyphSet()
    src_glyph = src_gs["l"]

    dst_top = dst["CFF "].cff.topDictIndex[0]
    cell = dst["hmtx"]["l"][0]

    # Ascender height from the destination 'h' so the new 'l' matches it.
    bp = BoundsPen(dst.getGlyphSet())
    dst.getGlyphSet()["h"].draw(bp)
    target_top = bp.bounds[3]

    src_bp = BoundsPen(src_gs)
    src_glyph.draw(src_bp)
    _, src_bottom, _, src_top = src_bp.bounds

    s = target_top / (src_top - src_bottom)
    shear = math.tan(math.radians(italic_angle))

    # Shear around the baseline: x' = x + y*tan(angle), then center in the cell.
    sheared = (s, 0, shear * s, s, 0, 0)
    b = transformed_bounds(src_glyph, src_gs, sheared)
    dx = (cell - (b[2] - b[0])) / 2.0 - b[0]
    matrix = (s, 0, shear * s, s, dx, 0)

    pen = T2CharStringPen(cell, None)
    src_glyph.draw(TransformPen(Qu2CuPen(pen, max_err=0.5, all_cubic=True), matrix))
    dst_top.CharStrings["l"] = pen.getCharString(private=dst_top.Private)

    # Rename the family so it does not collide with the packaged font.
    full_new = (
        FAMILY_NEW
        if style == "Regular"
        else f"{FAMILY_NEW} {style.replace('BoldItalic', 'Bold Italic')}"
    )
    ps_new = PS_NEW if style == "Regular" else f"{PS_NEW}-{style}"
    for rec in list(dst["name"].names):
        try:
            old = rec.toUnicode()
        except Exception:
            continue
        new = old.replace(FAMILY_OLD, FAMILY_NEW).replace(PS_OLD, PS_NEW)
        if new != old:
            dst["name"].setName(new, rec.nameID, rec.platformID, rec.platEncID, rec.langID)

    dst_top.FamilyName = FAMILY_NEW
    dst_top.FullName = full_new
    dst["CFF "].cff.fontNames[0] = ps_new

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{PS_NEW}-{style}.otf"
    dst.save(out)
    print(f"wrote {out}")
    dst.close()
    src.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_DIR / "fonts",
        help="output directory (default: ./fonts)",
    )
    args = parser.parse_args()

    for style, (hurmit, liberation, angle) in STYLES.items():
        patch(style, hurmit, liberation, angle, args.out)


if __name__ == "__main__":
    main()
