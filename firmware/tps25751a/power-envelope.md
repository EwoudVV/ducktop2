# PD current and power allowance

the corrected hardware uses a programmed IINDPM ceiling of 2.50 A and fixed
15/20 V contracts up to 3 A. their nominal difference is 0.50 A. that is not
a guaranteed extra 0.50 A for the raw-port AON supply.

use these bounds before releasing a load profile:

- raw AON current allowance = source minimum available current minus the
  charger's maximum actual regulated input current;
- minimum board voltage = source minimum voltage minus the released cable,
  connector, protection and trace voltage-drop allowance;
- raw AON power allowance = minimum board voltage times that current allowance;
- minimum charger input power = minimum board voltage times the charger's
  minimum actual regulated input current.

the BQ25798 SLUSDV2C current-regulation table gives 500, 1000, 2000 and 3000 mA
settings at VBUS = 9 V and TJ above -20 C. for example, the 3000 mA setting is
specified at 2720..2920 mA in those conditions. it does not establish a
2.50 A / 15 V or 20 V bound across the intended temperature range. a linear
interpolation is not a guaranteed specification.

`tools/calculate_pd_headroom.py` takes explicit minimum/maximum limits. it
does not manufacture missing bounds or qualify them. as an arithmetic-only
example, a 3.00 A minimum source and a 2.75 A maximum actual charger draw leave
250 mA. at a 19.0 V source floor with 0.2 V path drop, that is 4.70 W before
the AON converter's own losses. 2.75 A is an example input, not a TI guarantee.

exact source, charger-current, path-drop and AON demand bounds remain
unqualified. the 85% portable power model is not a substitute for them.
boot, pack bridge, charging and load qualification switches remain disabled.

## simultaneous running and charging

the new design needs to charge while running, during startup and while
shut down. it also needs to use 5 V and 9 V inputs with battery assistance
when the input is too small. the current 15/20 V input selector and PD
acceptance rules still need to be changed for that.

the calculator now has an optional operating budget. it needs explicit
system load, reserve, converter efficiency and output-current limits, along
with the pack voltage, allowed discharge current and path efficiency.
it reports charging headroom, battery assistance and any load reduction
needed. battery assistance never counts as charging.

the converter output limit includes the system and charging current.
for example, a 6 A output limit at 10 V caps this path at 60 W, even with
a 100 W adapter. this is why the charger cannot be chosen from its USB-C
input rating alone. the example is arithmetic, not a released load profile.
