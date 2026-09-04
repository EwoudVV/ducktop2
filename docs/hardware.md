# hardware

updated 4 september 2026. this describes the intended circuit in the current
split projects. [current status](design-status.md) lists where the board
files or testing still fall short of it.

## boards

| Board | Main contents | Connection to the rest of the laptop |
| --- | --- | --- |
| Center | Mu socket A1, STM32 EC, RP2350 maker MCU, charger U2, gauge U10, input selectors, converters, storage, system audio | FPC102, FPC103, FPC105, keyboard, radio, and module connectors |
| Left I/O | USB7206C hub, PD1 controller and protection, USB-C J21/J22/J23, USB-A J24/J25, AUX connector J190 | FPC101 to center FPC102 |
| Right I/O | PD2 controller and protection, USB-C J11/J12, HDMI, RTL8111H Ethernet | FPC104 to center FPC103 |
| BMS | J2 cell harness, F1, BQ77915, LTC4368, protection FETs, shunts, TPB1-16 | FPC106 to center FPC105 |
| Keyboard | 65 MX ULP switches and diodes, 5 x 14 matrix | 30-pin FFC to J310 |
| Radio | DRA818V, DRA818U, filters/switches, MAX-M10S GNSS, separate PCM2900C radio codec | Removable FFC interface |

the left, center, and right boards retain the original shared XY frame.
the BMS was reshaped and moved, so its file coordinates are no longer an
installed chassis position. the radio and keyboard also have their own frames.

## compute, display, and storage

the target is a LattePanda Mu N305 with 16 GB RAM and 64 GB eMMC. A1 is its
socket/interface, with separate mechanical retention. the module is powered
from regulated `MU_12V`, made by the TPS552892 converter.

the AUO B160QAN03.K internal display connects to the Mu's onboard eDP
connector. those eDP lanes do not run across the custom center PCB or an I/O
FFC. the final harness is still pending. [display details](display-direct-edp.md)

J10 is the M-key 2280 NVMe socket with PCIe x4. J40 is the E-key 2230
Wi-Fi/Bluetooth socket. the live schematic includes its PCIe TX/RX path to
Mu HSIO3, its reference clock/reset support, and USB.

## ports

| Reference | Board | Intended role |
| --- | --- | --- |
| J21 | Left | USB-C data and PD charging input |
| J22, J23 | Left | USB-C host/data ports with protected source VBUS |
| J11 | Right | USB-C data and PD charging input |
| J12 | Right | USB2 host/data port from hub DS4, with protected source VBUS |
| J24 | Left | USB3 Type-A on hub downstream port 5 |
| J25 | Left | USB2 Type-A on hub downstream port 6 |
| J190 | Left | AUX/DC input |

J12's `HUB_DS4_DP/DM` and `HUB_PRT_CTL4` cross both I/O cables. its U1760
power switch is hub-controlled. J12 is not a third laptop charging input.

external HDMI comes from the Mu TCP0 path. Gigabit Ethernet uses the RTL8111H
on the right board. review the complete routed channel, including cables,
coupling, clocks, protection, and connector transitions before release.

## controllers

the STM32F407 EC owns laptop functions: input qualification, power sequencing,
charging policy, keyboard scanning/HID, fan control, lid and buttons, status
OLEDs, and optional-device enables. its policy and target-code status are in
the [firmware docs](../firmware/README.md).

the RP2350 maker controller is independent and appears as a separate USB
device. exposed GPIO and user rails have their own authorization and
interlock policy. experiments on those pins should not control the EC.

## input and audio

the keyboard is a 273.5 x 80.0 mm, two-layer, 0.8 mm PCB. its matrix goes
straight to the EC over an FFC. the firmware scans columns and reads rows;
the Fn layer and report generation have host tests.

the JOMAA trackpad is a complete USB device. a USB-C plug stays at the
trackpad, and the cut Standard-A end of its USB2 cable goes to the four J58
solder lands: 1 GND, 2 D-, 3 D+, 4 VBUS. cable retention is still unfinished.

system audio uses its own USB codec, TPA2012D2 speaker amplifier, headphone
amplifier/jack, and microphone path. the radio codec is separate. headphone
insertion is intended to mute the speakers through EC control.

## power and radio

the battery, charger, protection, source priority, and ground references are
covered in [power and battery](power-and-battery.md).

the radio board is removable. its power, data, control, PTT, and status paths
default off or inactive. the rest of the laptop is intended to operate with
it absent. RF filters, antennas, and coexistence still need measurement.
[radio board](../radio_daughterboard/README.md)


## expected behavior

| When i do this | Intended behavior | What's still needed |
| --- | --- | --- |
| Press power | The EC qualifies the available source, applies limits, and starts the Mu in order. | Normal target requests, applied budgets, and startup HIL. |
| Plug a charger into J21 or J11 | The laptop negotiates PD and charges when the source and power budget allow it. | Target integration and measured charging/source-transfer tests. |
| Charge with the Mu off | The always-on EC and charger can manage charging while compute stays off. | Validate this on the finished hardware/firmware. |
| Plug power into J12/J22/J23 | Those ports remain source-only host/data ports; they do not charge the laptop. | Port-role and back-power tests. |
| Use AUX/DC | The source is qualified within the actual protection windows and available power. | Measured limits, charging behavior, and source transfer. |
| Close the lid | Turn the internal display off while the Mu keeps running. opening the lid should restore the display without a power cycle. | Target lid events, OS integration, and display testing. |
| Type or use Fn | The 65-key matrix produces normal keyboard and consumer reports. | Verify every physical switch and USB report on target. |
| Plug in headphones | Route audio to headphones and mute the speakers. | EC detect/amp integration and audio tests. |
| Read battery status | Show valid percentage, charge state, and useful remaining-time data. | Pack calibration and EC-to-OS telemetry transport. |
| Look at the OLEDs | Show real power/battery and thermal/system information; unavailable data stays unavailable. | SSD1306 target rendering, valid telemetry, and tests. |
| Run a heavy workload | The fan responds to measured temperatures and the system stays within a validated power/thermal envelope. | Characterize the actual cooler and integrate host limits. |
| Experiment with maker GPIO | The RP2350 handles the experiment independently of laptop control. | Complete target/interlock behavior and test it. |
| Remove the radio board | The laptop can still boot, charge, and use its normal input/audio/networking. | Optional-board isolation and fault tests. |
| Lose the main NVMe install | Boot a prepared recovery environment from eMMC or external recovery media. | Build and test the recovery path on the Mu. |

## keyboard Fn layer

the implemented keymap uses Fn+1..0 for F1..F10, Fn+Esc for grave/tilde,
Fn+Backspace for Delete, Fn+Up/Down for brightness, and Fn+Left/Right for
volume. the matrix scans columns and reads rows. software mapping tests
are separate from physical key and USB enumeration tests.

## OLED content

the planned left OLED shows source, battery percentage/state, voltage,
current, power, time remaining, capacity, cycles, and health. the right shows
fan, skin/Mu temperature, system/optional-device state, firmware version,
and faults. the content composer exists; all of that still needs reliable
target measurements and display transport.

## display and storage

the internal display target is 2560x1600 at 120 Hz over direct eDP. the
panel has achieved that mode on the Intehill controller; the final Mu harness
has not been validated. the main OS uses NVMe, with eMMC planned for recovery,
hibernation storage, and offline data. hibernation is a separate explicit
operation from the agreed lid-close behavior.
