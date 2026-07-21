# Ducktop2 Electrical Calculations

Generated: 2026-07-20

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
| BQ7791500 shunt dissipation at LTC4368 worst-case trip | 0.2428 W | 0 to 0.3 W | PASS | I(LTC4368 max)^2*RS11; RS11 is rated 2W |
| BQ7791500 internal balance current nominal | 25.93 mA | 25 to 27 mA | PASS | 4.2V/(2*R841+12ohm typical internal balance FET) |
| BQ7791500 internal balance current worst-case maximum | 27.09 mA | 0 to 30 mA | PASS | 4.24V/(2*R841*0.99+8ohm); below TI 50mA maximum |
| BQ7791500 internal balance filter capacitance | 1 uF | 0.99 to 1.01 uF | PASS | C842-C844/C848 are contract-checked at TI's 1uF internal-balance value |
| BQ25798 fixed TS divider | 58.87 % REGN | 58 to 60 % REGN | PASS | R705/(R16+R705); inside the default 44.8%-68.4% normal-temperature window |
| TPS259470A aggregate AON acceptance UV rising | 6.196 V | 6.1 to 6.3 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R795/R796/R797 |
| TPS259470A aggregate AON acceptance OV rising | 22.4 V | 22.1 to 22.7 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R795/R796/R797 |
| TPS259470A aggregate AON UV rising worst-case minimum | 6.06 V | 6.02 to 6.1 V | PASS | R795/R796/R797 at 0.1%, VUV=1.183V, and both pin leakages at corners |
| TPS259470A aggregate AON UV rising worst-case maximum | 6.363 V | 6.32 to 6.4 V | PASS | R795/R796/R797 at 0.1%, VUV=1.223V, and both pin leakages at corners |
| TPS259470A aggregate AON OV rising worst-case minimum | 21.97 V | 21.8 to 22.1 V | PASS | R795/R796/R797 at 0.1%, VOV=1.183V, and both pin leakages at corners |
| TPS259470A aggregate AON OV rising worst-case maximum | 22.94 V | 22.7 to 23 V | PASS | R795/R796/R797 at 0.1%, VOV=1.223V, and both pin leakages at corners; below 23V recommended input maximum |
| AON rejection margin above USB-C default 5V maximum | 0.5598 V | 0.5 to 0.7 V | PASS | AON UVLO worst-case minimum-5.5V; a 5V-only source is negotiation-only and cannot boot the EC |
| AON acceptance margin at minimum 7V AUX | 0.1367 V | 0.1 to 0.3 V | PASS | 7.0V minimum AUX-0.5V conservative Schottky drop-AON UVLO worst-case maximum |
| AON acceptance margin at minimum 15V PDO | 7.387 V | 7 to 8 V | PASS | 15V PDO at -5%-0.5V conservative Schottky drop-AON UVLO worst-case maximum |
| TPS259470A aggregate AON current limit nominal | 1.509 A | 1.45 to 1.56 A | PASS | 3334/R798, TI Equation 5 |
| TPS259470A aggregate AON current limit worst-case minimum | 1.276 A | 1.25 to 1.35 A | PASS | TPS25947 table minimum scaled from 3.32kOhm and R798 +0.1% |
| TPS259470A aggregate AON current limit worst-case maximum | 1.729 A | 1.65 to 1.75 A | PASS | TPS25947 table maximum scaled from 3.32kOhm and R798 -0.1% |
| TPS259470A aggregate AON output slew | 0.6061 V/ms | 0.55 to 0.67 V/ms | PASS | 2000/C799(pF), TI Equation 4 |
| TPS26630 PD1 eFuse acceptance UV rising | 12.35 V | 12.1 to 12.6 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R2080/R2081/R2082 |
| TPS26630 PD1 eFuse acceptance OV rising | 17.31 V | 17 to 17.6 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R2080/R2081/R2082 |
| TPS26630 PD1 eFuse current limit | 2.98 A | 2.9 to 3.1 A | PASS | 18/R2083(kOhm) |
| TPS26630 PD2 eFuse acceptance UV rising | 12.35 V | 12.1 to 12.6 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R2090/R2091/R2092 |
| TPS26630 PD2 eFuse acceptance OV rising | 17.31 V | 17 to 17.6 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R2090/R2091/R2092 |
| TPS26630 PD2 eFuse current limit | 2.98 A | 2.9 to 3.1 A | PASS | 18/R2093(kOhm) |
| USB-C PD1 nominal pre-attach VBUS capacitance | 5.84 uF | 5.8 to 5.9 uF | PASS | C2015+C2016+C2017+C2018+C2019+C795+C796 |
| USB-C PD1 worst-case pre-attach VBUS capacitance | 7.508 uF | 0 to 10 uF | PASS | nominal*1.20 + 0.5uF conservative unmodeled allowance; USB Type-C max 10uF |
| USB-C PD2 nominal pre-attach VBUS capacitance | 5.84 uF | 5.8 to 5.9 uF | PASS | C2055+C2056+C2057+C2058+C2059+C795+C796 |
| USB-C PD2 worst-case pre-attach VBUS capacitance | 7.508 uF | 0 to 10 uF | PASS | nominal*1.20 + 0.5uF conservative unmodeled allowance; USB Type-C max 10uF |
| LTC4418 PD1 selector acceptance UV rising | 13.05 V | 12.8 to 13.3 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R2140/R2141/R2142 |
| LTC4418 PD1 selector acceptance OV rising | 17.08 V | 16.7 to 17.5 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R2140/R2141/R2142 |
| LTC4418 PD2 selector acceptance UV rising | 13.05 V | 12.8 to 13.3 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R2143/R2144/R2145 |
| LTC4418 PD2 selector acceptance OV rising | 17.08 V | 16.7 to 17.5 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R2143/R2144/R2145 |
| LTC4418 USB acceptance UV rising | 13.05 V | 12.8 to 13.3 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R730/R731/R732 |
| LTC4418 USB acceptance OV rising | 17.08 V | 16.7 to 17.5 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R730/R731/R732 |
| LTC4418 AUX acceptance UV rising | 5.592 V | 5.3 to 5.9 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R733/R734/R735 |
| LTC4418 AUX acceptance OV rising | 23.32 V | 22.5 to 24 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R733/R734/R735 |
| TPS26630 AUX protection UV rising | 5.527 V | 5.3 to 5.8 V | PASS | VREF*(Rtop+Rmid+Rbot)/(Rmid+Rbot), R711/R712/R713 |
| TPS26630 AUX protection OV rising | 22.99 V | 22.5 to 23.5 V | PASS | VREF*(Rtop+Rmid+Rbot)/Rbot, R711/R712/R713 |
| TPS26630 AUX current limit | 2.98 A | 2.9 to 3.1 A | PASS | 18/R710(kOhm) |
| TPS26630 AUX PGOOD rising nominal | 5.282 V | 5.2 to 5.35 V | PASS | 1.2V*(1+R739/R740) |
| TPS26630 AUX PGOOD rising worst-case minimum | 5.168 V | 5.1 to 5.25 V | PASS | 1.176V*(1+R739*0.999/(R740*1.001)) |
| TPS26630 AUX PGOOD rising worst-case maximum | 5.396 V | 5.3 to 5.45 V | PASS | 1.224V*(1+R739*1.001/(R740*0.999)) |
| BQ25798 hardware input-current ceiling | 3.002 A | 2.9 to 3.1 A | PASS | (5V*R190/(R17+R190)-1V)/(0.8V/A) |
| 15V PD usable input budget with firmware reserve | 41.28 W | 40 to 42 W | PASS | 15V*(ILIM ceiling-0.25A); firmware also caps IINDPM from the active TPS25751A PDO/RDO |
| TPS56637 SYS_5V set-point | 5.208 V | 5.18 to 5.23 V | PASS | 0.6V*(1+R40/R41) |
| TPS56637 SYS_5V worst-case minimum | 5.121 V | 5.1 to 5.15 V | PASS | 0.591V*(1+R40*0.999/(R41*1.001)) |
| TPS56637 SYS_5V worst-case maximum | 5.295 V | 5.25 to 5.35 V | PASS | 0.609V*(1+R40*1.001/(R41*0.999)) |
| HDMI +5V guaranteed connector minimum | 4.864 V | 4.8 to 5.25 V | PASS | SYS_5V(min)-0.002V TPS22975 drop-0.205V TPD13S523 drop-0.050V board/connector allowance |
| TPS56637 SYS_5V nominal output capacitance | 44 uF | 40 to 100 uF | PASS | C44+C45; effective capacitance under DC bias remains a release hold |
| TPS56637 SYS_3V3 set-point | 3.318 V | 3.25 to 3.35 V | PASS | 0.6V*(1+R43/R44) |
| Hub USB-C J22 TPS2553D nominal current limit | 1.319 A | 1.15 to 1.5 A | PASS | 26.38/R1780(kOhm) |
| Hub USB-C J22 TPS2553D minimum current limit | 1.168 A | 1.15 to 1.5 A | PASS | 23.36/R1780(kOhm) |
| Hub USB-C J22 TPS2553D maximum current limit | 1.492 A | 1.15 to 1.5 A | PASS | 29.84/R1780(kOhm) |
| Hub USB-C J23 TPS2553D nominal current limit | 1.319 A | 1.15 to 1.5 A | PASS | 26.38/R1740(kOhm) |
| Hub USB-C J23 TPS2553D minimum current limit | 1.168 A | 1.15 to 1.5 A | PASS | 23.36/R1740(kOhm) |
| Hub USB-C J23 TPS2553D maximum current limit | 1.492 A | 1.15 to 1.5 A | PASS | 29.84/R1740(kOhm) |
| Hub USB-C J12 TPS2553D nominal current limit | 1.319 A | 1.15 to 1.5 A | PASS | 26.38/R1760(kOhm) |
| Hub USB-C J12 TPS2553D minimum current limit | 1.168 A | 1.15 to 1.5 A | PASS | 23.36/R1760(kOhm) |
| Hub USB-C J12 TPS2553D maximum current limit | 1.492 A | 1.15 to 1.5 A | PASS | 29.84/R1760(kOhm) |
| Internal trackpad TPS2553D nominal current limit | 0.6106 A | 0.53 to 0.7 A | PASS | 26.38/R252(kOhm) |
| Internal trackpad TPS2553D minimum current limit | 0.5407 A | 0.53 to 0.7 A | PASS | 23.36/R252(kOhm) |
| Internal trackpad TPS2553D maximum current limit | 0.6907 A | 0.53 to 0.7 A | PASS | 29.84/R252(kOhm) |
| Keyboard RGB TPS2553D nominal current limit | 0.3967 A | 0.39 to 0.41 A | PASS | TPS2553D datasheet ILIM table interpolation; 26.38/R388(kOhm) |
| Keyboard RGB TPS2553D minimum current limit | 0.3513 A | 0.34 to 0.36 A | PASS | TPS2553D lower tolerance; 23.36/R388(kOhm) |
| Keyboard RGB TPS2553D maximum current limit | 0.4487 A | 0.44 to 0.46 A | PASS | TPS2553D upper tolerance; 29.84/R388(kOhm), below 0.5A/contact |
| TPS54202 MCU_3V3 set-point | 3.293 V | 3.25 to 3.35 V | PASS | 0.596V*(1+R35/R36) |
| TPS54202 inductor versus 28V design minimum | 10 uH | 9.70357 to 10.5 uH | PASS | L3; Lmin=3.3V*(28V-3.3V)/(28V*0.30*2A*500kHz) |
| TPS54202 full-load peak inductor current | 2.364 A | 2 to 3.3 A | PASS | TI Eq.10 at 28V/2A; upper band is XGL5030-103 20%-drop Isat |
| TPS54202 nominal ceramic output capacitance | 44 uF | 43 to 45 uF | PASS | C39+C291; DC-bias derating remains a layout/bench hold |
| TPS54202 feed-forward capacitor | 56 pF | 53 to 59 pF | PASS | C292; TI 3.3V recommended-component table |
| TPS54302 RADIO_4V0 set-point | 4.021 V | 3.95 to 4.08 V | PASS | 0.596V*(1+R221/R222) |
| PE42820 control worst-case maximum | 3.47 V | 0 to 3.55 V | PASS | RADIO_4V0(max)*R227(max)/(R242(min)+R227(max)); PE42820 absolute max is 3.6V |
| TPS54302 worst-case full-load ripple ratio | 0.4213 ratio | 0 to 0.45 ratio | PASS | SYS_5V(max), L70 -20%, fSW(min)=290kHz; KIND is designer-selected per TI Eq.8 |
| TPS54302 worst-case full-load peak current | 3.632 A | 3 to 4 A | PASS | Worst-case ripple at 3A; upper band is TPS54302 guaranteed minimum high-side current limit |
| XGL5030-332 worst-case full-load RMS current | 3.022 A | 3 to 6 A | PASS | TI Eq.9; upper band is below Coilcraft 7.2A 20C-rise Irms with margin |
| XGL5030-332 peak versus 20%-drop Isat | 3.632 A | 3 to 6 A | PASS | Worst-case peak current; XGL5030-332 20%-drop Isat is 6.0A |
| TPS54302 nominal ceramic output capacitance | 44 uF | 43 to 45 uF | PASS | C222+C225; DC-bias derating remains a layout/bench hold |
| TPS54302 feed-forward capacitor | 56 pF | 53 to 59 pF | PASS | C224; interpolated starting point between TI 3.3V and 5V table rows |
| TPS552892 MU_12V set-point | 12.03 V | 11.9 to 12.15 V | PASS | 1.2V*(1+R753/R754) |
| TPS552892 output-current limit | 3.333 A | 3.2 to 3.5 A | PASS | 50mV/RS750 |
| TPS552892 output-current worst-case minimum | 3.168 A | 3.1 to 3.25 A | PASS | 48mV/(RS750*1.01); current-threshold minimum and shunt +1% |
| TPS552892 output-current worst-case maximum | 3.502 A | 3.45 to 3.55 A | PASS | 52mV/(RS750*0.99); current-threshold maximum and shunt -1% |
| TPS552892 total MU_12V worst-case low ceiling | 37.74 W | 37.5 to 38.5 W | PASS | MU_12V*0.99*Ilimit_min; shared by Mu, eDP backlight, and fan |
| TPS552892 total MU_12V worst-case high ceiling | 42.55 W | 42 to 43 W | PASS | MU_12V*1.01*Ilimit_max; shared by Mu, eDP backlight, and fan |
| Delta blower worst-case rail power | 3.16 W | 3 to 3.3 W | PASS | MU_12V high corner*0.26A fan datasheet maximum |
| Delta blower PTC hold-current margin | 2.885 x | 2.5 to 3.2 x | PASS | F200 hold current/BFB04512HHA-CZ0T 0.26A maximum |
| Delta blower FG RC cutoff | 4.977 kHz | 4.5 to 5.5 kHz | PASS | 1/(2*pi*R206*C209); Delta typical is 8.2k/4nF |
| Delta blower FG filter/pulse ratio | 24.48 x | 20 to 30 x | PASS | FG RC cutoff/(6100RPM*2 pulses/rev/60) |
| MU_12V headroom after normal Mu/eDP budget and maximum fan | 4.58 W | 4 to 8 W | PASS | MU_12V low current-limit ceiling-normal Mu/eDP budget-fan maximum |
| System reserve remaining after maximum fan | 2.84 W | 2.5 to 4 W | PASS | EC system reserve-fan maximum; remaining reserve covers mandatory support loads |
| TPS552892 rising UVLO | 9.015 V | 8.8 to 9.2 V | PASS | 1.23V*(1+R759/R760), hysteresis excluded |
| TPS552892 rising UVLO worst-case minimum | 8.645 V | 8.55 to 8.75 V | PASS | 1.20V*(1+R759*0.99/(R760*1.01)) |
| TPS552892 rising UVLO worst-case maximum | 9.396 V | 9.3 to 9.5 V | PASS | 1.26V*(1+R759*1.01/(R760*0.99)) |
| Mu fail-off Q750 gate at 8.45V VSYS | 4.225 V | 4 to 4.5 V | PASS | 8.45V*R761/(R766+R761); reset-state gate divider |
| TPS552892 switching frequency | 400.8 kHz | 380 to 420 kHz | PASS | 20e9/R756 |
| Low-pack derated source power minus enforced firmware budget | 0.7078 W | 0.5 to 10 W | PASS | 0.80*LTC4368 pack UV*breaker_min-(EC low-pack Mu+eDP budget/efficiency)-EC system reserve |
| Built-in microphone audio-band gain | 5.99 V/V | 5.9 to 6.1 V/V | PASS | 1+R432/R433; C454 restores unity DC gain |
| Built-in microphone low-frequency gain shelf | 33.86 Hz | 32 to 36 Hz | PASS | 1/(2*pi*R433*C454) |
| Built-in microphone feedback pole | 26.58 kHz | 24 to 28 kHz | PASS | 1/(2*pi*R432*C453) |
| Built-in microphone typical ADC headroom at 94dBSPL | 19.35 dB | 18.8 to 19.8 dB | PASS | PCM2900 0.6*3.3Vpp full scale versus IM68 -38dBV/Pa times preamp gain |
| Built-in microphone worst-case ADC headroom at 94dBSPL | 17.81 dB | 17.2 to 18.4 dB | PASS | PCM2900 0.6*3.1Vpp minimum rail versus IM68 -37dBV/Pa maximum sensitivity |
| Built-in microphone nominal self-noise at ADC | -87.35 dBFS | -88 to -86.5 dBFS | PASS | -(94dBSPL headroom + IM68 68dBA SNR); PCM2900 ADC SNR is 89dB typical |
| RTL8111H 25MHz crystal effective load | 8 pF | 7.8 to 8.2 pF | PASS | (C515*C516)/(C515+C516)+2.0pF assumed pin/PCB stray; Y500 CL=8pF |
| LTC4418 dual-PD selector handoff droop | 0.3302 V | 0 to 0.4 V | PASS | BQ ILIM ceiling*(7us VALID-off max+4us break-before-make max)/C2146; ESR and adapter loss excluded |
| LTC4418 PD/AUX selector handoff droop | 0.3302 V | 0 to 0.4 V | PASS | BQ ILIM ceiling*(7us+4us)/C746; ESR and source loss excluded |
| STM32 HSE effective crystal load | 8 pF | 7.75 to 8.25 pF | PASS | C32/2+3.0pF assumed PCB/pin stray; C32=C33=10pF |
| STM32 HSE critical transconductance | 0.6832 mA/V | 0 to 1 mA/V | PASS | 4*ESR*(2*pi*f)^2*(C0+CL)^2; ESRmax=400ohm, C0max=5pF |
| STM32 HSE startup gain-margin screen | 7.319 x | 5 to 20 x | PASS | STM32 gm_min/gmcrit; gm_min=5mA/V |
| STM32 LSE effective crystal load | 6 pF | 5.75 to 6.25 pF | PASS | C34/2+2.6pF assumed PCB/pin stray; C34=C35=6.8pF |
| STM32 LSE critical transconductance | 0.4154 uA/V | 0 to 0.56 uA/V | PASS | 4*ESR*(2*pi*f)^2*(C0+CL)^2; ESRmax=50kohm, C0typ=1.0pF |
| STM32 LSE startup gain-margin screen | 6.74 x | 5 to 20 x | PASS | STM32 gm_min/gmcrit; gm_min=2.8uA/V |

Result: **123 PASS, 0 FAIL**.

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

Mainboard netlist evidence: `verification/electrical_calculations_netlist.xml`
Radio daughterboard netlist evidence: `verification/radio_electrical_calculations_netlist.xml`
