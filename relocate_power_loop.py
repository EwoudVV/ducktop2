#!/usr/bin/env python3
"""
P1.3: Relocate critically-placed power loop components closer to their ICs.
Moves only components flagged in the independent review as being >20mm from their parent IC.
"""
import re
import shutil

PCB_FILE = 'ducktop2.kicad_pcb'
BACKUP_FILE = 'ducktop2.kicad_pcb.p1.3_backup'

# --- Define all moves ---
# Each entry: (ref, new_x, new_y) — rotation preserved from original
# Coordinates in mm

# U2 (BQ25798) at (68.10, 135.90) — 4x4mm VQFN
# PMID caps C702/C705/C707/C709 currently at y≈182 (48mm away)
# Place them in a row to the left of U2 where space is clear
U2_X, U2_Y = 68.10, 135.90
u2_moves = [
    ('C702', U2_X - 5.5, U2_Y - 3.0),
    ('C705', U2_X - 5.5, U2_Y - 5.0),
    ('C707', U2_X - 5.5, U2_Y - 7.0),
    ('C709', U2_X - 5.5, U2_Y - 9.0),
    # C708/C712 also >14mm — bring closer (right side)
    ('C708', U2_X + 5.5, U2_Y - 0.5),
    ('C712', U2_X + 5.5, U2_Y - 2.5),
]

# U11 (LTC4368) at (58.50, 146.50) — MSOP-10 3x3mm
# Q11/Q12 currently at y≈200 (54-68mm away) — 5x6mm DFN power FETs
U11_X, U11_Y = 58.50, 146.50
u11_moves = [
    ('Q11', U11_X + 4.0, U11_Y + 1.0),
    ('Q12', U11_X + 10.0, U11_Y + 1.0),
]

# U750 (TPS552892) at (157.25, 81.00) — VQFN-HR-21 3x5mm
# L750 is 28mm away — 8x8mm inductor; C750/C751/C753/C758 are >80mm away
# Place L750 and caps around the IC
U750_X, U750_Y = 157.25, 81.00
u750_moves = [
    ('L750', U750_X + 6.0, U750_Y - 1.5),
    ('C750', U750_X + 6.0, U750_Y + 3.5),   # 8x10mm electrolytic — goes below IC
    ('C751', U750_X - 4.5, U750_Y - 3.0),
    ('C753', U750_X - 4.5, U750_Y - 5.0),
    ('C758', U750_X - 4.5, U750_Y - 7.0),
]

all_moves = u2_moves + u11_moves + u750_moves

def main():
    # Backup
    shutil.copy2(PCB_FILE, BACKUP_FILE)
    print(f"Backed up {PCB_FILE} -> {BACKUP_FILE}")

    with open(PCB_FILE, encoding='latin-1') as f:
        content = f.read()

    modified_count = 0
    for ref, new_x, new_y in all_moves:
        # Find the footprint block by reference
        # Each footprint has: (property "Reference" "REF"
        # The (at line is between the uuid line and the descr line
        
        # Build a regex to find the (at ...) line within this footprint
        # Match: the reference property, then go backward to find the (at line
        # Actually, easier: find the (at line right before the (descr line
        # in the footprint whose reference matches
        
        # Find all occurrences of property "Reference" "REF"
        for m in re.finditer(rf'\(property\s+"Reference"\s+"{ref}"', content):
            # Go back to find the (at line for this footprint
            footprint_start = content.rfind('(footprint', 0, m.start())
            if footprint_start == -1:
                continue
            
            # The (at line is between the uuid line and descr/anything before first property
            # Let's find (at within the footprint block start to the reference property
            block_prefix = content[footprint_start:m.start()]
            
            # Find the last (at in this prefix (it's the footprint's position)
            at_match = re.search(r'\(at\s+([\d.]+)\s+([\d.]+)(\s+[\d.-]+)?\)', block_prefix)
            if not at_match:
                continue
            
            old_at = at_match.group(0)
            rot_part = at_match.group(3) or ''
            
            # Build new at string preserving rotation
            new_at = f'(at {new_x} {new_y}{rot_part})'
            
            # Get the absolute position in content
            at_abs_start = footprint_start + at_match.start()
            at_abs_end = footprint_start + at_match.end()
            
            old_text = content[at_abs_start:at_abs_end]
            old_x = float(at_match.group(1))
            old_y = float(at_match.group(2))
            
            content = content[:at_abs_start] + new_at + content[at_abs_end:]
            
            modified_count += 1
            print(f'{ref}: ({old_x:.2f}, {old_y:.2f}) -> ({new_x:.2f}, {new_y:.2f})  [{old_at} -> {new_at}]')
            break  # Only modify first occurrence
        else:
            print(f'{ref}: NOT FOUND')

    if modified_count > 0:
        with open(PCB_FILE, 'w', encoding='latin-1') as f:
            f.write(content)
        print(f"\nModified {modified_count} components. File written.")
    else:
        print("\nNo modifications made.")

if __name__ == '__main__':
    main()
