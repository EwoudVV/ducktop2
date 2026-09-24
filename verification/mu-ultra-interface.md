# Mu Ultra interface changes

checked 24 september 2026. this covers the interface migration. the
100 W power path, firmware, cooling and completed routing still need work.

## what changed

- A1 now uses the official 260-contact Ultra pin table. the TE socket and
  its position stay the same. pin 136 is separate from ground and left open.
- Bluetooth moves to USB2 P6, and the left hub moves to P2. the internal
  hub becomes USB2513BT-I/M2, with codec, trackpad and optional radio ports.
- U400 has the Microchip M2 land pattern: 0.28 x 0.90 mm signal lands,
  0.5 mm pitch and a 3.7 mm exposed ground pad with nine ground vias.
- the trackpad keeps U64's protected supply. U450 combines hub permission
  with host-active status; U451 isolates fault feedback from the always-on
  EC pull-up. both have powered-off input/output protection.
- HDMI uses TCP2. the cable contacts and right-board routes are unchanged.
- NVMe CLKREQ reaches A1 pin 108. the old R50 pull-down is removed.

## checks

| check | result |
| --- | --- |
| official A1 contact names | all 260 match |
| center schematic contracts | pass |
| right-board schematic contracts | pass |
| center and right PCB pad nets | match their fresh schematic netlists |
| net-class and connector tests | 13 pass |
| electrical ERC errors | 0; 375 library-copy warnings remain |
| retained component positions and IDs | unchanged |
| retained track/via geometry | unchanged |
| new routing | none |
| removed copper | 51 items at the changed A1 contacts and R50 |
| new shorts, clearance or courtyard violations | none compared with the checked baseline |

the center has 786 footprints and 5,193 tracks/vias after this pass. its
actual unrouted count is 1,571, up from 1,538 as the changed contacts and
new logic need connecting. the CLI report stops listing at 499; that is
not the full count.

the complete center DRC has 828 reported violations, compared with 822 in
the baseline. the added reports are seven dangling tracks and two dangling
vias after removing old connections; three previous reports disappear.
existing routing errors, including shorts and restricted-layer use, remain.
these results do not clear the board for fabrication.

the BMS, keyboard, firmware and software files are unchanged. the present
PD and charger limits stay in place until the 100 W circuit is designed
and qualified. [module requirements](../manufacturing/lattepanda_mu_bios_release.md)
