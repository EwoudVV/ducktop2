# PD current and power allowance

the 29 september profiles request up to 100 W: 3 A at 5, 9 and 15 V,
and 5 A at 20 V. the EC uses the actual negotiated current. a 100 W
profile does not make a 3 A cable or a smaller adapter supply 5 A.

these profiles belong to the ISL9241 redesign, which is still being
integrated into the schematics and boards. the old BQ25798 hardware must
not use them. no controller has been programmed with this revision.

the target EC caps the programmed charger input at 4.4 A. it also reserves
250 mA on PD inputs and 6.5 W for the separate always-on branch. the reserve
is converted to current using the source-voltage floor before choosing a
charger limit, then rounded down to an ISL9241 register step. smaller
contracts therefore get a smaller charger limit, even when the ceiling
is 4.4 A.

those are design allocations. the hardware tests still need to establish
maximum actual charger current, always-on demand, cable and board losses,
current-sense error and response during a contract change. the difference
between a contract and a programmed limit is not all available for loads.

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
