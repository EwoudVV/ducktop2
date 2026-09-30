these are compact snapshots of the native center, left and right netlists
reviewed on 30 september 2026. they keep the exported values, ordering codes,
footprints and pin connections used by the power wiring contract. unrelated
components and KiCad display metadata are omitted.

the side snapshots include C2680..C2684. the center snapshot includes the
reviewed CSD17577Q3A_DNH footprint associations, C2685, and the selector's
local regulator bypasses. the tests deliberately mutate
these records to make sure a missing bypass, wrong rail, wrong package or
wrong ordering code fails the contract.
