# Intehill Teardown Findings

Date: 2026-07-06

Source photos: `/Users/ellievanvooren/Downloads/attachments.zip`

## Current Situation

- The front glass/touch stack was cracked during panel removal.
- Treat this original V1 monitor panel as mechanically damaged for final use.
- Bench update: despite the cracked front glass/touch stack, the LCD image still
  works and looks clean. This strongly suggests the LCD cell/controller path
  survived, though the cracked glass is still not a good final mechanical part.
- Do not keep prying or flexing the panel. Tape the cracked glass, keep it flat,
  and handle it with gloves/eye protection.
- The controller board, speakers, button wiring, touch daughterboard, and panel
  identification labels are still useful design data.

## Observed Hardware

- Main controller board has one HDMI-A input, two USB-C ports, five side buttons,
  one audio-style jack, one wide panel FFC, and two 2-pin speaker connectors.
- Measured controller board outline is about 114 x 70 mm.
- Each speaker module is about 18 x 38 mm. Current mechanical intent is to
  place both speakers near the front/user edge and route their harnesses back
  to the retained Intehill controller board.
- Button labels visible on the controller edge include menu/up/down style inputs;
  this supports the existing trace-only button pass-through plan.
- Panel/touch flex marking visible: `K1740_V01_FPC`.
- Touch/controller daughterboard marking visible: `TBI?C-A3-V1.2` best read from
  photo; confirm with a sharper close-up before using as a purchasing key.
- Panel sticker confirmed from close-up: AUO `B160QAN03.K`, hardware revision
  `HW:0A`, firmware `FW:1`, alternate/EDID name `AUO30A5`, Dell-style DPN
  `0P3FPJ`, barcode sticker `HS16025090829 A0`.

## Design Impact

- Existing ducktop2 retained-controller architecture is still valid:
  internal HDMI to the monitor controller, internal USB-C/power/touch feed, and
  trace-only pass-through for physical monitor buttons.
- The original display assembly now tests electrically good for image output,
  but remains mechanically damaged. The likely paths are:
  1. Buy a replacement/donor Intehill monitor and avoid raw panel removal.
  2. Buy a matching AUO `B160QAN03.K` raw LCD and reuse the controller if the
     controller/touch hardware still tests good.
  3. Switch to a known raw panel plus known controller board, then update sheet
     10/11 around that specific hardware.
- Before buying parts, confirm whether the cracked front glass was only cover
  glass/touch glass or whether the LCD cell itself is cracked. Also confirm
  whether the touch layer is separate from the AUO LCD replacement.

## Immediate Next Checks

- Use `B160QAN03.K HW:0A / AUO30A5` as the safest replacement-panel target.
  `B160QAN03.H` listings are close relatives, but treat them as compatibility
  gambles unless the seller confirms connector position/orientation, 120 Hz
  operation, backlight compatibility, and easy returns.
- Photograph the touch daughterboard and its connector labels without tape/glare
  if possible.
- Measure controller PCB mounting holes, max component height, and port edge
  positions.
- Measure speaker connector pitch, impedance, polarity, and acoustic outlet
  direction.
- If testing power, remove loose glass fragments first, put the controller on a
  nonconductive surface, current-limit the supply if possible, and do not touch
  the cracked panel while powered.

## External References

- AUO B160QAN03.K overview: https://www.panelook.com/B160QAN03.K_AUO_16.0_LCM_overview_68142.html
- Example replacement listings currently exist for `B160QAN03.K`; verify seller,
  connector, touch support, refresh rate, and return policy before buying.
