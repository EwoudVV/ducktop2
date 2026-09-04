# direct-eDP display

the selected panel is the AUO B160QAN03.K HW0A. the replacement panel has
been tested at 2560x1600 and 120 Hz using the Intehill controller. the
finished laptop is intended to connect it directly to the Mu's onboard eDP
connector, removing the separate monitor controller and external cable loop.

updated 4 september 2026. the final harness remains pending in
[`direct_edp_harness_release.json`](../manufacturing/direct_edp_harness_release.json).
the known panel test does not validate a new Mu-to-panel cable.

## connector identification

| End | Recorded identification | Status |
| --- | --- | --- |
| Mu | I-PEX CABLINE-VS 40-pin, 0.5 mm pitch; module documentation names the 20455 family | Module-side family/pin table recorded; inspect exact installed suffix and pin-1 datum |
| Panel | Possible I-PEX CABLINE-CA II 20682-040E-02, 40-pin, 0.4 mm pitch | Secondary-catalog association only; not confirmed for the owned panel |

the recorded CABLINE-VS cable-side family is 20453, with matching housing
and shell parts. if the panel-side CA II identification is confirmed, its
cable-side family is 20679 with the associated 20680 housing, 3204 shell,
and 20681 lock bar. confirm full suffixes from the actual drawings before
using those families in an order.

the intended cable is a finished micro-coax assembly from a cable vendor.
the earlier 200-300 mm length was a candidate, pending the hinge route.
I-PEX's 82691/82692 VS-to-VS assemblies are relevant only if both ends and
the contact map are actually compatible. they are not automatically a cable
for the suspected CA II panel connector.

## module-side contact reference

this is the retained Mu-side reference map. panel destination contacts are
still unresolved. do not infer a 1:1 wiring order from the shared pin count.

| Mu contact(s) | Signal | Required panel connection |
| --- | --- | --- |
| 1, 34, 35, 40 | NC | Open |
| 2, 5, 8, 11, 14, 17, 23-26, 28-31 | GND | Individually mapped panel grounds |
| 3 / 4 | DDIA_TX3- / DDIA_TX3+ | Panel lane 3 - / + |
| 6 / 7 | DDIA_TX2- / DDIA_TX2+ | Panel lane 2 - / + |
| 9 / 10 | DDIA_TX1- / DDIA_TX1+ | Panel lane 1 - / + |
| 12 / 13 | DDIA_TX0- / DDIA_TX0+ | Panel lane 0 - / + |
| 15 / 16 | DDIA_AUX+ / DDIA_AUX- | Panel AUX + / - |
| 18-21 | LCD_VCC | Panel logic-supply contacts, subject to confirmed limits |
| 22 | Selftest, grounded by default on Mu | Leave unassigned until the panel specification resolves it |
| 27 | HPD | Panel HPD |
| 32 | BL_EN | Panel backlight enable |
| 33 | BL_PWM | Panel brightness PWM |
| 36-39 | BL_PWR | Panel backlight-power contacts, subject to confirmed limits |

source: [official Mu pinouts](https://github.com/LattePandaTeam/LattePanda-Mu/blob/main/Electricals/Pinouts/README.md).
the local upstream reference is [`gen/Pinouts_README.md`](../gen/Pinouts_README.md).

## power and link requirements

the Mu reference defines LCD_VCC as 3.3 V and BL_PWR as following the module
input voltage. the custom center design supplies regulated `MU_12V`.
that makes the exact panel's permitted backlight voltage and startup sequence
part of the harness review; the selected rail alone does not settle them.

at 2560x1600 and 120 Hz, active video is about 11.80 Gbit/s at 8 bits per
component, before blanking. use the panel's real EDID/DPCD and timings to
confirm lane count, link rate, color depth, and bandwidth. the design expects
four lanes and needs HBR2 or better for the intended mode. do not assume DSC
or a two-lane arrangement without panel evidence.

the panel's logic and backlight voltage/current limits, inrush, enable/PWM
levels and timing, HPD behavior, sequencing, connector orientation, and full
contact map remain part of the unresolved panel-side record.

## what to do before ordering the harness

1. Inspect the exact panel and both connectors. record markings, suffixes,
   contact side, pin-1 datums, and connector position.
2. Obtain the exact panel specification or establish a controlled contact/
   electrical record using the working Intehill assembly as a reference.
3. Produce a complete drawing: every Mu pin/signal to every panel pin/signal,
   with NCs, grounds, logic power, backlight power, and control signals explicit.
4. Measure the installed route through the hinge sweep. specify length,
   insertion, bends, strain relief, power conductors, and the micro-coax construction.
5. Review the cable's impedance, skew/loss, flex life, and connector compatibility
   with the assembly vendor. continuity/isolation-test the finished harness before mating.
6. Validate cold/warm boot, brightness, the intended lid behavior, supported
   sleep/resume modes, full-resolution 120 Hz, and errors on the real Mu.

retain those results with the harness drawing and update the release record
only when the corresponding evidence exists.

## references

- [Mu power guide](https://docs.lattepanda.com/content/mu_edition/design_guide_power/)
- [Mu specifications](https://docs.lattepanda.com/content/mu_edition/specification/)
- [I-PEX CABLINE-VS](https://www.i-pex.com/product/cabline-vs)
- [I-PEX CABLINE-CA II](https://www.i-pex.com/product/cabline-ca-II)
- [I-PEX 82691 drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_MCX_HARNESS_CABLINE-VS_40P_HARNESS_82691C0.pdf)
- [I-PEX VS plug drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_CABLINE-VS_PLUG_CABLE_ASSEMBLY_20453C38.pdf)
- [I-PEX VS handling manual](https://www.i-pex.com/sites/default/files/downloads/pdf/MANUAL_CABLINE-VS_HIM-08004-08EN.pdf)
- [I-PEX CA II receptacle drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_CABLINE-CA_II_RECEPTACLE_20682C17.pdf)
- [I-PEX CA II plug drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_CABLINE-CA_II_PLUG_CABLE_ASSEMBLY_20679C14.pdf)
- [secondary panel listing](https://www.panelook.com/B160QAN03.K_AUO_16.0_LCM_overview_68142.html), a lead for identification, not the panel's approval specification
