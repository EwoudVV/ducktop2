# Hardware Architecture

This page describes the current Ducktop2 motherboard, not the retired ideas
that appeared earlier in the project.

## Compute and Display

The main computer is a LattePanda Mu with an Intel N305 or N100-class processor,
LPDDR5 memory, and 64 GB eMMC. A regulated `MU_12V` rail powers the module and
its onboard eDP backlight supply.

The internal display is an AUO B160QAN03.K. The replacement panel has been
tested at its native 2560x1600 resolution and 120 Hz through the original
Intehill controller. The laptop design uses the Mu's onboard 40-pin eDP
connector instead, so the carrier board does not route the eDP lanes.

The eDP cable is still a measured part, not a generic laptop cable. Both
connector families, pin-one orientation, power rails, and all 40 contacts must
be confirmed before ordering the final harness. See
[display-direct-edp.md](display-direct-edp.md).

## Storage and Networking

- M.2 M-key 2280 socket with PCIe Gen3 x4 for the primary NVMe drive
- M.2 E-key 2230 socket for an AX210-class Wi-Fi/Bluetooth card
- RTL8111H PCIe Gigabit Ethernet with a mid-mount integrated-magnetics jack
- External antenna connections at the rear of the case

The current placement still needs a high-speed pass. AC-coupling capacitors,
clocks, and endpoint support parts must be moved into their manufacturer
placement windows before those interfaces are routed.

## External I/O

- Five USB-C host/data ports through native Mu links and a USB7206C hub
- One rear data/charging port per side with TPS25751A USB-PD control
- Three host/data ports with a source-only power role and protected 5 V VBUS
- External HDMI-A from Mu TCP0
- Two 15 V USB-C PD charging inputs
- Protected AUX/DC input for bench supplies or occasional solar use
- Gigabit Ethernet
- Rear radio and wireless antenna connections

The earlier VL822 USB hub and USB-C video-port plans are gone. The two rear
PD/data ports use native Mu links, the other three ports remain data-capable,
and the external video connector is HDMI.

## Battery and Power

Ducktop2 uses three 3.7 V pouch cells in series. The motherboard contains:

- BQ7791500 autonomous three-cell overvoltage, undervoltage, overcurrent, and
  short-circuit protection
- Back-to-back charge/discharge MOSFETs and an 8 mOhm current shunt
- LTC4368-1 whole-pack protection, a second shunt, and a replaceable 10 A fuse
- BQ25798 buck-boost charger and NVDC power path
- BQ34Z100-G1 pack fuel gauge
- Two TPS25751A USB-C PD controllers with released EEPROM policy
- Default-off input eFuses and an always-on source manager
- TPS552892 regulated 12 V rail plus system 5 V and 3.3 V rails

The small boards attached to the cells are retained for cell-local thermal
cutoff. They are not used as the motherboard's electrical OV/UV/OC protection.
The motherboard intentionally has no battery thermistor harness.

## Controllers

The STM32F407 embedded controller owns the laptop functions that the x86 module
does not provide directly:

- source qualification, charging policy, and power sequencing
- keyboard scan and USB HID
- fan control and temperature monitoring
- lid, power, and reset controls
- two SSD1306 status displays
- radio, GNSS, trackpad sideband, and audio enables

The RP2350 is a separate maker controller. It appears as its own USB device and
exports protected GPIO and user power without giving experiments control over
the laptop's EC.

## Keyboard, Trackpad, and Audio

The keyboard is a separate 273.5 x 80 mm, two-layer board with 65 Cherry MX
Ultra Low Profile switches in a 5x14 matrix. It connects to the mainboard over a
30-pin FFC. The rev-A keyboard production files are already generated.

The trackpad is a 140 x 105 mm USB unit. System audio uses an internal USB hub,
a PCM2900-family codec, a TPA2012D2 stereo amplifier, two front speakers, and a
chip-down digital microphone/preamp path. A second USB audio codec handles the
radio receive/transmit audio path.

## Radio and Navigation

The motherboard supports DRA818V and DRA818U modules for 2 m and 70 cm FM. Each
path has external low-pass filtering and RF switching between the internal feed
and a rear connector. A u-blox MAX-M10S provides GNSS for position, APRS, and
software-assisted satellite work.

The RF layout, antennas, filter tuning, coexistence, and emissions still need
physical validation. The schematic provides the intended paths; it does not
replace VNA and spectrum-analyzer measurements.
