"""TI YZ0012-C01 lands, mask and paste for the TPD1S514 family."""
from pathlib import Path

NAME = "Texas_TPD1S514_YZ0012_1.99x1.29mm_P0.4mm"
LIB_ID = "ducktop2:" + NAME
SOURCE = "https://www.ti.com/lit/ds/symlink/tpd1s514.pdf"


def footprint():
    rows = [
        f'(footprint "{NAME}"',
        '  (version 20260206) (generator "pcbnew") (layer "F.Cu")',
        '  (descr "TI YZ0012-C01, drawing 4221703/A: 0.4mm pitch, 0.225mm NSMD copper, 0.30mm mask openings, 0.25mm rounded-square paste. Nominal 1.99x1.29mm body, 0.625mm maximum height.")',
        '  (tags "TPD1S514 YZ0012 DSBGA 0.4mm")',
        '  (property "Reference" "REF**" (at 0 -1.55) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
        f'  (property "Value" "{NAME}" (at 0 1.55) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))',
        '  (attr smd) (clearance 0.15)',
        '  (fp_line (start -0.995 -0.395) (end -0.745 -0.645) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
        '  (fp_line (start -0.745 -0.645) (end 0.995 -0.645) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
        '  (fp_line (start 0.995 -0.645) (end 0.995 0.645) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
        '  (fp_line (start 0.995 0.645) (end -0.995 0.645) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
        '  (fp_line (start -0.995 0.645) (end -0.995 -0.395) (stroke (width 0.1) (type solid)) (layer "F.Fab"))',
        '  (fp_line (start -1.1 -0.75) (end -0.55 -0.75) (stroke (width 0.1) (type solid)) (layer "F.SilkS"))',
        '  (fp_rect (start -1.3 -0.95) (end 1.3 0.95) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
    ]
    for row, y in zip("ABC", (-.4, 0, .4)):
        for col, x in enumerate((-.6, -.2, .2, .6), 1):
            rows.append(f'  (pad "{row}{col}" smd circle (at {x:g} {y:g}) (size 0.225 0.225) (property pad_prop_bga) (layers "F.Cu" "F.Mask") (solder_mask_margin 0.0375))')
            rows.append(f'  (pad "" smd roundrect (at {x:g} {y:g}) (size 0.25 0.25) (layers "F.Paste") (roundrect_rratio 0.2))')
    return "\n".join(rows + [")", ""])


if __name__ == "__main__":
    dest = Path(__file__).resolve().parents[1] / "ducktop2.pretty" / (NAME + ".kicad_mod")
    dest.write_text(footprint())
    print(dest)
