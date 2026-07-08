# ducktop2 Pre-Layout Freeze

Date: 2026-07-06

This is the contract for the first PCB floorplan pass. It freezes the current
schematic intent, names the physical assumptions that layout should honor, and
keeps unresolved mechanical unknowns visible instead of hiding them in routing.

## Non-Negotiables

- Keep `ducktop2.kicad_pcb` blank until the first intentional placement pass.
  The current blank-file check is 79 bytes.
- Do not add more feature sheets before the first floorplan. The next work is
  mechanical fit, connector edges, high-current copper, high-speed escape, and
  thermal stack.
- The display must have no external cables. If the Intehill controller is
  retained, HDMI/USB-C/button wiring becomes internal harnessing. If it cannot
  be opened safely, design the enclosure around short internal plugs/adapters.
- The first board spin is the integrated motherboard only. The keyboard is a
  separate cheaper PCB, and exact key placement belongs there.

## Frozen Physical Architecture

### Compute And Thermal

- Compute module remains LattePanda Mu. Use the Mu reference dimensions,
  connector keepouts, module courtyard, and thermal contact zone as hard
  mechanical constraints before placing nearby connectors.
- Cooling baseline is a conventional laptop stack: Mu heat spreader or cold
  plate, heatpipe/vapor chamber if useful, fin stack, and quiet 5 V PWM blower.
  Use LattePanda's 6 W to 35 W TDP range as the sizing envelope; final sustained
  performance depends on the measured enclosure airflow and heat-spreader stack.
- Peltier/TEC cooling remains excluded from the base design.
- AirJet-style modules remain a future experiment only. They are interesting,
  and the AirJet Mini Slim class claims very thin 5 W-class heat removal, but
  the baseline schematic assumes a broadly sourceable fused 5 V blower with
  tach and open-drain PWM.

### Display

- Default path is retained Intehill controller, not raw panel, unless the
  monitor can be opened cleanly and the raw panel/control board can be
  identified.
- Teardown update: the original V1 monitor glass/touch stack is cracked and
  should not be considered a final usable display assembly. The controller board
  and speaker/button hardware remain useful design references. The panel sticker
  confirms AUO `B160QAN03.K HW:0A / AUO30A5`.
- Bench update: the cracked panel still produces a clean image, which means the
  retained Intehill controller/LCD path can be used for 120 Hz power, thermal,
  speaker, and button measurements while the replacement raw panel is pending.
- Internal video/audio path is Mu DDIB HDMI 2.0 to the Intehill controller HDMI
  input. User has bench-verified 2560x1600 at 120 Hz through HDMI.
- Internal touch/power path is Mu USB2_P4 plus a protected 5 V monitor supply
  into the controller's USB-C/touch/power side.
- The monitor button board is trace pass-through only. No EC logic is inserted
  unless a later teardown proves the keypad is a clean resistor ladder or logic
  interface worth controlling.

### Keyboard

- Keyboard is a separate 2-layer daughterboard using the Pi 500+ keycap layout
  and low-profile mechanical switches.
- Raspberry Pi documents the Pi 500+ as 312 x 123 x 35 mm with 84, 85, or
  88 mechanical keys depending on regional variant. Match the user's physical
  keyboard/keycap set before committing the daughterboard outline.
- Switch target remains the Gateron KS-33 low-profile MX-stem family so reused
  Pi 500+ keycaps still fit. The stock Pi 500+ switch is clicky; choose a
  quiet KS-33 Silent 2.0 tactile or linear variant for the creamy/thocky feel.
- Motherboard connector stays as a 30-pin keyboard FFC/mezzanine contract:
  8x16 matrix, EC I2C utility bus, 3.3 V, optional 5 V backlight power, and
  grounds.
- Each key gets a diode on the keyboard PCB. Diode orientation must be locked
  with EC firmware before keyboard PCB fab.

### Trackpad And Front Input Area

- A trackpad is required because the final display path may be non-touch. It is
  now part of sheet 8, not a later add-on.
- Host path is Mu USB2_P8 as an internal USB HID pointing device. EC sideband
  owns reset/interrupt and optional I2C utility/control lines.
- Preferred low-risk final path is a real USB HID module. Current shortlist:
  MNT Reform capacitive trackpad module for the cleanest embedded integration,
  or Perixx PERIPAD-501 as a cheap bench/ergonomics mockup. Random laptop
  replacement trackpads remain risky because many are HID-over-I2C plus
  vendor/ACPI assumptions instead of plain USB HID.
- The MNT module is electrically attractive but physically small compared with
  a MacBook-class trackpad. Keep a large trackpad target in the mechanical
  planner, plus an MNT-size reference rectangle, until a larger embedded USB
  HID option is found.
- A JOMAA wired USB trackpad is now a plausible large-trackpad candidate. Treat
  it as an external module to gut or mount internally until proven otherwise.
  On arrival, verify actual outer size/thickness, whether the cable can be
  replaced or soldered to a board connector, USB HID behavior on macOS/Linux,
  gesture behavior without vendor software, and whether the click is mechanical,
  tap-only, or firmware-generated.
- Sheet 8 now includes a populated internal USB-C receptacle for the trackpad
  cable on Mu USB2_P8, with fused 5 V and default-current Type-C CC pull-ups.
  The older 10-pin trackpad FFC connector is DNP fallback only if the trackpad
  is later gutted to internal wires/FFC.
- A MacBook-style haptic click is possible as a second-stage feature using an
  LRA/ERM haptic actuator and driver such as DRV2605L, but it is not a drop-in
  replacement for Apple's Force Touch/Taptic stack. First pass should work with
  tap-to-click or simple mechanical buttons; add haptic feedback only after the
  pointer path is proven.
- Reserve the palm-rest/front-center zone before placing speakers, keyboard
  connector support, or battery edges.

### Mechanical Layout Tool

- `mechanical_layout_planner.html` is a standalone drag-and-drop floorplanning
  helper in the project root. It uses millimeter dimensions, browser local
  storage, JSON export/import, and default placeholders for the lid panel,
  Intehill controller, three cells, keyboard, trackpad, speakers, Mu, cooler,
  exhaust, NVMe, ports, and rear antenna connector zone.
- The planner is only a packaging sketch. It does not replace KiCad board
  outline/mounting work, but it is the right place to quickly test whether the
  laptop can physically exist before locking connector edges.

### Power Entry

- Battery entry remains protected 3S pack by default: main positive through
  the blade fuse into `PACK_POS_FUSED`, main negative through the low-side
  shunt into system `GND`, balance taps sense-only/DNP.
- Pack connector remains Mega-Fit-class high-current, not JST-XH. Use real
  strain relief and copper width; the schematic connector is a placement
  contract, not permission to make skinny traces.
- Current cell measurement: each loose 3.7 V cell is about 100 x 60 mm. Three
  cells laid flat in a row require about 300 x 60 mm before spacing, tabs,
  insulation, BMS, padding, and cable strain relief. Thickness is still unknown.
- Shared AUX/SOLAR screw terminal stays one physical input. Default population
  is random DC into BQ25798 through `D191`; optional solar MPPT populates `D8`
  and BQ24650 path instead. Do not populate both paths without a deliberate
  charger-policy review.

### RF And Antennas

- Wi-Fi/Bluetooth is AX210-class M.2 E-key with external antennas routed to
  the enclosure edge.
- VHF/UHF radios get LPF-first RF routing, RF switch, default internal/PCB
  antenna-feed path where practical, and optional rear external SMA/u.FL path.
  Do not treat a true 2 m PCB antenna as realistic; the default VHF path should
  be a loaded internal/enclosure antenna feed or a short internal coax to an
  enclosure antenna.
- GNSS gets the quietest practical edge/corner with sky view, short 50 ohm RF
  path, and distance from Wi-Fi/radio TX antennas.

## First Floorplan Edge Map

- Rear/hinge/internal display edge: Intehill controller HDMI plug/harness, USB-C
  power/touch plug/harness, monitor button-board pass-through, display-service
  headers, fan exhaust.
- Front/keyboard edge: 30-pin keyboard daughterboard connector, trackpad FFC,
  palm-rest keepout, and two front speaker openings/modules, with enough
  clearance for thin FFC/mezzanine routing and no tall service loop.
- Left user edge: USB-C charge inputs and AUX/SOLAR screw terminal behind a
  protected access opening, battery service path if the enclosure allows it.
- Right user edge: two downstream USB-C hub ports and the external HDMI-A output.
- Rear edge/corners: VHF/UHF rear external antenna connector options, Wi-Fi
  antenna leads, GNSS U.FL/internal antenna feed. Keep GNSS away from radio TX
  and switching power.
- Board center/thermal zone: LattePanda Mu, heat spreader, memory/module
  keepout, blower inlet/outlet path, SYS buck regulators placed to avoid
  preheating intake air.
- Power zone: pack connector, blade fuse, low-side shunt, BQ25798, SYS_5V,
  SYS_3V3, USB-C PD input ORing, and AUX/SOLAR protection grouped for short
  high-current loops.
- Display controller zone: Intehill controller board is about 114 x 70 mm, so
  reserve a flat internal bay with connector-height clearance and cable exits
  for HDMI, USB-C/power/touch, panel FFC, buttons, and speakers.
- Intehill one-cable USB-C is mechanically attractive, but electrically it is
  only simple if the mainboard implements a real full-featured USB-C DP Alt Mode
  source with power, USB2 touch, CC/PD policy, and orientation handling. A flat
  internal USB-C cable can carry those signals, but it cannot convert HDMI to
  USB-C video by itself. The known-good first-pass path remains internal HDMI
  for video/audio plus low-profile USB-C/power-touch harnessing.
- Correct desired harness shape, if one-cable display is revived: USB-C male
  plug on the Intehill-controller end, and a dense FPC/board connector on the
  motherboard end. Do not use generic charge-only FPV ribbon cables here unless
  the vendor proves all 24 Type-C pins, CC/SBU, SuperSpeed/DP lanes, shielding,
  and controlled-impedance routing are present.
- Current thermal hardware direction is now a 150 mm flat heatpipe plus a
  50 x 50 x 14 mm fin stack. The exact blower remains to be selected around the
  final side-exhaust location and keyboard/base Z stack.

## KiCad Net Classes

The project file now defines starter classes:

- `USB2_90R`: Mu USB2 links, touch USB2, EC USB, PCM2902 USB, maker MCU USB.
- `USB3_HDMI_100R`: USB3 SuperSpeed and HDMI/TMDS style 100 ohm differential
  pairs.
- `PCIe_85R`: NVMe and M.2 E-key PCIe.
- `RF_50R`: GNSS, VHF/UHF antenna, LPF, and RF switch traces.
- `POWER_5A`: `VSYS`, `SYS_5V`, `VBUS_COMBINED`, monitor 5 V, fan 5 V, and
  charger-input power paths that are not the raw pack path.
- `POWER_10A_PACK`: `PACK_POS_RAW`, `PACK_POS_FUSED`, `PACK_NEG_RAW`, shunt,
  blade fuse, and the immediate battery connector copper.

These class widths are starter values, not impedance-certified geometry. After
the actual 6-layer stackup is chosen, recalculate widths/gaps in KiCad's
calculator or the board house impedance tool and update the classes before
routing high-speed nets.

## Measurements Required Before Placement Release

- Intehill monitor: confirm whether the shell opens safely; photograph PCB
  labels; measure controller board outline, connector heights, cable exit
  direction, button-board pin count, speaker wiring, and screw/adhesive points.
  Use `INTEHILL_TEARDOWN_MEASUREMENT_GUIDE.md` as the first-attempt checklist.
- Intehill power: measure 5 V current in HDMI plus touch mode at 2560x1600
  120 Hz, including plug-in/inrush behavior. Confirm whether the monitor works
  reliably from plain 5 V or expects USB-C PD on either port.
- Speakers: each measured speaker module is about 18 x 38 mm. Confirm
  impedance, polarity, connector pitch, acoustic opening direction, and whether
  both are driven directly by the Intehill controller board.
- Trackpad: pick and measure the exact module. Record active area, outer size,
  thickness, FFC pitch/pinout, mounting method, click mechanism, and whether it
  appears to the host as USB HID without custom drivers.
- Keyboard: measure Pi 500+ keycap set, row/column layout, stabilizer wire
  locations, spacebar width, cap stem positions, and total keyboard opening.
  Verify KS-33 footprint and socket/no-socket decision before daughterboard CAD.
- Cooling: choose exact blower and heat spreader geometry. Measure total Z stack
  from Mu thermal surface to keyboard/display clearance, including compression
  pad and heatpipe/vapor chamber thickness.
- Battery: measure pack dimensions, wire gauge, connector/cable exit, fuse
  service access, and strain-relief route. Confirm the pack protection board
  current rating and cutoff behavior.
- Antennas: choose enclosure locations before RF placement. Document distance
  between Wi-Fi, GNSS, VHF, and UHF antennas; avoid putting GNSS near radio TX.
  Default internal antenna feeds and rear external connector feeds both need
  board-edge keepout and coax/ground strategy.
- User edges: keep charge USB-C, downstream USB-C, external HDMI-A, and AUX/SOLAR
  on the side edges like a laptop; keep radio antenna connectors on the rear.

## Layout Start Order

1. Board outline, mounting holes, hinge/display opening, keyboard opening, fan
   cavity, battery cavity, trackpad/palm-rest area, speaker openings, and major
   enclosure keepouts.
2. LattePanda Mu, thermal module, fan, and heat spreader.
3. Display/controller internal connectors, keyboard connector, trackpad FFC, and
   front speaker harnesses.
4. User-facing USB-C, HDMI-A, AUX/SOLAR, antenna, and battery service edges.
5. High-current power components and copper.
6. High-speed connectors and escape paths: HDMI, USB3, PCIe, USB2.
7. RF modules, LPFs, switches, and antennas.
8. EC, maker MCU, OLED headers, radios, codec, low-speed headers.

## Source Links

- Intehill monitor product page: https://www.intehill.com/products/intehill-16-inch-120hz-touchscreen-portable-monitor-t16kb-t16pb
- LattePanda Mu product page: https://www.lattepanda.com/lattepanda-mu
- LattePanda Mu hardware repository: https://github.com/LattePandaTeam/LattePanda-Mu
- Raspberry Pi 500+ product page: https://www.raspberrypi.com/products/raspberry-pi-500-plus/
- Gateron low-profile switch family: https://www.gateron.com
- Gateron KS-33 Silent 2.0 switch option: https://www.gateron.com/products/gateron-ks-33-low-profile-red-silent-20-mechanical-switches-set
- Raspberry Pi 500+ keyboard documentation: https://www.raspberrypi.com/documentation/computers/keyboard-computers.html
- Infineon BGS12WN6 RF switch datasheet: https://www.infineon.com/cms/en/product/rf/rf-switches/antenna-switches/bgs12wn6/
- Frore AirJet information: https://www.froresystems.com
- Frore AirJet Mini Slim information: https://www.froresystems.com/products/airjet-r-mini-slim
- Molex Mega-Fit product family: https://www.molex.com/en-us/products/connectors/wire-to-board-connectors/mega-fit-connectors
