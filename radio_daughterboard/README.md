# radio daughterboard

the radio/GNSS/audio board is removable. i want the rest of the laptop to
work while it is absent or being revised, including normal system audio,
the microphone, charging, and boot.

it contains DRA818V and DRA818U radio modules, external filters and RF
switches, a MAX-M10S GNSS receiver, and a separate PCM2900C USB audio codec.
power, USB, UART/control, PTT, presence, and fault signals go through the
removable interface. the radio is intended to start off and stay separate
from core laptop power decisions.

## layout state

the 4 september board read found 126 footprints on a four-layer placement
board, with no tracks or vias. the nominal outline is about 120 x 70 mm.


the stored renders show a placement-stage design. they do not prove the
current chassis fit. the center-side FFC connector J2300 is now at (188,4),
rotation 0, so the installed cable route and board supports need a new check.
[mechanical plan](../docs/mechanical.md)

## source and checks

the schematic hierarchy and placement generator live in `gen/`:

- `generate_radio_daughterboard_project.py`
- `generate_radio_daughterboard_pcb.py`
- `verify_radio_daughterboard.py`

generation can replace source/placement files. use a copied candidate for
a deliberate change, following [the rebuild guidance](../docs/build-and-verify.md#deliberate-rebuilds).
direct ERC and DRC can inspect the existing files without regeneration.

## remaining work

finish placement/routing, test access, the cable installation, and mechanical
supports. then verify rails, default-off behavior, removal/fault handling,
GNSS, control and audio paths. RF filters, antennas, transmit behavior,
emissions, and coexistence need their own measured test setup.

the radio can be deferred during initial laptop bring-up. its removal must
not silently break a shared bus, reset, power, or audio dependency.
