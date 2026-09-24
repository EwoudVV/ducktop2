# compute module and BIOS

updated 24 september 2026. **interface migration in progress; power and hardware qualification pending.**

i'm starting with a Mu Ultra 226V. the carrier, power path and cooling
must also support the 256V from the start, so a later upgrade only needs
the module swap and any documented BIOS or software setup.

## selected parts

| item | target |
| --- | --- |
| initial module | DFRobot DFR1294, Mu Ultra Core Ultra 5 226V, 16 GB RAM |
| upgrade module | DFRobot DFR1295, Mu Ultra Core Ultra 7 256V, 16 GB RAM |
| initial development kit | DFR1294-1, includes the 226V module, Mini Carrier and active cooler |
| reference cooler | FIT1049, the Mu Ultra cooler family |
| carrier socket | TE Connectivity 2309411-1, with separate mechanical retention |
| boot storage | NVMe on the custom carrier; neither module has onboard eMMC |
| recovery | prepared external USB media |
| BIOS | official DFLT `SBCLNLCXR120-A.bin`, build 2026-04-30; downloaded binary hash and hardware qualification still pending |

the two Ultra models share the documented module interface and mechanical
format. the old N305 carrier needs the interface and power changes below.
the N305-specific BIOS identity previously recorded here is obsolete for
this target. do not flash an N305 image onto either Ultra model.

## what the common carrier has to support

- one assembled PCB and one cooling assembly for both variants. no solder
  rework, connector change or cooler replacement when upgrading to 256V.
- the 256V's sustained and transient load, including conversion losses,
  display, NVMe, wireless and permitted USB loads. check the 226V too rather
  than assuming one processor's test results qualify the other.
- the official 50 W or greater Ultra supply recommendation as an input to
  the system budget, not a promise that a 50 W adapter powers the complete
  laptop and charges its battery simultaneously. the selected target is
  20 V / 5 A USB-C input. the current charger and roughly 40 W Mu/display
  rail still need circuit changes before that can be enabled.
- a checked common USB, PCIe, HDMI and eDP allocation. move the existing
  USB2 connections off pins 67/69/70/72, check pin 136's reserved state,
  and review every used pin against the Ultra comparison table.
- real NVMe CLKREQ wiring and correct peripheral power behaviour for
  Modern Standby. the old fixed-low clock request and S3 assumptions need
  changing. qualify firmware limits and sleep behaviour for both SKUs.
- a documented PCIe link-speed policy. existing Gen3 routing is not a
  Gen4 qualification; validate the complete routed channels and cables.

## before calling the upgrade supported

1. finish the Ultra schematic and PCB migration, then rerun ERC, DRC,
   schematic parity and the power-path checks on the final files.
2. record the module model, BIOS image/hash, BIOS settings, power limits,
   cooler and source used for each tested configuration.
3. verify cold boot, NVMe, wireless, Ethernet, all USB ports, HDMI and the
   exact internal panel mode with both the 226V and 256V.
4. measure startup, sustained load and short peaks, then verify charging,
   source changes, battery operation and faults within the approved budget.
5. measure temperatures and repeat sleep/wake tests. check the mechanical
   fit after a powered-off module replacement.

## interface changes

the saved interface uses the full [Ultra pin table](../reference/lattepanda/mu-ultra-pinout.json).
the six native USB2 ports are allocated as follows:

| port | A1 contacts | connection |
| --- | --- | --- |
| P1 | 109 D-, 111 D+ | U400 USB2513BT-I/M2 internal hub |
| P2 | 112 D+, 114 D- | left USB7206C upstream |
| P3 | 73 D-, 75 D+ | existing USBC1 path |
| P4 | 79 D-, 81 D+ | EC host USB |
| P5 | 76 D+, 78 D- | maker MCU |
| P6 | 82 D+, 84 D- | Bluetooth |

U400 port 1 is the system codec, port 2 is the trackpad and port 3 is the
optional radio. the first two ports are strapped as non-removable. the
trackpad keeps its protected VBUS switch, with hub permission and isolated
fault feedback. the hub's reset supervisor stays in place.

HDMI now leaves TCP2. NVMe uses REFCLK2 and CLKREQ2 at pin 108; R50's
permanent pull-down is removed. pins 67/69/70/72 and reserved pin 136 are
open. the external coupling capacitors on the used PCIe lanes remain.

the physical USB companion-port mapping still needs a kit test with USB2
and USB3 devices. the default BIOS groups Ethernet's lane 1 with unused
lane 2, so x1 link training also needs checking. pin 7 is SLP_S4 despite
the legacy `SLS_S3` net name. both status outputs can stay high in Modern
Standby; the current host watchdog must be adapted before enabling suspend.

the existing power circuits are still present. the 100 W charger, source
transitions and full module load are not qualified by these interface changes.
existing firmware qualification gates stay disabled until their evidence
is recorded. 226V tests alone do not establish a tested 256V upgrade.

## sources

- [Ultra specifications](https://docs.lattepanda.com/content/mu_ultra_edition/specification/)
- [Mu to Ultra migration guide](https://docs.lattepanda.com/content/mu_ultra_edition/migration_guide_mu_to_mu_ultra/)
- [226V development kit and shipping list](https://www.dfrobot.com/product-3149.html)
- [256V module](https://www.dfrobot.com/product-3148.html)
- [Ultra cooler](https://www.dfrobot.com/product-3156.html)
- [official Ultra BIOS files](https://github.com/LattePandaTeam/LattePanda-Mu-Ultra/tree/main/Softwares/BIOS)
- [internal hub datasheet](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/USB251xB-xBi-Data-Sheet-DS00001692.pdf)
- [internal hub errata](https://ww1.microchip.com/downloads/en/DeviceDoc/USB251xB-xBi-Errata-DS80000627D.pdf)
