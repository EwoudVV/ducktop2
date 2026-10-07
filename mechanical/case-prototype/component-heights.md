# component clearance around the power wires

6 october 2026. the 31 missing-height records covered 21 footprints, with
several repeated under different wires. the wider clearance screen also
picked up R2443, C2285 and J2073. all 189 current wire/component crossings
now have a recorded height basis. this covers the power-wire paths, not
every part or cable in the laptop.

## manufacturer dimensions

maximum dimensions come from the exact part or the manufacturer's named
package. the check adds 0.3 mm of assembly space above these maxima.

| part | maximum height | drawing |
| --- | ---: | --- |
| TPS22948DCKR | 1.10 mm | [TI DCK0006A, page 18](https://www.ti.com/lit/ds/symlink/tps22948.pdf) |
| CC0402KRX7R9BB183 | 0.55 mm | [Yageo exact-part sheet](https://yageogroup.com/download/specsheet/CC0402KRX7R9BB183), 0.50 +/-0.05 mm |
| GRM155R71E473KA88D | 0.55 mm | [Murata reference sheet, page 2](https://www.mouser.com/datasheet/3/76/1/GRM155R71E473KA88-01A.pdf), 0.50 +/-0.05 mm |
| LM706A0RRXR | 1.00 mm | [TI RRX0029B, page 53](https://www.ti.com/lit/ds/symlink/lm706a0.pdf) |
| RP2350A, A4 stepping | 0.90 mm | [Raspberry Pi QFN-60 outline, page 6](https://datasheets.raspberrypi.com/rp2350/rp2350-product-brief.pdf) |
| SN74CB3T3245PWR | 1.20 mm | [TI PW0020A, page 24](https://www.ti.com/lit/ds/symlink/sn74cb3t3245.pdf) |
| XGL1060-822MEC | 6.00 mm | [Coilcraft document 1735, pages 1 and 3](https://www.coilcraft.com/pdfs/xgl1060.pdf) |
| ERJ3RQFR33V | 0.55 mm | [Panasonic ERJ3R outline, page 5](https://industrial.panasonic.com/cdbs/www-data/pdf/RDN0000/AOA0000C313.pdf), 0.45 +/-0.10 mm |
| T520X337M010ATE010 | 4.30 mm | [KEMET exact-part sheet](https://search.kemet.com/download/specsheet/T520X337M010ATE010), 4.0 +/-0.3 mm |

the RP2350 A4 requirement is unchanged. package thickness does not establish
which silicon stepping a supplier will ship.

## space reserved for assembly

these are dimensions to meet when assembling the laptop. they are not
measured heights or guaranteed manufacturer maxima. `height-allowances.json`
binds each one to its exact footprint and part number so a replacement
cannot silently inherit the same clearance result.

| footprint | reserved above its PCB | basis and remaining fit check |
| --- | ---: | --- |
| center H24 | 2.80 mm | modeled 2 mm nylon head and 0.5 mm washer, plus 0.3 mm clearance |
| center J10 | 5.00 mm | [Amphenol socket](https://www.amphenol-cs.com/product/mdt420m01001.html) is nominally 4.2 mm; confirm the seated socket, full SSD and insertion space separately |
| center J54 | 4.60 mm | [JST GH side-entry connector](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf); confirm the complete mated plug and thermistor lead dressing |
| center J2073 | 3.20 mm | [JST SH connector](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf), 2.95 mm nominal mated height; confirm plug seating and control-wire dressing |
| center J58 | 4.00 mm | existing allowance for trackpad cable, solder and insulation |
| center J2432, J2450, J2452, J2462 | 4.80 mm | WAGO nominal 4.5 mm body plus 0.3 mm assembly space; release-tool access is checked separately |
| center J2446 and right J2447 | 1.00 mm | finished braid and solder joints; nominal braid is 0.508 mm thick |
| center TP6, TP2660, TP2661 | 1.00 mm | bare test pads with solder allowance; no fitted pins or permanent test leads |

the braid windows, screw hardware and WAGO release envelopes also have
solid-geometry checks. probe access and the full control/signal-cable
routes still need work. the bare test pads are not assumed to have zero
assembly height just because they lack a purchase part number.

## guide clearance

the old screen subtracted a full guide radius anywhere its top-view
projection touched a courtyard. the revised screen follows the round
cross-section. it retains every path vertex and inserts stations no more
than 0.05 mm apart. half the maximum station spacing enlarges the checked
radius to cover the intervals, with another 0.025 mm for the fitted curve.

the guide radius includes maximum wire OD, 0.15 mm radial fit, 0.4 mm
wall and 0.2 mm position allowance. the check uses the same trimmed guide
points as the CAD builder. beyond those ends, the complete wire remains
checked with its own diameter and position allowance.

right R2045 needed more assembly room beneath the PD2 lead. its guide now
ends 5 mm before J2433's wire entrance instead of 3 mm. the nearby clamp,
wire path, bend radius and cut length are unchanged. the resulting
conservative clearance is 0.324 mm after the resistor's 0.55 mm maximum
height, 0.3 mm assembly space and the wire/guide allowances.

two carrier overhangs also needed local pockets after adding the missing
part heights: the left main carrier over center R2443, and the right USB
carrier over center U913. each pocket follows the saved courtyard with
0.3 mm around its edge and above the maximum component height. these join
the existing pockets over U904 and C2069.

the smallest remaining calculated margin is about 0.035 mm at right U54,
after all those allowances, including its 1.1 mm maximum height and
0.3 mm assembly space. the nominal solid-to-body gap is larger; the small
remaining margin makes this a useful location for the first fit coupon.
check guide warping, mounting accuracy, solder seating and loaded-harness
deflection before printing the complete case.

`harness-case-checks.json` contains every crossing, its source and margin.
`gen/test_case_component_heights.py` checks nominal/max classification,
part-number changes, assembly reservations, round-guide geometry, short
crossings and the exposed wire beyond a trimmed guide.

![shortened guide beside R2045](views/right-power-guide.png)
