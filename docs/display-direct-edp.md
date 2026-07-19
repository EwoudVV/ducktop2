# Ducktop2 direct-eDP display release contract

## Architecture decision

The final laptop is intended to use the LattePanda Mu module's onboard eDP
connector directly. The Intehill controller is a proven bench fixture and
fallback, not a populated motherboard subsystem.

The installed replacement panel has been physically verified on the Intehill
controller at 2560x1600 and 120 Hz. Its label identifies:

- AUO `B160QAN03.K`
- hardware `HW:0A`, firmware `FW:1`
- EDID identity `AUO30A5`
- Dell part `0P3FPJ`

That successful Intehill test proves the panel works. It does not prove that a
generic 40-pin eDP cable is electrically compatible with the Mu connector.

## Known connector mechanics

| Endpoint | Installed receptacle | Required cable-side assembly |
| --- | --- | --- |
| LattePanda Mu | I-PEX CABLINE-VS `20455-040E`, 40 pin, 0.5 mm pitch | `20453-240T-03`: housing `20454-240T`, shell `2574-0402`, insulated pull bar `2576-140-00` |
| AUO B160QAN03.K | Likely I-PEX CABLINE-CA II `20682-040E-02`, 40 pin, 0.4 mm pitch; this is not yet confirmed by an AUO approval specification | Conditional on that receptacle ID: `20679-040T-01`, housing `20680-040T-01`, shell `3204-0401`, lock bar `20681-040T-01` |

The LattePanda endpoint is confirmed by the current official Mu repository.
LattePanda omits the complete receptacle suffix; current I-PEX literature lists
`20455-040E-76`, so the installed suffix and pin-1 datum still need microscope
confirmation. The panel-side connector association currently comes from a
secondary panel catalog and must be verified from the physical connector or an
AUO/Dell approval specification.

The intended solution is a purchased, finished 200-300 mm micro-coax harness,
not a hand-built cable. If physical inspection confirms that the panel also
uses CABLINE-VS and the verified contact map is 1:1, I-PEX publishes stock
40-pin assemblies `82691` (200 mm) and `82692` (300 mm). If the panel instead
uses the currently suspected 0.4 mm CABLINE-CA II receptacle, a stock
CABLINE-VS-to-VS cable cannot mate and a cable-assembly vendor must build a
passive VS-to-CA-II harness from a released wiring drawing.

In either case, the drawing or purchased-cable specification must resolve every
individual `Mu pin + signal -> panel pin + signal` connection. Descriptions
such as "generic 40-pin eDP", "same-side", "reverse", or "1-to-N" are not
sufficient by themselves. The working Intehill cable is the physical and
continuity-map reference for the panel end.

References:

- [Official LattePanda Mu eDP pinout](https://github.com/LattePandaTeam/LattePanda-Mu/blob/main/Electricals/Pinouts/README.md)
- [I-PEX CABLINE-VS product family](https://www.i-pex.com/product/cabline-vs)
- [I-PEX 82691 200 mm 1:1 40-pin harness drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_MCX_HARNESS_CABLINE-VS_40P_HARNESS_82691C0.pdf)
- [I-PEX 20453 cable assembly drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_CABLINE-VS_PLUG_CABLE_ASSEMBLY_20453C38.pdf)
- [I-PEX CABLINE-VS handling manual](https://www.i-pex.com/sites/default/files/downloads/pdf/MANUAL_CABLINE-VS_HIM-08004-08EN.pdf)
- [I-PEX CABLINE-CA II product family](https://www.i-pex.com/product/cabline-ca-II)
- [I-PEX 20682 receptacle drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_CABLINE-CA_II_RECEPTACLE_20682C17.pdf)
- [I-PEX 20679 cable assembly drawing](https://www.i-pex.com/sites/default/files/downloads/pdf/2D_CABLINE-CA_II_PLUG_CABLE_ASSEMBLY_20679C14.pdf)
- [Secondary B160QAN03.K connector association](https://www.panelook.com/B160QAN03.K_AUO_16.0_LCM_overview_68142.html)

## Confirmed Mu contact map

The official Mu pin table resolves the complete module side of the harness.
Panel contact numbers remain unresolved and no lane, pair, or polarity reversal
is authorized until the panel approval specification is obtained.

| Mu contact(s) | Signal | Required panel destination |
| --- | --- | --- |
| 1, 34, 35, 40 | NC | Open |
| 2, 5, 8, 11, 14, 17, 23-26, 28-31 | GND | Individually assigned panel grounds, contacts TBD |
| 3 / 4 | DDIA_TX3- / DDIA_TX3+ | Panel lane 3 - / +, contacts TBD |
| 6 / 7 | DDIA_TX2- / DDIA_TX2+ | Panel lane 2 - / +, contacts TBD |
| 9 / 10 | DDIA_TX1- / DDIA_TX1+ | Panel lane 1 - / +, contacts TBD |
| 12 / 13 | DDIA_TX0- / DDIA_TX0+ | Panel lane 0 - / +, contacts TBD |
| 15 / 16 | DDIA_AUX+ / DDIA_AUX- | Panel AUX + / -, contacts TBD |
| 18-21 | LCD_VCC | Panel 3.3 V VDD contacts TBD |
| 22 | Selftest, grounded by default on Mu | Open until the AUO specification defines the panel contact |
| 27 | HPD input | Panel HPD contact TBD |
| 32 | BL_EN output | Panel backlight-enable contact TBD |
| 33 | BL_PWM output | Panel PWM contact TBD |
| 36-39 | BL_PWR | Panel backlight-input contacts TBD |

## Bandwidth

The Mu advertises eDP 1.4 support up to 4K60. The target panel should use all
four lanes. Active video alone is 11.79648 Gbit/s at 8 bits per component and
14.7456 Gbit/s at 10 bits per component, before blanking overhead.

- Four-lane HBR is insufficient: 8.64 Gbit/s payload.
- Four-lane HBR2 is the minimum credible link: 17.28 Gbit/s payload.
- Do not rely on two-lane HBR3 or DSC without confirming the panel DPCD.

Reference: [LattePanda Mu specifications](https://docs.lattepanda.com/content/mu_edition/specification/).

## Electrical release block

Do not order or power a direct-eDP harness yet. The exact Mu contact map is now
public and confirmed, but no public primary AUO/Dell document has been found
that gives the `B160QAN03.K HW0A` contact map and electrical limits.

The Mu endpoint is confirmed to provide `LCD_VCC = 3.3 V` and `BL_PWR` equal to
the Mu input rail. A regulated 12 V input is valid for the Mu and will therefore
put 12 V on `BL_PWR`; that does not prove that 12 V is valid for this exact AUO
panel revision.

The following remain unknown for the exact AUO revision:

- `LCD_VCC` and backlight rail minimum/maximum voltage
- steady-state and inrush current
- backlight-enable level and timing
- PWM voltage, polarity, frequency, and duty-cycle limits
- HPD electrical levels and timing
- required rail power-up and power-down sequence
- exact panel lane/AUX/power contact mapping and connector datum orientation

The Mu power guide states that its eDP backlight converter supply follows Mu
input power. Therefore the motherboard must not feed the Mu from a drifting raw
3S/NVDC rail while the panel limits are unknown; the Mu input rail needs a
defined contract. The separate power audit decides whether that is a regulated
rail or a verified bounded NVDC range.

Reference: [LattePanda Mu power guide](https://docs.lattepanda.com/content/mu_edition/design_guide_power/).

## Measurements required before harness release

1. Obtain the AUO B160QAN03.K HW0A approval specification, or establish every
   panel contact by controlled continuity/back-probe measurements against the
   working Intehill cable and controller. Record both cable-end connector
   markings, pin-1 datums, and all 40 end-to-end connections before buying a
   longer assembly. The Mu contact table above is already fixed.
2. Record panel-pin `LCD_VCC`, backlight power, current/inrush, enable level,
   PWM polarity/frequency, HPD timing, and power-off behavior at 0%, 50%, and
   100% brightness.
3. Capture raw EDID and DPCD. Confirm `AUO30A5`, native 2560x1600 at 120 Hz,
   four active lanes, HBR2 or faster, pixel clock/totals, and color depth.
4. Measure the final connector-datum-to-datum route through the hinge at every
   opening angle before specifying harness length and bend geometry.
5. Microscope-confirm both receptacle markings, complete suffixes, and pin-1
   datums. Continuity-test all 40 conductors and verify no shorts before mating
   either end. Confirm 100 ohm differential construction, skew/loss budget,
   power-wire gauge, insulation, hinge bend radius, and flex life with the
   cable vendor.
6. Live validation must cover cold boot, warm boot, sleep/resume, brightness
   control, full-resolution 120 Hz operation, and link-error monitoring.

Until these items are closed, direct eDP is the selected architecture but not
an electrically released cable assembly.
