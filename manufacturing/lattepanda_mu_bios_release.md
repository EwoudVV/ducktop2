# compute module and BIOS

updated 23 september 2026. **Ultra migration and hardware qualification pending.**

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
| BIOS | an official Mu Ultra image verified for the installed variant; exact image and hashes still pending |

the two Ultra models share the documented module interface and mechanical
format. this does not make the current N305 carrier a drop-in Ultra board.
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
  laptop and charges its battery simultaneously. the current roughly 40 W
  Mu/display rail still needs review and any necessary circuit changes.
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

the current KiCad files still describe the N305 circuitry. these are the
new design requirements, not completed migration or first-article results.
existing firmware qualification gates stay disabled until their evidence
is recorded. 226V tests alone do not establish a tested 256V upgrade.

## sources

- [Ultra specifications](https://docs.lattepanda.com/content/mu_ultra_edition/specification/)
- [Mu to Ultra migration guide](https://docs.lattepanda.com/content/mu_ultra_edition/migration_guide_mu_to_mu_ultra/)
- [226V development kit and shipping list](https://www.dfrobot.com/product-3149.html)
- [256V module](https://www.dfrobot.com/product-3148.html)
- [Ultra cooler](https://www.dfrobot.com/product-3156.html)
- [official Ultra BIOS files](https://github.com/LattePandaTeam/LattePanda-Mu-Ultra/tree/main/Softwares/BIOS)
