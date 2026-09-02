# Ducktop2 rebuild pipeline (Phase 5) — READ BEFORE TOUCHING THE BOARDS

The schematics and boards are REGENERATED. Never hand-edit a .kicad_sch.

1. `python3 gen/generate_fh41_68s_footprint.py`      # FH41-68S land pattern (self-verifying)
2. `python3 gen/generate_conn100_ffc_symbol.py`      # FFC symbols (FFC_PINS=68 default)
3. `python3 gen/generate_mu_carrier_sheet.py`        # center project (root + sheets + FPC sheets)
4. `python3 gen/generate_left_io_project.py`         # left project
5. `python3 gen/generate_right_io_project.py`        # right project
6. `python3 gen/generate_bms_project.py`             # bms project
7. `python3 gen/verify_design_contracts.py --project {ducktop2,left_io,right_io,bms} --schematic-only`
   (also refreshes verification/*_netlist.xml, which step 9 consumes)
8. Recreate the three daughterboards from their schematics (MCP
   create_board_from_schematic, or delete + re-sync), then:
9. `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 gen/generate_split_boards.py`
   (additive env: KICAD_PYTHON; exits non-zero on any hard failure)
10. `python3 gen/fix_board_hygiene.py`               # overlap sweep + final zone refill
11. ERC + DRC + gates:
    `kicad-cli sch erc ...` x4, `kicad-cli pcb drc ...` x4,
    `python3 gen/check_release_candidate.py --stage schematic|fabrication`

NEVER run "Update PCB from Schematic" (F8) on ducktop2-center.kicad_pcb:
its net names only match the schematic after normalize_board_nets; a sync
outside the pipeline rewrites hundreds of nets. The pipeline is the only
sanctioned path. Net names on all boards are normalized to the schematic's
exact names by generate_split_boards (normalize_board_nets); connector pad
nets are resolved from gen/fpc_contract.py (the boundary SSOT, including
per-cable CABLE_TRANSFORM and FPC_ROTATIONS).
