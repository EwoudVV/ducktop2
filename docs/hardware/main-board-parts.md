# main-board part selections

the [16 october power placement pass](mainboard-power-placement.md) updates
the PD regulator capacitor banks and three USB protection footprints.

5 october 2026: filled in R450/R451 and replaced 41 incomplete
capacitor codes plus the discontinued C2606 part. the changes cover 42
capacitors on the center and right boards. capacitance, circuit ratings,
footprints, placement and copper are unchanged.

## capacitor order codes

body heights include the manufacturer's positive dimensional tolerance.
solder, board thickness and case clearances need their own allowances.

| parts | manufacturer and order code | nominal rating / package | maximum body height |
| --- | --- | --- | ---: |
| C720, C432, C433, C434, C435, C461, C462, C463, C464 | TDK [C2012X7R1H105K125AB](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X7R1H105K125AB) | 1 uF, 50 V, X7R, +/-10%, 0805 | 1.45 mm |
| C290, C767, C774, C775 | KEMET [C0603C103K5RACTU](https://search.kemet.com/download/specsheet/C0603C103K5RACTU) | 10 nF, 50 V, X7R, +/-10%, 0603 | 0.9 mm |
| C2300 | Murata [GRM155R71H472KA01D](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM155R71H472KA01-01A.pdf) | 4.7 nF, 50 V, X7R, +/-10%, 0402 | 0.55 mm |
| C902, C911, C912, C913, C917 | TDK [C1005X5R1A475K050BC](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1005X5R1A475K050BC) | 4.7 uF, 10 V, X5R, +/-10%, 0402 | 0.65 mm |
| C918, C919 | Murata [GRM1555C1H150JA01D](https://statics3.seeedstudio.com/images/opl/datasheet/302010041.pdf) | 15 pF, 50 V, C0G, +/-5%, 0402 | 0.55 mm |
| C414, C415, C420, C421 | KEMET [C0603C180J5GACTU](https://search.kemet.com/download/specsheet/C0603C180J5GACTU) | 18 pF, 50 V, C0G, +/-5%, 0603 | 0.87 mm |
| C430, C431, C2606 | KEMET [C0603C473K5RACTU](https://search.kemet.com/download/specsheet/C0603C473K5RACTU) | 47 nF, 50 V, X7R, +/-10%, 0603 | 0.95 mm |
| C442, C443, C444, C445 | Murata [GRM155R71H102KA01D](https://www.farnell.com/datasheets/2047936.pdf) | 1 nF, 50 V, X7R, +/-10%, 0402 | 0.55 mm |
| C453 | Murata [GRM1885C1H122JA01D](https://www.murata.com/en-us/products/productdetail?partno=GRM1885C1H122JA01%23) | 1.2 nF, 50 V, C0G, +/-5%, 0603 | 0.9 mm |
| C454, C455, C456 | Murata [GRM319R61C475KA88D](https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/dynamic-model/component-list-d-mlcc-2504.ashx?cvid=20250523010405000000&la=en) | 4.7 uF, 16 V, X5R, +/-10%, 1206 | 0.95 mm |
| C457, C458, C459, C460 | Murata [GRM21BR71H474KA88L](https://docs.rs-online.com/d898/0900766b81423ca7.pdf) | 470 nF, 50 V, X7R, +/-10%, 0805 | 1.35 mm |
| C515, C516 | Murata [GRM1555C1H120JA01J](https://www.mouser.com/datasheet/2/281/1/GRM1555C1H120JA01_01A-1982584.pdf) | 12 pF, 50 V, C0G, +/-5%, 0402 | 0.55 mm |

the last letter on each Murata code identifies its packaging. the old
17-character base codes did not specify an orderable reel or tape option.
the inventory check now flags those incomplete codes. the TDK and KEMET
selections also have explicit value, package, voltage and tolerance checks.

## regulator capacitors

C911 and C912 retain the RP2350 reference-board lands, and C913 retains
the regulator analog-supply filter. the [RP2350 hardware guide](https://datasheets.raspberrypi.com/rp2350/hardware-design-with-rp2350.pdf)
specifies 4.7 uF 0402 capacitors in these positions. the TDK choice has
the same nominal capacitance and 10 V X5R rating as the original selection.

C911/C912 have a 0.56 mm pad gap; TDK's general land recommendation is
0.3..0.5 mm. keep the reference-board geometry and have the assembler
confirm the stencil and solder process for this land pattern. the nominal
4.7 uF rating does not guarantee effective capacitance under DC bias.
check the regulator ripple and load-step response on the assembled board.

## other assembly details

- R450 is Yageo RC0603FR-07100KL, 100k in 0603. R451 is RC0603FR-0710KL, 10k in 0603. both now have manufacturer and part-number fields in the schematic, board and generator.
- U901 requires RP2350A A4 silicon. keep that requirement on the assembly order and confirm the supplied stepping; a quote for an unspecified RP2350A is insufficient.
- F190 and F195 each use one Bel 0678H5000-02 SMD fuse. the old Littelfuse 0297003.WXNV and Keystone 3568 assemblies are removed. [AUX input details](aux-input.md) cover the current budget, footprint and fault-test requirements.
- the three AKZYTUE 1160100 packs are already owned. their confirmed listing is B0FBRGNCJF; the supplier lists 100 x 60 x 11 mm. the replacement wiring and finished insulated pack envelope still need measurements.

## verification

the 5 october check covered all 44 corrected identities and
1,315 populated physical sourcing items, with no missing manufacturer
or part-number fields and no incomplete Murata codes. this is an identity
check, not proof of supplier stock or a completed assembly quote.

fresh schematic exports match all three saved boards. ERC has zero errors;
the 575 warnings match the existing symbol and intentional-connection
records. the capacitor and resistor field edits leave the board geometry
and nets unchanged. 84 passive-identity, power-calculation and battery-path
regression tests pass.

[parts and cost](../bom-and-cost.md) covers the full quote, including the
separate BMS, keyboard, radio, cables and mechanical parts.
