#!/usr/bin/env python3
"""
P1.3 pass 2: Relocate remaining misplaced components.
Item 1: C502/C503 (PCIe TX AC caps) near A1 (Mu socket)
Item 2: Remaining BQ25798 caps (C700/C701/C704/C706)
        Remaining TPS552892 caps (C752/C756/C757/C759)
"""
import re

PCB_FILE = 'ducktop2.kicad_pcb'

# Plan: ref -> (new_x, new_y)
# Item 1: C502/C503 PCIe TX caps near A1 Mu socket (105.2, 143.75)
# Currently ~20mm, need <8mm per Mu guide
plan = {
    'C502': (111.0, 145.0),   # 6mm from A1
    'C503': (109.0, 145.0),   # 4mm from A1
    # Item 2: remaining BQ25798 caps near U2 (68.10, 135.90)
    'C700': (72.0, 139.0),    # 5mm from U2 (0402)
    'C701': (69.0, 141.0),    # 5mm from U2 (1206)
    'C704': (61.0, 139.0),    # 8mm from U2 (1206)
    'C706': (71.0, 141.0),    # 6mm from U2 (1206)
    # Item 2: remaining TPS552892 caps near U750 (157.25, 81.00)
    'C752': (148.0, 84.0),    # 10mm from U750 (1206)
    'C756': (148.0, 82.0),    # 9mm from U750 (0402)
    'C757': (154.0, 87.0),    # 7mm from U750 (0402)
    'C759': (165.0, 84.0),    # 8mm from U750 (1206)
}

def main():
    with open(PCB_FILE, encoding='latin-1') as f:
        content = f.read()

    modified = 0
    for ref, (new_x, new_y) in plan.items():
        for m in re.finditer(rf'\(property\s+"Reference"\s+"{ref}"', content):
            fp_start = content.rfind('(footprint', 0, m.start())
            if fp_start == -1:
                continue
            prefix = content[fp_start:m.start()]
            at_m = re.search(r'\(at\s+([\d.]+)\s+([\d.]+)(\s+[\d.-]+)?\)', prefix)
            if not at_m:
                continue

            old_at = at_m.group(0)
            rot_part = at_m.group(3) or ''
            new_at = f'(at {new_x:.2f} {new_y:.2f}{rot_part})' if rot_part else f'(at {new_x:.2f} {new_y:.2f})'

            abs_start = fp_start + at_m.start()
            abs_end = fp_start + at_m.end()
            old_x = float(at_m.group(1))
            old_y = float(at_m.group(2))

            content = content[:abs_start] + new_at + content[abs_end:]
            print(f'{ref}: ({old_x:.1f}, {old_y:.1f}) -> ({new_x:.1f}, {new_y:.1f})')
            modified += 1
            break
        else:
            print(f'{ref}: NOT FOUND')

    if modified:
        with open(PCB_FILE, 'w', encoding='latin-1') as f:
            f.write(content)
        print(f'\nModified {modified} components.')

if __name__ == '__main__':
    main()
