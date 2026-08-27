# Ducktop2 Full-Board Routing Plan — 2026-08-24

Status: PLAN (awaiting user go-ahead). Companion docs:
`HIGH_SPEED_ROUTING_PLAN_2026-08-01.md` (impedance/geometries),
`USB_A_PORT_ROUTING_PLAN_2026-08-24.md` (port-cluster topology),
`mainboard_stackup_release.json` (fab field-solve), `ducktop2.kicad_dru` (rules).

## 0. Objective and definition of done

Route the remaining **3,307 unconnected items** (pcbnew
`GetUnconnectedCount(True)`; kicad-cli's DRC reports a partial 499 subset)
to zero, with **zero new DRC findings beyond the documented routing-phase
allowlist enforced by `gen/check_release_candidate.py`**:

- 0 shorts, 0 clearance violations, 0 unconnected items
- DRC findings exactly the fabrication allowlist (placement backlog and the
  2026-08-24 USB-A cluster dispositions; stale entries are pruned on sight)
- Schematic parity 0; `check_release_candidate.py` PASS on every gate
- Impedance pairs on approved layers at approved width/gap, no pair vias
- Power nets sized per `POWER_PLAN_8L.md` budget
- Final gerbers + drill export clean

## 1. Preconditions — all verified 2026-08-24 (commit 8643449)

| Item | State |
| --- | --- |
| Hub DIS5 SS lanes (pins 83/84/86/87) | Wired to J24 via U1802/C1852/C1853 (was a dead-net bug) |
| J24 SH pads (4) / J25 SH pads (2) | All on GND (J24 symbol gained SH pin; board synced) |
| Net classes (KiCad 10, `ducktop2.kicad_pro`; authoritative) | DIFF_85 0.183/0.1524, DIFF_90 0.1796/0.2032, DIFF_100 0.1521/0.254, USB2_45 0.2248; POWER_HI 1.0 mm incl. PACK_*_RAW / PD*_VBUS_RAW / PCIE_3V3_IN, POWER_MID 0.6 mm incl. MAKER_3V3_CORE |
| DRU rules (ducktop2.kicad_dru) | via↔track 0.18, via↔via 0.2, TH↔TH 0.4, intra-footprint exemptions (U41/U42 0.12, power pads 0.15), MK430 hole 0.15, H1/H2 0 mm hole + mask bridge + courtyard −1 |
| Project constraints (ducktop2.kicad_pro) | min_track 0.09, min_clearance 0.09, via 0.45/0.2, TH hole 0.2, hole_clearance 0.3, hole_to_hole 0.3, annular 0.1 |
| ERC / DRC / parity | 0 errors / allowlist-tracked / 0 (see the live gate, not this snapshot) |

Note on the old "min track width 0.2" blocker: it was an artifact of DRC-ing
board copies **without the project file** (kicad-cli falls back to 0.2 mm
defaults). The real project floor is 0.09 mm. DRC must always run with
cwd = ducktop2/ so `.kicad_pro` + `.kicad_dru` apply.

## 2. Toolchain (verified end-to-end 2026-08-24)

| Step | Tool | Verified |
| --- | --- | --- |
| DSN export | bundled pcbnew Python 3.9 `pcbnew.ExportSpecctraDSN` | yes (646 KB DSN, net classes + rules present) |
| Router | Freerouting v2.3.0 + Temurin JDK 25 (`/Library/Java/JavaVirtualMachines/temurin-25.jdk`, `~/.local/bin/java` on PATH) | yes (MCP `check_freerouting` → ready) |
| SES import | bundled pcbnew `pcbnew.ImportSpecctraSES` | yes (264 segments imported into a copy) |
| MCP `kicad_autoroute` | available but SWIG session is wedged | needs MCP server restart; the pcbnew-Python pipeline above is the proven fallback |

Freerouting invocation (flags matter):

```
java -jar ~/.kicad-mcp/freerouting.jar \
     -de ducktop2.dsn -do ducktop2.ses -mp 20 -mt 1
```

- `-mt 1` is mandatory: multi-threaded optimization is known to generate
  clearance violations (tool's own warning).
- Best-of-N: run 3–5 attempts with varied `-mp` (e.g. 30/45/60), keep the
  attempt with the highest routed count, import the best SES.
- The DSN export emits **no `(pair ...)` definitions** (count 0). Diff pairs
  therefore route as individual class-width nets; pair symmetry/adjacency is
  a manual post-verification step (Phase 4).

## 3. Layer strategy (8 copper layers)

| Layer | Name | Role |
| --- | --- | --- |
| L1 | F.Cu | clusters, connectors, short stubs; impedance microstrip (L1-over-L2 = 2116 prepreg geometry, fab-solved) |
| L2 | In1.Cu | GND — solid, never routed |
| L3 | In2.Cu | stripline (GND/GND); impedance pairs ONLY with fab stripline geometry (see §6) |
| L4 | In3.Cu | GND — solid, never routed |
| L5 | In4.Cu | POWER islands — source-local (11 islands, see §4.1); all other rail copper routed deliberately |
| L6 | In5.Cu | general routing; NO impedance pairs unless L5 reference unbroken |
| L7 | In6.Cu | GND — solid, never routed |
| L8 | B.Cu | long runs (layer is component-free; only ~360 TH pads block it) — the left-edge cluster highway |

## 4. Phases (each ends with a verification gate + git commit)

### Phase 0 — Checkpoint
Board is at the routing-phase checkpoint: 3,307 unrouted (499 partial
kicad-cli subset), allowlist-tracked findings, parity 0. Snapshot PDF,
commit marker. No routing yet.

### Phase 1 — Power and ground

#### §4.1 L5 source-local islands (2026-08-26 partition)

The L5 islands are **source-local**, not consumer-covering: each sits on the
rail's generating/entry point (converter output, connector VBUS) with its
local decoupling. All other rail copper is routed by hand to consumers.
Island map (mm, In4.Cu; exact net names, from `gen/write_power_zones.py`
`POWER_ISLANDS` — do not edit the board by hand, regenerate + re-indent):

| Rail | Island rect (x1,y1)-(x2,y2) | On-island (sources) |
| --- | --- | --- |
| /PD1_VBUS_RAW | (1,19)-(75,67) | U41 PD controller, J21, C2015-19 |
| /PD2_VBUS_RAW | (315,19)-(357,84) | J11, C2055 |
| /SYS_3V3 | (124,19)-(151,44) | L5, R1714/R1718, C1816 |
| /USB_PORT_5V | (157,19)-(181,45) | L1701, R1712 |
| /MU_12V | (145,69)-(181,99) | R751, RS750 |
| /SYS_5V | (119,83)-(143,109) | L4, C45 |
| /Mu Carrier/INTERNAL_USB_VBUS | (184,83)-(209,101) | U770, R777, C830 |
| /Mu Carrier/PCIE_3V3_IN | (210,83)-(265,117) | U772, L1702, C782/C832 |
| /MCU_3V3 | (270,85)-(306,103) | L3, U4, U60, R32/R35/R202 |
| /VSYS | (54,114)-(119,156) | U2 charger, C706/708/709/710 |
| /Maker MCU/MAKER_3V3_CORE | (247,8)-(308,82) | U901-913, L900, 46 pads |

Guards in the generator enforce: bounds within board, pairwise island
separation ≥ 1 mm, and every island net existing on pads.

#### Routing consequence (read before routing Phase 1)

Off-island consumer pads must be reached by **deliberate tracks, not
island adjacency** (the old bbox islands covered them; the new ones do
not). Per rail, route the source island to every off-island consumer:

- **VSYS** (40 off-island): U6/U7/U750/U1703 converter inputs, R1710/C750
  sense cluster, far-side decoupling.
- **MCU_3V3** (107 off-island): STM32 EC + full peripheral spread.
- **SYS_3V3** (139 off-island): largest distribution — NVMe J10, Wi-Fi,
  RTL8111H, hub U1700, muxes/redrivers (see POWER_PLAN_8L.md budget).
- **SYS_5V** (20 off-island): U6 output to radio/eFuse branch, amp, USB
  switches.
- **USB_PORT_5V** (18 off-island): U1703 to TPS2553 branches + PD ports.
- **MU_12V** (15 off-island): Mu module lands (A1), fan branch.
- **PD1_VBUS_RAW** (1 off-island): D712 at (348.7,167.8) — long right-edge
  trunk from the U41 island.
- **PD2_VBUS_RAW** (10 off-island): D713, C2056-59, U2015, U42 — route
  from the J11 island (x~356) to the x25-298 scatter.
- **INTERNAL_USB_VBUS** (1 off-island): TP13.
- **MAKER_3V3_CORE** (2 off-island): C934, R930.

Widths: VSYS 1.0 mm, SYS_5V 1.0 mm, MU_12V 1.0 mm, VBUS_RAW 1.0 mm,
MCU_3V3 0.6 mm, USB_PORT_5V 0.6 mm, INTERNAL_USB_VBUS 0.4 mm, control 0.25 mm.
Long legs on B.Cu, short legs on L1/L6.

- GND: keep L2/L4/L7 solid; add via stitching at cluster boundaries.
- Gate: DRC shorts=0 clearance=0; parity 0; commit.

### Phase 2 — Hub fanout (VQFN-100, 0.4 mm pitch)
- Fan out SS/D pins at y=32.54 (81–87) and y=44.22 (41/42) to the clean
  via band at **y=29.5, x 258–266, 1.2 mm pitch**:
  `81→x267.4, 82→266.2, 83→265.0, 84→263.8, 86→262.6, 87→261.4, 42→268.6, 41→269.8`
  (verified zero via-via shorts).
- SS pins at DIFF_90 width immediately; D± at USB2_45 width.
- Gate: DRC; commit.

### Phase 3 — Left-edge port cluster (J24/J25 + J12/J22/J23 + J190)
- B.Cu long runs; cluster-side vias ≥ 1.2 mm from any pad.
- **Pad rotation accounting (critical):** J24/J25 pads carry their own 270°
  pad rotation on top of the footprint's 270° → combined 540° = 180°, so
  world-coord pads are 1.6 × 0.7 mm. Any tooling must use footprint rotation
  + pad rotation, or it will place vias/tracks inside pads.
- Cluster netlist: `USB_A_PORT_ROUTING_PLAN_2026-08-24.md` §cluster netlist.
- Gate: DRC (verify J24/J25 pads report 1.6 × 0.7); commit.

### Phase 4 — Differential pairs (DIFF_85/90/100, USB2_45)
- Route on L1 or L8 microstrip (same geometry) at class width/gap; L3 only
  with the fab stripline numbers below; **no vias on pairs**.
- AC-coupling caps (C1720–C1729, C1852/C1853) centered on the pair, stub
  ≤ 0.4 mm.
- Manual pair audit: per-pair symmetry (parallel, equal length), min
  pair-to-pair separation 0.5 mm, pair-to-via ≥ 0.3 mm.
- Gate: DRC + pair audit script output; commit.

### Phase 5 — Remaining general signals
- L1/L6; via discipline (0.6/0.3 mm, ≥ 0.18 mm to tracks, ≥ 0.2 mm to vias,
  ≥ 0.4 mm TH-pad-to-TH-pad per DRU).
- Gate: DRC 0 new findings; commit.

### Phase 6 — Zone refill + stitching
- Refill all zones (11 copper islands + 3 GND planes + keepouts); the gate
  now DRCs in refilled state and fails on any non-`isolated_copper` category
  introduced by refill (see `check_release_candidate.py` REFILL_DELTA_TYPES).
  Add GND stitching vias around hub, connectors, and along B.Cu long-run
  edges.
- Gate: DRC (refill can change counts — rerun full gate); commit.

### Phase 7 — Final verification
- `kicad-cli pcb drc` (cwd = ducktop2) → 0 unconnected / 0 shorts /
  0 clearance, findings exactly the enforced fabrication allowlist
- `sync_main_pcb_from_netlist.py` → parity 0
- `check_release_candidate.py` → PASS
- gerbers + drill export test
- commit with DRC report attached

## 5. Working-copy discipline

- Never route the committed `ducktop2.kicad_pcb` directly. Each phase runs
  on a copy; adopt via the sync script, diff the board file, then commit.
- Every phase gets a git commit (single-file changes keep history legible).
- Snapshot PDF after each phase (kicad-cli `pcb render`).

## 6. Impedance geometries (fab numbers)

| Class | L1/L8 microstrip | L3/L6 stripline (GND/GND) |
| --- | --- | --- |
| DIFF_90 (USB 3.x) | w 0.1796 / s 0.2032 | w 4.37 mil (0.111) / s 8.00 mil (0.203) |
| DIFF_100 (HDMI/ETH) | w 0.1521 / s 0.254 | w 3.59 mil (0.091) / s 10.00 mil (0.254) |
| USB2_45 | w 0.2248 | w 5.17 mil (0.131) |
| DIFF_85 (PCIe, 2026-08-25 fab reply) | w 7.19 mil (0.183) / s 6.00 mil (0.1524) | w 4.48 mil (0.114) / s 6.00 mil (0.1524) |

Pairs must NOT change layers (L1↔L3 switches need a field-solver pass first).

## 7. Known risks and mitigations

1. Freerouting multi-threaded violation bug → always `-mt 1`.
2. DSN has no diff-pair definitions → pairs route as individual nets; pair
   symmetry is a manual audit step (Phase 4), fixes done interactively.
3. MCP SWIG session wedged → restart the MCP server; pcbnew-Python pipeline
   is proven and independent of it.
4. PCIe 85 Ω resolved 2026-08-25: fab geometry is L1/L8 w 0.183 / s 0.1524,
   L3/L6 w 0.114 / s 0.1524 (all 85.00 Ω ±10 %). DIFF_85 class carries the
   L1/L8 numbers.
5. Zone refill can shift DRC counts → refill before the final gate, never
   after.
6. Fine-pitch convergence (hub 0.4 mm, cluster 1 mm pads): if Freerouting
   stalls with shorts inside the cluster, hand-finish that region on L1 —
   this was the exact failure mode of the 2026-08-24 scripted attempt.

## 8. Definition of done (exact numbers)

- `kicad-cli pcb drc` from the project dir: **0 unconnected items, 0 shorts,
  0 clearances**, findings = the enforced fabrication allowlist only
- release gate: all gates PASS
- gerbers + drill export to `manufacturing/` without errors
- one commit per phase; final commit tagged with the DRC report