# bq76922 charging

this profile uses 12.120 v cv, a measured 4.100 v charge-only cell ceiling
and a measured 30 mv cell spread limit. normal charge and discharge still
require every cell at or above 3.100 v. bounded discharge keeps the separate
4.200 v ceiling, including discharge after cov. balancing and recovery
charging stay disabled. the ec does not write bq configuration, fet enable
or otp commands.

legacy hardware keeps its existing 12.528 v charger setting. a nonzero bq
board charge setting must be exactly 12.120 v, and the bq charger driver
rejects values above it. runtime admission also binds the target to the
readback profile's cov code 82 and disabled threshold override.

## voltage and measurements

cov is 4.1492 v nominal with a guaranteed +/-25 mv threshold error over the
bq operating temperature range. the current cv target and 30 mv measured
spread, with calibrated +/-15 mv cell error, give a highest static cell
screen of 4.1002 v under the inherited +0.5% charger model. that is 24 mv
below the earliest cov trip. the measured 4.100 v ceiling and +/-15 mv
cell error leave 9.2 mv for voltage growth before inhibit. a released image
must carry a measured, upward-rounded rise bound from 1 to 9 mv. zero
remains the unusable default.

the charger error must be measured at the selected lower cv voltage. cell
measurement bounds require board offset calibration. measure the complete
cell-conversion, polling, i2c and inhibit response, including charge steps
and interruptions. bq observations expire after 200 ms; charger observations
expire after 300 ms. crc, exact configuration readback, readiness, faults
and the directional fet checks remain required.

## host termination

a qualified host ends charge after 30 continuous seconds with the charger
in its cv loop, every measured cell at least 3.980 v, their sum at least
12.000 v, nonnegative measured charge current and a conservative true-current
upper bound no greater than 200 ma. that current bound includes the installed
measurement gain, offset and one adc count. qualify it near zero and 200 ma,
including bypass loads, temperature, noise and both current directions.

the cv indication comes from the charger's actual charging state and active
control loop. it remains usable when the coarse charger current adc rounds
to zero. the bq provides the taper current. the low cv/measurement corner
still reaches the cell and sum floors; the numerical verifier checks this.

completion immediately lowers chg_enable and writes zero to both charger
charge-enable registers. it is a host completion latch, separate from gauge
fc and soc. neither gauge value is changed. adapter loss or stale data keeps
the completion latch and resets its timing windows. recharge requires every
cell at or below 3.950 v for 5 continuous seconds, with fresh qualified data
and all normal admission checks still passing. it does not allow deep-cell
recovery charging.

two accumulated hours of fresh, qualified, enabled cv operation without
completion latches a charge fault. this is a prototype cv acceptance limit,
not a pack-capacity estimate or a cell-manufacturer charge-time rating.
bulk/cc operation and input-limited operation outside the cv loop have no
wall-clock limit from this counter; a large pack or a small supply can spend
many hours there.

the counter advances only between consecutive qualified cv observations
that are enabled and no more than 200 ms apart. bulk, disable, adapter loss,
invalid or stale data, lost readiness and lost qualification pause counting.
unknown time across a missed polling interval is not added retrospectively.
pauses and enable/source toggles retain the accumulated budget and any
fault/completion latch. the budget resets only after genuine completion
followed by the qualified 5-second recharge condition. a timeout cannot
clear through that condition, source changes or another enable request.

the latches and budget are volatile and clear on ec restart. investigate a
cv timeout before restarting the ec. the separate 30-second continuous
valid taper window and the 5-second continuous valid recharge window still
reset on invalid/stale data; pausing the cv budget does not weaken them.

## release gates

cell-voltage, charge-voltage and termination qualification flags default
false in both the board inputs and unit profile. the profile itself remains
unqualified, the actual board charge voltage defaults to zero, and the
response-rise bound defaults to zero. fixture capture and code generation
keep every release flag false.

before a release, validate cell offsets, the charger cv error, complete
voltage-rise response, low-current transfer, continuous taper timing,
termination, recharge hysteresis, cumulative cv timeout, transport loss and supply loss
with simulated cells. then qualify the actual cells, current limits, thermal
windows and harness separately. software tests are not those measurements.

sources: [renesas fn8945 rev6](https://www.renesas.com/en/document/dst/isl9241-datasheet),
voltage accuracy table, maxsystemvoltage register and smbus charging mode;
[ti sluse86a](https://www.ti.com/lit/ds/symlink/bq76922.pdf), cell measurement
and cov threshold tables; [ti sluu cg7](https://www.ti.com/lit/pdf/SLUUCG7),
cov detection and recovery. the charger 0.5% model remains a board acceptance
requirement at 12.120 v.
