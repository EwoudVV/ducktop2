# KiCad MCP Server — Setup & Usage Guide

This project is wired to the **KiCad MCP server** (mixelpixx/KiCAD-MCP-Server v2.6.0), which lets the AI edit the ducktop2 schematic and PCB **through a live KiCad instance** instead of hand-editing `.kicad_sch` / `.kicad_pcb` text files. Edits made via the MCP appear in the KiCad UI in real time, and KiCad (not the AI) owns file serialization, so edits stay valid.

## How it works

- The MCP server is a Node.js process (`~/tools/KiCAD-MCP-Server/dist/index.js`) that spawns a Python subprocess using KiCad's bundled Python 3.9.
- It talks to a **running KiCad GUI** over the IPC API (Unix socket `/tmp/kicad/api.sock`). When KiCad is running with the project open, the backend reports `realtime_sync: true` — changes apply live, no reloads.
- If KiCad isn't running, it falls back to file-based SWIG mode (`realtime_sync: false`). Edits still work but KiCad won't show them until you reopen the project. `KICAD_BACKEND=auto` handles the choice automatically.

## Current status (verified 2026-08-12)

- KiCad 10.0.4 installed at `/Applications/KiCad/KiCad.app` (IPC API server **enabled** via `~/Library/Preferences/kicad/10.0/kicad_common.json` → `api.enable_server: true`).
- MCP server registered in the global opencode config: `~/.config/opencode/opencode.json` under `mcp.kicad`.
- Tested: `check_kicad_ui` → `backend: "ipc", realtime_sync: true`; `open_project` on `ducktop2.kicad_pro` → 1181 components loaded; net classes readable.

## How to use it

The `kicad` MCP server exposes 221 tools, grouped into 13 categories. Tools are both directly callable and discoverable via:

- `list_tool_categories` / `get_category_tools` / `search_tools` — discover what exists
- `execute_tool` — run any tool by name

### Typical workflow (preferred)

1. **Make sure KiCad is running with ducktop2 open** (KiCad project manager or PCB editor with `ducktop2.kicad_pcb` loaded). Verify with `check_kicad_ui` — you want `realtime_sync: true`.
2. `open_project` with `filename: "/Users/ellievanvooren/Documents/kicad/ducktop2/ducktop2.kicad_pro"` to bind the session to the project.
3. Read state first: `get_component_list`, `get_nets_list`, `get_schematic_view` / `get_board_2d_view` (raster previews), `run_drc` / `run_erc` for verification.
4. Make edits with the high-level tools, then **always run `run_drc` (and `run_erc` for schematics) afterward** and read violations.

### Key tools by area

| Area | Tools |
|---|---|
| Project | `open_project`, `save_project`, `get_project_info`, `snapshot_project` |
| Board | `set_board_size`, `add_board_outline`, `add_zone`, `add_mounting_hole`, `import_svg_logo`, `get_board_2d_view` |
| Components | `place_component`, `move_component`, `rotate_component`, `replace_component`, `find_component`, `get_component_pads`, `batch_move_components`, `get_component_geometry` |
| Routing | `route_trace`, `route_pad_to_pad` (auto-vias), `add_via`, `query_traces`, `create_netclass`, `add_copper_pour`, `refill_zones`, `check_placement_clearance` |
| Schematic | `add_schematic_component`, `add_wire`, `add_schematic_connection`, `add_schematic_net_label`, `connect_to_net`, `annotate_schematic`, `get_schematic_pin_locations`, `get_net_connections`, `sync_schematic_to_board` (F8 equivalent) |
| DRC/ERC | `run_drc`, `get_drc_violations`, `run_erc`, `get_design_rules`, `set_design_rules`, `set_layer_constraints` |
| Export | `export_gerber`, `export_pdf`, `export_svg`, `export_3d`, `export_bom`, `export_netlist`, `export_position_file` |
| Autoroute | `autoroute` (Freerouting), `export_dsn` / `import_ses` |
| Parts | `search_footprints`, `search_symbols`, `create_footprint`, `create_symbol`, `enrich_datasheets`, JLCPCB search tools |

Full inventory: `docs/TOOL_INVENTORY.md` in the server repo (`~/tools/KiCAD-MCP-Server/docs/`).

## Rules and gotchas (learned the hard way)

1. **Run DRC/ERC after every edit batch.** The MCP can place parts and route traces that violate constraints; verification is the only safety net. Compare against `verification/ducktop2_current_live_drc.json`.
2. **Open the project in KiCad's GUI first.** IPC mode binds to what's open in the GUI. `open_project` via MCP may fall back to SWIG session pinning; for live sync, have the board open in pcbnew.
3. **Check `_backend` / `_realtime` in tool responses.** If `realtime_sync: false`, KiCad's UI won't reflect changes until the project is reopened/reloaded.
4. **`save_project` has an external-edit guard**: it refuses to overwrite a board file that changed on disk since load (unless `force: true`). Don't fight it — reload the board (`reload_board` / `discard_or_reload`) or use force deliberately.
5. **This project is heavily revisioned** (`.bak`, `.p1.3_backup`, etc.). Before large MCP-driven edits, use `snapshot_project` or copy the `.kicad_pcb` to a new backup — the AI is not the only editor here.
6. **KiCad must not be quit while a session holds it via IPC.** If the GUI is closed mid-session, tools may fail or fall back to SWIG; `check_kicad_ui` tells you the truth.
7. **Backend selection is per-session** once a project is loaded (session pinning). If you need to switch backends, `close_project` then reopen.
8. **Off-grid / broken symbols:** `lint_offgrid` and `repair_flat_symbols` exist if schematic geometry misbehaves (e.g. SnapEDA symbols).

## Environment details (for the AI)

- Server repo: `~/tools/KiCAD-MCP-Server` (build v2.6.0; `venv/` = KiCad Python 3.9 venv with `--system-site-packages`, deps include `kipy` 0.7.1, `kicad-skip` 0.2.5)
- Python used by the server: `KICAD_PYTHON=~/tools/KiCAD-MCP-Server/venv/bin/python`
- KiCad IPC socket: `/tmp/kicad/api.sock` (created when KiCad launches)
- MCP config: `~/.config/opencode/opencode.json` → `mcp.kicad` (type `local`, `KICAD_BACKEND=auto`)
- Logs: `~/.kicad-mcp/logs/` (default `info` level, 10 MB rotation)

## Diagnostics

- `check_kicad_ui` → is KiCad running, which backend, is IPC connected.
- `get_project_info` → which project/board/schematic the session is bound to.
- `search_tools <keyword>` → find a tool when unsure of its name.
- Server log: `~/.kicad-mcp/logs/kicad_interface.log` for Python-side errors.
