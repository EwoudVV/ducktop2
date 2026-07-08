# ducktop2 Layout Readiness Notes

These notes capture the current schematic decisions before PCB placement. Keep
`ducktop2.kicad_pcb` blank until the first intentional layout pass.

The placement contract for the first floorplan is now captured in
`PRE_LAYOUT_FREEZE.md`. Treat that file as the starting checklist before moving
anything onto the PCB.

## Locked Module-Class Decisions

- OLEDs: two SSD1306 I2C status panels, 3.3 V only. Each header pinout is
  `GND`, `3V3`, `SCL`, `SDA`, `RES`, `SA0`.
- OLED addresses: OLED A defaults to `0x3C`; OLED B defaults to `0x3D`.
  Do not populate both panels at the same address.
- Wi-Fi/Bluetooth: Intel AX210-class M.2 2230 Key-E module. Wi-Fi uses PCIe;
  Bluetooth uses USB2. Avoid CNVio/CNVio2-only modules unless LattePanda Mu
  support is explicitly verified.
- GNSS: u-blox MAX-M10S on-board module, UART to EC, passive U.FL antenna by
  default. A DNP active-antenna bias option is present but should stay unpopulated
  unless the selected antenna requires it.
- Protected pack gauge: BQ34Z100-G1 TSSOP-14 pinout is verified against the
  TI datasheet. Divider is 215 kOhm / 16.5 kOhm for about 0.9 V at 12.6 V
  full-charge 3S; RS1 remains the populated low-side gauge shunt.
- Battery entry: the protected-pack default now separates `PACK_POS_RAW`,
  `PACK_POS_FUSED`, `PACK_NEG_RAW`, `CELL*_BAL` sense-only balance taps, and
  system `GND`. The main pack positive lead goes through a replaceable blade
  fuse footprint before charger/gauge/system use; the main negative lead returns
  through the low-side current shunt. The bq76920 bare-cell AFE/balance-tap
  network is DNP by default and must not be treated as the protected-pack
  current path.
- BQ25798 wiring: the charger is configured as a no-external-input-mux,
  single-combined-input design. `VAC1`/`VAC2` tie to `VBUS_COMBINED`,
  `ACDRV1`/`ACDRV2` go to `GND`, and unused `SDRV` has a 1 nF capacitor to
  ground.
- Population options: generator DNP handling now emits real KiCad `dnp yes`
  and `in_bom no` metadata for DNP-valued optional parts, including address
  straps, debug connectors, bare-cell AFE parts, active GNSS bias, and the
  optional solar MPPT path.
- Symbol/footprint discipline: the generator now includes unit-0/common pins
  when placing symbols, so hidden/common ground pads are not silently dropped.
  Project-local numbered NMOS symbols are used for the SOT-23 fan PWM sink and
  TO-252/DPAK optional power FET placeholders instead of stock `Device:Q_NMOS`,
  so schematic pins match footprint pad numbers. `gen/check_schematic.py` now
  includes a footprint-pad audit; the latest run checked 476 generated footprint
  groups with zero symbol/pad mismatches.
- Crystals and ESD arrays: 4-pad 3225 crystals use `Crystal_GND24`, with pads
  2/4 grounded and the active crystal terminals on pads 1/3. TPD4E02B04DQA
  HDMI ESD arrays explicitly tie common ground pad 3 to `GND`.
- Optional DNP power MOSFET choices: Q1/Q2 bare-cell pack protection FETs use
  Infineon IPD90N04S4L-04 as the selected DNP candidate, a 40 V DPAK part with
  low conduction loss for a 10 A-class path. Q3/Q4 optional BQ24650 solar buck
  FETs use Infineon IPD50N04S4L-08 as the selected DNP candidate, a 40 V DPAK
  part with lower gate charge for the 6 V BQ24650 gate driver. Both match the
  project-local TO-252 symbol pinout of 1=G, 2=D/tab, 3=S.
- EC host link: Mu USB2_P3 is reserved for the STM32 EC USB device link.
- Touch link: Mu USB2_P4 is reserved for the internal touchscreen USB2 link.
- Trackpad: sheet 8 now reserves Mu USB2_P8 for a required internal USB HID
  trackpad. The connector contract supplies fused 5 V, `MCU_3V3`, USB2 D+/D-,
  EC I2C, `TPAD_INT_N`, `TPAD_RESET_N`, and grounds over a generic 10-pin FFC.
  The exact trackpad module, click mechanism, and FFC pinout must be chosen
  before layout release.
- Reused monitor path: sheet 11 keeps the Intehill portable-monitor controller
  as an internal module. Mu DDIB HDMI 2.0 feeds video/audio to the monitor HDMI
  input, so the monitor's integrated speakers stay usable. Mu USB2_P4 plus a
  5 V internal USB-C source feeds touch/power. This is the preferred path if
  the monitor cannot be safely depanelled.
- Monitor teardown update: the original V1 monitor glass/touch stack cracked
  during removal, but photos revealed useful hardware data. The panel sticker
  confirms AUO `B160QAN03.K HW:0A / AUO30A5`, a 16 inch 2560x1600 panel family,
  and the controller board exposes HDMI-A, two USB-C ports, two 2-pin speaker
  connectors, side buttons, and a wide panel FFC. See
  `INTEHILL_TEARDOWN_FINDINGS.md` before buying a replacement panel or donor
  monitor.
- Bench update: the cracked original panel still displays a clean image, so the
  controller/LCD electrical path is usable for testing and measurements even if
  the cracked glass is not desirable as the final enclosure part.
- Current measured loose parts: each 3.7 V cell is about 100 x 60 mm; three
  cells laid flat in a row need about 300 x 60 mm before gaps, tabs, wiring,
  BMS, padding, and strain relief. Each speaker module is about 18 x 38 mm and
  should sit near the front/user edge. The Intehill screen/controller board is
  about 114 x 70 mm and needs an internal cable path to the panel, button
  pass-through, USB-C/power/touch feed, HDMI feed, and speaker outputs.
- Full-rate display target: the retained-controller path is now constrained as
  HDMI 2.0 / 18 Gbps end-to-end for 2560x1600 at 120 Hz, and the user has
  bench-verified that the Intehill HDMI input runs the native mode at 120 Hz.
  Sheet 11 includes 100 nF TMDS AC-coupling caps, 470 ohm HDMI bias parts
  following the Mu HDMI reference direction, and HDMI-2.0-capable
  low-capacitance TMDS ESD. Do not substitute HDMI 1.4-only adapters, cables,
  ESD arrays, or long uncontrolled harnesses on this path.
- External monitor output: sheet 6 uses LattePanda Mu `TCP0` as the second
  default-BIOS HDMI 2.0 output and adds a real user-accessible HDMI-A jack.
  The earlier TCP0 USB-C/DP-alt-mode concept was removed; `TCP1` remains the
  better future candidate if a later Type-C video/PD port is needed.
- AUX/SOLAR DC input: sheet 1 uses one 2-pin screw-terminal input for
  bench/random external supplies and optional solar. The shared input is fused,
  TVS-clamped, and divided down to EC `AUX_DC_ADC` so firmware can identify the
  source voltage. Default population routes it through `D191` into the BQ25798
  VBUS combine node. The solar side feature uses the same terminal by populating
  the BQ24650 MPPT path feed `D8` instead of adding a second user-facing plug.
- Monitor power: the retained Intehill USB-C power/touch feed is gated by a
  TPS2592xx-class eFuse from `SYS_5V`, enabled by EC `PANEL_PWR_EN`, with
  an 82.5 kOhm current-limit resistor, 10 nF dV/dT soft-start capacitor, and
  47 uF local VBUS bulk as first-pass values. This replaces the earlier bare
  fuse/load-switch stub.
- Monitor buttons: sheet 11 includes a trace-only pass-through between the
  monitor controller keypad connector and the case/button-board connector for
  power, menu/source, volume, and brightness controls. No EC logic is inserted.
- Raw panel path: sheet 10 remains as the fallback if a compatible bare eDP
  panel/controller path is chosen instead of retaining the Intehill controller.
- User GPIO: an exposed EC-owned header is present with EC I2C, five
  GPIO/SPI-capable signals, 3.3 V, and grounds. It is intentionally not a
  direct LattePanda/PCH GPIO header.
- Keyboard: sheet 12 defines a separate Pi 500+ keycap-compatible low-profile
  mechanical keyboard daughterboard. The motherboard exports an 8x16 matrix,
  EC I2C, 3.3 V, optional 5 V backlight power, and grounds over a 30-pin
  FFC/board-to-board connector. Key switches, stabilizers, physical key
  placement, and anti-ghosting diodes live on the cheaper keyboard PCB, not
  the 6-layer motherboard.
- Keyboard physical target: Raspberry Pi documents the 500+ as 312 x 123 x
  35 mm with 84, 85, or 88 mechanical keys depending on regional variant.
  Match the user's actual Pi 500+ keycap set before committing the daughterboard
  outline, stabilizer footprints, or matrix map.
- Keyboard switch target: Gateron KS-33 low-profile MX-stem switches so the
  Pi 500+ keycaps remain reusable. The stock Pi 500+ uses clicky KS-33-style
  switches; use KS-33 Silent 2.0 tactile or linear parts for the quieter
  creamy/thocky feel.
- Keyboard host path: the STM32 EC scans the keyboard matrix and enumerates to
  the LattePanda Mu as an internal USB HID device over Mu USB2_P3. The x86 host
  should see a normal boot keyboard, not a direct PCH GPIO matrix.
- Mu power/reset: the EC can assert `MU_PWRBTN_N` and `MU_RSTBTN_N` as
  open-drain GPIOs, with a 4-pin case-button harness on sheet 2 for physical
  power/reset buttons.
- Ham radios: DRA818V/SA818-compatible 2m and DRA818U/SA818-compatible 70cm
  module sockets are present with Dorji V1.23 pinout wiring, a local radio
  rail, audio harness, first-pass VHF/UHF low-pass filter values, and RF SPDT
  antenna switching. Default RF switch state now selects the internal/PCB
  antenna-feed path, and EC control can switch to the rear external SMA/u.FL
  path.
- Radio audio: sheet 13 adds a PCM2902 USB audio codec on Mu USB2_P5. VHF and
  UHF receive audio feed the host as stereo inputs; one codec DAC output feeds
  both radio mic inputs through isolation resistors while EC PTT selects the
  active transmitter.
- Cooling: sheet 8 now treats cooling as a conventional active laptop thermal
  path: copper spreader/heatpipe or vapor chamber to a quiet 5 V PWM blower.
  The blower rail is fused, tach is pulled up to EC 3.3 V, PWM is an open-drain
  sink, and the EC reads separate skin/hinge and Mu-heatsink NTCs.
- Cooling part direction: use the official Mu thermal envelope as a validation
  reference, but do not force a tall stock cooler into the laptop. Floorplan
  around a flat copper cold plate plus heatpipe/vapor chamber to a side exhaust
  blower, then pick the exact blower after the keyboard/display/battery Z-stack
  is measured.
- Current cooling buy/design direction: use the LattePanda Mu official active
  cooler only as a cheap bring-up reference and thermal-envelope sanity check.
  For the actual laptop, design around a conventional low-profile copper plate
  plus heatpipe/vapor chamber to a 5 V PWM blower. Frore AirJet-class modules
  stay in the experiment bucket until availability, price, airflow ducting, and
  dust tolerance make sense for a one-off build.
- Cooling exclusions: Peltier/TEC cooling is not part of the base design because
  it worsens battery life, adds hot-side heat, and creates condensation risk.
  AirJet-style solid-state active modules may be a future mechanical experiment,
  but the schematic baseline remains a 5 V blower.
- Maker MCU: sheet 14 adds a separate Arduino/Pico-class sandbox controller
  interface on Mu USB2_P7. It has fused 5 V from `SYS_5V`, module-provided
  `MAKER_3V3`, boot/reset/SWD controls, and an exposed 3.3 V GPIO header. This
  is intentionally separate from the EC so experiments cannot break laptop
  keyboard, power, fan, or display control.
- Internal display: sheet 10 now models a 40-pin eDP source-to-panel harness
  from the LattePanda Mu on-module eDP connector, with carrier-injected
  `LCD_3V3`, `LCD_BL_PWR`, EC backlight controls, and an optional I2C touch FFC.
- Net classes: `ducktop2.kicad_pro` now defines starter classes for `USB2_90R`,
  `USB3_HDMI_100R`, `PCIe_85R`, `RF_50R`, `POWER_5A`, and `POWER_10A_PACK`.
  These are pre-layout buckets; recalculate actual trace widths/gaps after the
  board stackup is chosen.

## Placement Priorities

- Put the user-accessible side ports first: USB-C charge inputs, two hub USB-C
  ports, external TCP0 HDMI-A, and the protected AUX/SOLAR screw-terminal/random
  DC opening. Preserve connector orientation and cable-clearance room.
- Put the M.2 E-key socket where its module antenna leads can reach board-edge
  antennas without crossing power inductors, USB-C connectors, or charger
  switching loops.
- Put the MAX-M10S close to the GNSS U.FL connector. Keep the RF trace short.
- Keep the SSD1306 headers near the display opening; avoid routing high-speed
  pairs beneath the display flex/header region.
- Place the EC USB/touch/fan/display-service sheet items near their mechanical
  exits: keyboard/controller area, hinge/display harness, fan cavity, and
  touchscreen flex/USB board.
- Place the retained Intehill controller or internal HDMI/USB-C adapter stack
  so no cable exits the enclosure. The external-looking HDMI/USB-C connectors
  on sheet 11 are electrical stand-ins for internal plugs/adapters.
- Place the monitor button pass-through connectors near the display/controller
  harness path so the opened monitor's keypad board can relocate without a
  tall service loop.
- Put the keyboard FFC/mezzanine connector on the front edge of the motherboard
  where the separate low-profile switch PCB can meet it without a tall cable
  loop or service strain.
- Reserve the palm-rest/front-center zone for the trackpad before placing
  front speakers or keyboard support hardware. Keep the trackpad FFC short and
  leave mechanical room for either physical-click travel or separate low-profile
  click buttons.
- Put the 18 x 38 mm speaker modules near the front/user edge with acoustic
  openings and keep their harnesses away from the trackpad FFC and keyboard
  connector strain-relief path.
- Preserve the Pi 500+ key positions and stabilizer assumptions when creating
  the separate keyboard PCB. The exact regional key count/layout must match the
  user's physical keycap set before switch footprints are committed.
- Put the maker MCU socket and exposed maker header somewhere user-accessible
  but away from charger hot loops, radio RF, and HDMI/USB3/PCIe high-speed
  lanes. The module should be replaceable or reprogrammable without disassembling
  the main board stack.
- Put the Mu cooling assembly early in the mechanical floorplan. The heatsink
  pressure stack, heatpipe/vapor chamber, fin outlet, blower intake, and service
  clearance will constrain connector edges and display/keyboard height.
- Put VHF/UHF radio modules and their LPF/switch/antenna chains near the rear
  antenna edge with real RF keepouts and distance from GNSS/Wi-Fi antennas.
  The rear external connectors are the performance path; the internal/PCB feed
  is the default convenience path.
- Place charger, battery, SYS_5V, and SYS_3V3 power blocks early because their
  thermal copper and current paths will dominate the board floorplan.
- Use the current first-pass power defaults as layout anchors: BQ25798
  `PROG=10.5k` for 3S/1.5 MHz, BQ25798 ILIM divider for about a 3 A input
  clamp, and DNP BQ24650 solar defaults for 18 V nominal MPP, 12.6 V 3S charge
  target, and about 1 A fast-charge sense current. Revisit after
  thermal/mechanical power budgeting.
- Treat the pack connector, blade fuse, low-side shunt, and charger/system
  copper as high-current layout items. Do not downsize them to JST-XH or 1206
  current paths.
- Put the AUX/SOLAR DC screw terminal near an edge with clearance and a clear
  polarity marking. Keep its fuse, TVS, input bulk cap, BQ25798 feed diode, and
  optional solar MPPT feed close to the terminal before the trace joins either
  charger path.
- Keep the PCM2902 radio-audio codec away from RF PA output, radio buck
  switching nodes, and USB3/PCIe/TMDS high-speed lanes. Put the audio RC/gain
  network close to the codec/radio module boundary, not underneath antennas.

## Routing Constraints

- Route USB3, PCIe, TCP0 HDMI, and M.2 E-key PCIe as impedance-controlled
  differential pairs with length/polarity review before fab.
- Route GNSS `RF_IN` as 50 ohm controlled impedance, with via count minimized.
- Keep GNSS RF away from Wi-Fi antennas, USB3/PCIe/TCP0 high-speed pairs,
  switching regulators, inductors, and charger hot loops.
- Give all three USB-C connector shield/ground structures a deliberate chassis
  and ESD return strategy during layout.
- Keep the M.2 E-key antenna keepout and module courtyard clear. Do not pour
  copper under antenna keepout zones specified by the selected module/antenna.
- Route EC-host USB2 and touch USB2 as short 90 ohm differential pairs; keep
  their ESD parts close to the connector/module-side exposure points.
- Route the trackpad USB2 pair as a short 90 ohm differential pair on Mu
  USB2_P8. Keep ESD near the trackpad FFC/module connector and keep the
  `TPAD_INT_N`/`TPAD_RESET_N` sideband traces away from charger switch nodes.
- Route DDIB HDMI TMDS pairs as controlled-impedance differential pairs from
  the Mu edge to the retained monitor-controller harness. Keep HDMI DDC/HPD
  away from switching nodes and keep the TPD4E02B04 ESD arrays close to the
  cable/adapter exit.
- For the 120 Hz target, treat the DDIB HDMI path like a real 6 Gbps/lane
  channel: minimize stubs, keep ESD arrays at the internal HDMI cable/adapter
  exit, preserve pair polarity, length-match within each pair, and use a
  short certified HDMI 2.0-class internal cable/plug if the monitor controller
  is retained.
- Route the TCP0 external HDMI jack with the same HDMI 2.0 discipline: short
  100 ohm TMDS pairs, low-cap ESD at the connector, controlled return path,
  and verified lane order/polarity before layout release.
- Route monitor button pass-through nets as low-speed keypad lines, but keep
  them away from HDMI/TMDS pairs, radio RF, and buck-switching nodes.
- Route the keyboard matrix as low-speed GPIO, but keep the FFC reference
  ground solid and avoid running matrix traces through charger/radio hot zones.
- On the separate keyboard PCB, put one diode per key and lock diode orientation
  with EC firmware before fab. Use the EC I2C pins only for keyboard ID, LED
  driver, or low-speed utility functions.
- Route fan tach/PWM away from switching nodes. Keep the fused fan 5 V path
  short, and place the Mu-heatsink NTC where it tracks module temperature rather
  than exhaust air temperature.
- Route Mu USB2_P5 to the PCM2902 as a short 90 ohm USB2 differential pair.
- Route Mu USB2_P7 to the maker MCU as a short 90 ohm USB2 differential pair.
  Keep the exposed header GPIO traces low-speed and clearly separated from the
  EC-owned laptop-control nets.
- Keep DRA818 AF_OUT and MIC_IN audio traces short, filtered, and away from RF
  output and buck switch nodes; finalize gain/attenuation values by bench
  measurement before fab.
- Route VHF/UHF RF paths as 50 ohm controlled impedance from module to LPF,
  switch, and antenna connectors. Keep LPF ground returns tight and stitched.
  A true printed 2 m antenna is not realistic in this enclosure; treat VHF
  "PCB antenna" as an internal/enclosure antenna feed unless a qualified loaded
  antenna geometry is selected and tested.

## Open Layout Decisions

- Final board outline and exact connector edge coordinates. Current intent is
  side edges for USB-C, HDMI-A, and AUX/SOLAR/random DC; rear edge for antenna
  connectors.
- Battery connector/pack geometry and cable exit direction. Current schematic
  placeholder is a Mega-Fit-class high-current connector plus blade-fuse
  footprint; verify against the actual pack harness before layout.
- AUX/SOLAR connector current rating, exact accepted voltage label, and default
  population policy: `D191` for random DC into BQ25798, or `D8`/BQ24650 MPPT
  parts for the optional solar behavior. Do not populate both paths together
  unless dual-charger behavior has been intentionally reviewed.
- Whether MAX-M10S needs the DNP active antenna bias populated, and whether an
  antenna supervisor is worth adding later.
- Whether each SSD1306 is a bare display, small module, or cabled daughterboard.
- Exact trackpad module: outer dimensions, active area, FFC pinout, USB-vs-I2C
  behavior, click mechanism, mounting holes/adhesive, and Linux HID behavior.
  The schematic assumes USB HID as the host-facing path and keeps EC I2C/reset
  as sideband.
- Current trackpad direction: prefer a known USB HID module such as the MNT
  Reform capacitive trackpad for the integrated build. Buy/borrow a cheap wired
  USB touchpad such as PERIPAD-501 only if palm-rest size testing is needed
  before spending on the final module. Haptic click can be added with an LRA/ERM
  driver later, but should not block proving the pointer path.
- Exact maker MCU module/pinout/footprint: Pico/RP2350/Arduino-class is the
  current electrical intent, but J340 should be swapped to the exact module
  pattern before layout release if one is chosen.
- Exact USB-C ESD part placement and return-path stitching pattern.
- TCP0 external HDMI lane order/polarity confirmation against the selected
  LattePanda Mu BIOS/reference design before layout.
- Intehill mechanical path: safe disassembly vs internal short HDMI/USB-C plugs
  vs replacing it with a raw panel. The design constraint is no external display
  cables under any option.
- Intehill cable path: one internal USB-C cable for power/touch/video requires a
  real Type-C DP Alt Mode source path on the mainboard. A thin USB-C FPC/FFC
  harness is only a harness, not an HDMI-to-USB-C converter. Keep internal HDMI
  plus separate low-profile USB-C/power-touch harness as the conservative first
  spin unless a full DP Alt Mode source path is deliberately revived.
- Intehill button board pinout: identify whether the keypad is discrete
  switches or a resistor ladder, then update J302/J303 labels/footprints before
  fab.
- Intehill power requirement: verify whether the first-pass 5 V / about 3 A
  source path is enough in HDMI+USB mode, or whether the monitor expects USB-C
  PD/source behavior for reliable operation.
- Monitor eFuse tuning: confirm the 82.5 kOhm ILIM and 10 nF dV/dT values after
  measuring the monitor's steady-state current and plug-in/inrush behavior.
- Keyboard mechanical stack: exact low-profile switch family, key pitch,
  stabilizers, plate/case strategy, daughterboard thickness, and connector
  choice/orientation.
- Palm-rest/input stack: exact trackpad size, front speaker placement, and
  whether the trackpad needs a diving-board click, separate buttons, or a
  tap-to-click-only mechanical mount.
- Keyboard electrical details before keyboard-PCB release: exact Pi 500+
  regional layout, KS-33 footprint variant, diode orientation, optional
  backlight/RGB driver, and whether switches are soldered or socketed.
- Cooling mechanical details: exact Mu heatsink/spreader, fan/blower part,
  duct geometry, fin outlet, acoustic target, and whether an AirJet-style option
  deserves a separate experimental layout study. Baseline remains conventional
  blower because it is easier to source, duct, service, and drive from the
  existing 4-wire fan schematic.
- Radio audio gain/attenuation: final PCM2902 line-in, line-out, and DRA818
  mic/AF levels need bench calibration for voice, APRS, and satellite software.
- BQ34Z100-G1 calibration/default-flash work: voltage divider parameter,
  3S cell count, chemistry ID, shunt value, and learning cycle.
- DRA818V/U LPF simulation/bench verification, RF switch truth table, antenna
  connector choices, and enclosure antenna clearances.
