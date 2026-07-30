# BOM MPN Assignments — P1.3 Item 3

Generated: 2026-07-30
Source: `BOM_RELEASE_GAPS_2026-07-28.md` — 43 missing Manufacturer/MPN

All suggestions are **Murata GRM series** (widely available at LCSC/Mouser/Digikey).
Tolerance: ±10% (X7R/X5R) or ±5% (C0G) unless noted.

---

## 02_ec_mcu.kicad_sch (4 caps)

| Ref | Value | Package | Voltage | Dielectric | Suggested MPN | Notes |
|-----|-------|---------|---------|------------|---------------|-------|
| C29 | 2.2µF | 0805 | 6.3V | X5R | GRM21BR60J225ME01 | STM32 VCAP — use low-ESR ceramic |
| C30 | 2.2µF | 0805 | 6.3V | X5R | GRM21BR60J225ME01 | STM32 VCAP — use low-ESR ceramic |
| C290 | 10nF | 0603 | 50V | X7R | GRM188R71H103KA01 | VDDA HF decoupling |
| C292 | 56pF | 0402 | 50V | C0G | GRM1555C1H560JA01 | ±5%, feed-forward cap |

## 15_system_audio.kicad_sch (18 caps)

| Ref | Value | Package | Voltage | Dielectric | Suggested MPN | Notes |
|-----|-------|---------|---------|------------|---------------|-------|
| C414 | 18pF | 0603 | 50V | C0G | GRM1885C1H180JA01 | ±5%, hub crystal load |
| C415 | 18pF | 0603 | 50V | C0G | GRM1885C1H180JA01 | ±5%, hub crystal load |
| C420 | 18pF | 0603 | 50V | C0G | GRM1885C1H180JA01 | ±5%, codec crystal load |
| C421 | 18pF | 0603 | 50V | C0G | GRM1885C1H180JA01 | ±5%, codec crystal load |
| C430 | 47nF | 0603 | 50V | X7R | GRM188R71H473KA01 | L DAC out-of-band shunt |
| C431 | 47nF | 0603 | 50V | X7R | GRM188R71H473KA01 | R DAC out-of-band shunt |
| C432 | 1µF | 0805 | 50V | X7R | GRM21BR71H105KA01 | L input AC coupling |
| C433 | 1µF | 0805 | 50V | X7R | GRM21BR71H105KA01 | R input AC coupling |
| C434 | 1µF | 0805 | 50V | X7R | GRM21BR71H105KA01 | L negative-input AC ref |
| C435 | 1µF | 0805 | 50V | X7R | GRM21BR71H105KA01 | R negative-input AC ref |
| C442 | 1nF | 0402 | 50V | X7R | GRM155R71H102KA01 | Speaker EMI shunt |
| C443 | 1nF | 0402 | 50V | X7R | GRM155R71H102KA01 | Speaker EMI shunt |
| C444 | 1nF | 0402 | 50V | X7R | GRM155R71H102KA01 | Speaker EMI shunt |
| C445 | 1nF | 0402 | 50V | X7R | GRM155R71H102KA01 | Speaker EMI shunt |
| C453 | 1.2nF | 0603 | 50V | C0G | GRM1885C1H122JA01 | ±5%, feedback low-pass |
| C454 | 4.7µF | 1206 | 16V | X5R | GRM31CR61C475KA01 | Mic gain AC coupling |
| C455 | 4.7µF | 1206 | 16V | X5R | GRM31CR61C475KA01 | Mic to PCM2900 VINL |
| C456 | 4.7µF | 1206 | 16V | X5R | GRM31CR61C475KA01 | Mic to PCM2900 VINR |

## 16_gigabit_ethernet.kicad_sch (2 caps)

| Ref | Value | Package | Voltage | Dielectric | Suggested MPN | Notes |
|-----|-------|---------|---------|------------|---------------|-------|
| C515 | 12pF | 0402 | 50V | C0G | GRM1555C1H120JA01 | ±5%, crystal load |
| C516 | 12pF | 0402 | 50V | C0G | GRM1555C1H120JA01 | ±5%, crystal load |

## 01_power_battery.kicad_sch (4 caps)

| Ref | Value | Package | Voltage | Dielectric | Suggested MPN | Notes |
|-----|-------|---------|---------|------------|---------------|-------|
| C700 | 3.3nF | 0402 | 50V | X7R | GRM155R71H332KA01 | LTC4368 CGATE |
| C720 | 1µF | 0805 | 50V | X7R | GRM21BR71H105KA01 | AUX input |
| C724 | 4.7nF | 0402 | 50V | X7R | GRM155R71H472KA01 | Pack hot-swap slew |
| C799 | 3.3nF | 0402 | 50V | X7R | GRM155R71H332KA01 | AON eFuse dVdt |

## 03_mu_carrier.kicad_sch (7 caps)

| Ref | Value | Package | Voltage | Dielectric | Suggested MPN | Notes |
|-----|-------|---------|---------|------------|---------------|-------|
| C767 | 10nF | 0603 | 50V | X7R | GRM188R71H103KA01 | DITH/SYNC spreading |
| C770 | 100nF | 0603 | 50V | X7R | GRM188R71H104KA01 | Current-sense filter |
| C771 | 4.7nF | 0603 | 50V | X7R | GRM188R71H472KA01 | COMP |
| C772 | 100pF | 0603 | 50V | C0G | GRM1885C1H101JA01 | ±5%, COMP HF |
| C773 | 100nF | 0603 | 50V | X7R | GRM188R71H104KA01 | UVLO noise filter |
| C774 | 10nF | 0603 | 50V | X7R | GRM188R71H103KA01 | PG deglitch |
| C775 | 10nF | 0603 | 50V | X7R | GRM188R71H103KA01 | CC deglitch |

## 14_maker_mcu.kicad_sch (7 caps)

| Ref | Value | Package | Voltage | Dielectric | Suggested MPN | Notes |
|-----|-------|---------|---------|------------|---------------|-------|
| C902 | 4.7µF | 0402 | 10V | X5R | GRM155R61A475KE15 | Flash bulk |
| C911 | 4.7µF | 0402 | 10V | X5R | GRM155R61A475KE15 | VREG input |
| C912 | 4.7µF | 0402 | 10V | X5R | GRM155R61A475KE15 | 1V1 output |
| C913 | 4.7µF | 0402 | 10V | X5R | GRM155R61A475KE15 | VREG_AVDD |
| C917 | 4.7µF | 0402 | 10V | X5R | GRM155R61A475KE15 | ADC_AVDD filter |
| C918 | 15pF | 0402 | 50V | C0G | GRM1555C1H150JA01 | ±5%, XIN load |
| C919 | 15pF | 0402 | 50V | C0G | GRM1555C1H150JA01 | ±5%, XOUT load |

## 09_radio_daughterboard_interface.kicad_sch (1 cap)

| Ref | Value | Package | Voltage | Dielectric | Suggested MPN | Notes |
|-----|-------|---------|---------|------------|---------------|-------|
| C2300 | 4.7nF | 0402 | 50V | X7R | GRM155R71H472KA01 | Radio eFuse controlled rise |

---

## Summary

| Sheet | Count | Dominant MPN |
|-------|-------|-------------|
| 15_system_audio | 18 | GRM21BR71H105KA01 (×4), GRM31CR61C475KA01 (×3) |
| 03_mu_carrier | 7 | GRM188R71H103KA01 (×3) |
| 14_maker_mcu | 7 | GRM155R61A475KE15 (×5) |
| 02_ec_mcu | 4 | GRM21BR60J225ME01 (×2) |
| 01_power_battery | 4 | GRM155R71H332KA01 (×2) |
| 16_gigabit_ethernet | 2 | GRM1555C1H120JA01 (×2) |
| 09_radio_daughterboard_interface | 1 | GRM155R71H472KA01 |

**Total unique MPNs: ~19** (many values shared across refs)
**Total stock-keeping cost:** ~$2-4 at LCSC/JLCPCB pricing.
