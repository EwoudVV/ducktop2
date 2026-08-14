# Ducktop2 8-Layer Power Plan (rail inventory + island budget)

Status: WORKING DRAFT — rail inventory is from the schematic; endpoint load
currents are estimates until the load audit is closed. This plan defines
where power copper lives so routing never has to invent it.

## Layer assignment (from HIGH_SPEED_ROUTING_PLAN)

- L2 In1.Cu: GND solid
- L4 In3.Cu: GND solid
- L5 In4.Cu: POWER islands
- L7 In6.Cu: GND solid
- Impedance pairs on L1/L8/L3; L6 general.

## Rail inventory (from the schematic converters)

| Rail | Converter | Spec | Plane island (L5) | Notes |
|---|---|---|---|---|
| VSYS (3S pack) | battery input | ~9.0-12.6 V, pack fuse + protector | LARGE island | feeds all bucks; see current budget |
| MU_12V | U750 TPS552892 | 12 V, 3.33 A limit, 400 kHz forced PWM | island | Mu module + fan + buck chain |
| SYS_5V | U6 TPS56637 | 6 A class | island | hub/USB/audio/OLED/maker |
| SYS_3V3 | U7 TPS56637 | 6 A class | island | Mu IO rails, logic |
| MCU_3V3 | U5 TPS54202 | 2 A | island | always-on EC domain |
| USB_PORT_5V | U1703 chain | USB VBUS current-limited outputs | islands | port-specific, current-limited |
| MAKER_3V3_CORE | U900 chain | maker MCU | island | isolated maker zone |
| HUB_CORE / HUB_VCORE | U1700 chain | hub core rails | islands | |

## Current budget (ESTIMATES — close before final order)

Peak totals assumed: Mu module 15 W class (12 V => 1.3 A on MU_12V),
keyboard/OLEDs ~0.5 A, USB-C downstream 2x 1.5 A (3 A on SYS_5V), audio
1 A, hub 1 A, maker 0.4 A, fan 0.26 A. Estimated VSYS peak: ~3.5-4.5 A
continuous with 8 A transient headroom (motor/charger inrush excluded;
charger path is separate).

## L5 island rules

- Island-to-island gap: >= 1.0 mm (matching the outer clearance rules) so
  no L6 impedance run is forced to cross an island boundary.
- VSYS and MU_12V islands: 2 oz-class equivalent copper; if the fab keeps
  1 oz inner layers, width the neck-downs to carry 3 A per 10 mm of width
  with <= 0.1 V drop.
- Every island gets a via farm at its source (converter SW node / inductor
  output) and at each major load: >= 4 vias per amp for 0.3/0.6 vias.
- MCU_3V3 stays an L5 island but is sourced from the always-on U5 domain;
  no EC rail crosses a host-gated region.

## Open items before routing can rely on this plan

1. Load audit: per-rail endpoint current from the BOM/datasheets
   (replace the estimates above).
2. Fab confirmation: inner copper weight (1 oz vs 2 oz) and the L5 island
   voltage-drop acceptance.
3. Thermal: VRM copper + thermal-via density for U6/U7/U750 and the
   charger path — affects island shape.
