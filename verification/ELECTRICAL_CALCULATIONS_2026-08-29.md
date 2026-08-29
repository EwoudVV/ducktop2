# Ducktop2 Electrical Calculations

Generated: 2026-08-29

These values were recalculated from the component values in a fresh KiCad XML netlist, not copied from generator comments.

| Check | Result | Required band | Status | Equation |
|---|---:|---:|:---:|---|
| LTC4368 pack acceptance UV rising | 8.456 V | 8.2 to 8.7 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R700/R701/R702 |
| LTC4368 pack acceptance OV rising | 13.57 V | 13.2 to 13.8 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R700/R701/R702 |
| LTC4368 bidirectional pack breaker nominal | 4.545 A | 4.4 to 4.7 A | PASS | 50mV/RS10; nominal forward and reverse magnitude |
| LTC4368 breaker worst-case minimum | 3.6 A | 3.5 to 3.7 A | PASS | 40mV/(RS10*1.01); LTC4368 threshold minimum and shunt +1% |
| LTC4368 breaker worst-case maximum | 5.51 A | 5.4 to 5.6 A | PASS | 60mV/(RS10*0.99); LTC4368 threshold maximum and shunt -1% |
| LTC4368 nominal VOUT capacitance | 10 uF | 9.9 to 10.1 uF | PASS | C725 on PACK_POS_FUSED; datasheet requires at least 1uF effective at VOUT |
| BQ7791500 backup overcurrent nominal | 7.5 A | 7.4 to 7.6 A | PASS | BQ7791500PWR 60mV OCD threshold / RS11 |
| BQ7791500 backup overcurrent worst-case minimum | 5.941 A | 5.9 to 6.1 A | PASS | 48mV/(RS11*1.01); protector threshold minimum and shunt +1% |
| BQ7791500 backup overcurrent worst-case maximum | 9.091 A | 9 to 9.2 A | PASS | 72mV/(RS11*0.99); protector threshold maximum and shunt -1% |
| BQ7791500 short-circuit nominal | 15 A | 14.9 to 15.1 A | PASS | BQ7791500PWR 120mV SCD threshold / RS11 |
| BQ7791500 short-circuit worst-case minimum | 11.88 A | 11.8 to 12 A | PASS | 96mV/(RS11*1.01); protector threshold minimum and shunt +1% |
| BQ7791500 short-circuit worst-case maximum | 18.18 A | 18 to 18.2 A | PASS | 144mV/(RS11*0.99); protector threshold maximum and shunt -1% |
| BQ7791500 shunt power at pack trip | 0.2428 W | 0 to 0.3 W | PASS | I(LTC4368 max)^2*RS11; RS11 is rated 2W |
| BQ7791500 balance current nominal | 25.93 mA | 25 to 27 mA | PASS | 4.2V/(2*75R+12R); internal-balance current |
| BQ7791500 balance worst-case max | 27.09 mA | 0 to 30 mA | PASS | 4.24V/(2*75R*0.99+8R); worst-case high balance current |

Result: **15 PASS, 0 FAIL**.

## Scope And Holds

- This is a DC/set-point and selector hold-up calculation, not a substitute for vendor-model loop simulation or bench validation.
- The LTC4368, TPS552892, TPS26630 PGOOD, TPS56637 SYS_5V, TPS54302/PE42820, and TPS2553 rows include the stated IC and/or resistor corners shown in their equations. Other resistor/reference tolerances, capacitor DC-bias derating, capacitor ESR, MOSFET loss, connector/cable loss, thermal rise, and PCB parasitics are not included.
- C725 is 10 uF nominal against the LTC4368 minimum 1 uF effective VOUT requirement. Confirm the selected 25 V X7R part remains above 1 uF at the actual pack bias, tolerance, and temperature before release.
- Each USB-C pre-attach capacitance row includes every explicit raw-port capacitor, the shared AON input capacitors reached through the Schottky OR, +20% capacitance tolerance, and a 0.5 uF unmodeled allowance. Recheck against final fitted parts and parasitics before Type-C compliance testing.
- The two selector droop rows use the 3 A hardware ceiling, datasheet maximum validation-off plus break-before-make times, and only the dedicated 100 uF hybrid capacitor; ESR is still excluded.
- The oscillator rows use ST AN2867's negative-resistance screen with assumed total PCB/pin stray capacitance of 3.0 pF for HSE and 2.6 pF for LSE. These are starting-value calculations, not measured qualification.
- Verify HSE/LSE startup time, frequency error, and crystal drive level on assembled hardware across supply voltage and temperature before release.
- TPS25751A power telemetry and firmware policy are functional requirements: keep the Mu rail disabled until the selected source is valid, read Active PDO (0x31), Active RDO (0x32), and PD Status (0x35), program VSYSMIN/IINDPM, require VSYS >=10.0 V, and cap IINDPM below the negotiated current with a 2.75 A ceiling.
- Verify both TPS25751A service-I2C channels for rise time, powered-off leakage, stale-read rejection, interrupt recovery, and negotiated-contract decoding at 100 kHz and 400 kHz.
- TPS552892 compensation and current-sense filtering must still be reviewed against the final layout and measured on first hardware.
- The tolerance-aware MU_12V ceiling is approximately 38 to 42.5 W and is shared by the complete Mu module, eDP backlight, and Delta blower. The normal 30 W Mu/eDP budget leaves about 4.8 W at the low current-limit corner after the fan's 0.26 A maximum. Measure all three loads and lock BIOS PL1/PL2 accordingly.
- The 6 W firmware system reserve explicitly includes the Delta blower's approximately 3.15 W worst-case rail draw, leaving about 2.85 W for mandatory support loads in the low-pack calculation. HIL power measurements must confirm that assumption with optional loads shed.
- The low-pack row reads the released EC constants directly, derates the minimum hardware breaker power to 80%, includes the firmware source-efficiency assumption and a dedicated system reserve, and requires positive headroom. Exact cell/BMS/harness limits and HIL transient/latch-recovery tests remain release holds.
- The microphone rows verify the nominal small-signal network only. Acoustic sealing, microphone sensitivity spread, ADC headroom, clipping, echo, fan noise, charger noise, and RF desense require assembled-hardware tests.
- The Ethernet crystal row assumes 2.0 pF total pin/PCB stray. Confirm 25 MHz startup and frequency on assembled hardware before production release.

## Primary Sources

- Analog Devices LTC4368: https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4368.pdf
- Analog Devices LTC4417: https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4417.pdf
- Analog Devices LTC4418: https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4418.pdf
- Texas Instruments TPS2663: https://www.ti.com/lit/ds/symlink/tps2663.pdf
- Texas Instruments TPS25947: https://www.ti.com/lit/ds/symlink/tps25947.pdf
- Texas Instruments BQ25798: https://www.ti.com/lit/ds/symlink/bq25798.pdf
- Texas Instruments TPS552892: https://www.ti.com/lit/ds/symlink/tps552892.pdf
- Delta BFB04512HHA-CZ0T: https://www.delta-fan.com/Download/Spec/BFB04512HHA-CZ0T.pdf
- Texas Instruments TPS54202: https://www.ti.com/lit/ds/symlink/tps54202.pdf
- Texas Instruments TPS54302: https://www.ti.com/lit/ds/symlink/tps54302.pdf
- Texas Instruments TPS56637: https://www.ti.com/lit/ds/symlink/tps56637.pdf
- Texas Instruments TPS2553: https://www.ti.com/lit/ds/symlink/tps2553.pdf
- Texas Instruments TPD13S523: https://www.ti.com/lit/ds/symlink/tpd13s523.pdf
- pSemi PE42820: https://www.psemi.com/pdf/datasheets/pe42820ds.pdf
- Texas Instruments PCM2900C: https://www.ti.com/lit/ds/symlink/pcm2900c.pdf
- Texas Instruments TLV9061/TLV9062: https://www.ti.com/lit/ds/symlink/tlv9062.pdf
- Infineon IM68A130: https://www.infineon.com/dgdl/Infineon-IM68A130-DataSheet-v01_10-EN.pdf?fileId=8ac78c8c85ecb34701860371623f1204
- STMicroelectronics AN2867 oscillator design guide: https://www.st.com/resource/en/application_note/an2867-oscillator-design-guide-for-stm8afals-stm32-mcus-and-mpus-stmicroelectronics.pdf
- STMicroelectronics STM32F407 datasheet: https://www.st.com/resource/en/datasheet/stm32f407vg.pdf
- Jauch J32SMX crystal: https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7432/JQG_DB_Q-J32SMX_250618_online.pdf
- Epson FC-135R crystal: https://download.epsondevice.com/td/pdf/td_xtal_32khz/FC-135R_X1A0001410006_en.pdf
- Coilcraft XGL5030: https://www.coilcraft.com/getmedia/e64ac115-95f2-45c7-b798-1b3769b91583/xgl5030.pdf
- Coilcraft XGL5030-332: https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xgl/xgl5030/xgl5030-332/
- Texas Instruments TPS25751A: https://www.ti.com/lit/ds/symlink/tps25751a.pdf
- USB-IF USB Type-C Cable and Connector Specification: https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf
- Texas Instruments TCA9548A: https://www.ti.com/lit/ds/symlink/tca9548a.pdf
- ECS ECS-250-8-33-AGN-TR crystal: https://ecsxtal.com/products/crystals/surface-mount-crystals/ecs-250-8-33-agn-tr/
- ECS ECX-32 crystal datasheet: https://ecsxtal.com/store/pdf/ecx-32.pdf

Mainboard netlist evidence: `verification/bms_netlist.xml`
Radio daughterboard netlist evidence: `verification/radio_electrical_calculations_netlist.xml`
