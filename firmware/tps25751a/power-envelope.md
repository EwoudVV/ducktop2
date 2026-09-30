# PD current and power allowance

the 29 september profiles request up to 100 W: 3 A at 5, 9 and 15 V,
and 5 A at 20 V. the EC uses the actual negotiated current. a 100 W
profile does not make a 3 A cable or a smaller adapter supply 5 A.

these profiles belong to the ISL9241 redesign, which is still being
integrated into the schematics and boards. the old BQ25798 hardware must
not use them. no controller has been programmed with this revision.

the EC first reserves 250 mA on PD inputs and 6.5 W for standby. it uses
a source-voltage floor that includes supply tolerance, cable drop and the
raw-input wiring. it then derates the charger command for current-sense
resistance and charger error, rounds down to a 4 mA register step, and
keeps the 4.4 A command ceiling.

the current-transfer screen uses 0.919..1.081 of nominal shunt resistance,
0.975..1.025 gain and a 50 mA offset in nominal-shunt units. these bounds
include the named datasheet points but still require board qualification
across the actual voltage, current, temperature and transient range.
`DUCKTOP2_CHARGER_CURRENT_QUALIFIED` remains off. boot, charging and USB
load qualification cannot bypass it.

| input contract | charger command | lower current used for the power budget |
| --- | ---: | ---: |
| 5 V / 3 A | 992 mA | 848 mA |
| 9 V / 3 A | 1676 mA | 1465 mA |
| 15 V / 3 A | 1984 mA | 1742 mA |
| 20 V / 3 A | 2096 mA | 1843 mA |
| 20 V / 5 A | 3884 mA | 3456 mA |

these are conservative design settings, not measured output ratings. the
100 W port rating does not promise 100 W for loads. converter loss, the
remaining system demand and charging come out of the available power.
the 60 W Mu/display setting is a ceiling, not a minimum entitlement.

charging gets its own current-error calculation using the battery shunt,
regulation error and the maximum charging voltage. a qualified 500 mA
pack ceiling is therefore not written directly as a 500 mA command. the
64 mA precharge setting and its error are included. budgets below 1850 mW
are cleared to zero, so the driver is not given an unusable small command.

`tools/calculate_pd_headroom.py` takes explicit minimum and maximum bounds.
it checks source current left after the charger, voltage lost in the path,
and the power remaining at the board. its inputs must come from component
limits or measurements; it does not qualify them itself.

## running and charging

the laptop can use spare input power to charge while running, starting up
or shut down. 5 V and 9 V operation uses the buck-boost charger. if a small
adapter cannot cover the running load, the qualified battery can supply
the difference. battery assistance does not count as charging.

the operating budget includes system loads, reserves, converter efficiency,
output-current limits and the allowed battery current. processor power,
USB loads and charging share what is available. the charger output limit
also applies to the combined system and charging current.

software tests cover weak contracts, source changes and charging without
the OS. startup, negotiation, transient current, converter stability and
physical load tests remain. all charging, boot, pack-bridge and USB load
qualification switches remain off.
