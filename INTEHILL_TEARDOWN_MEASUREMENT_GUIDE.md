# Intehill Monitor Teardown And Measurement Guide

Date: 2026-07-06

Goal: learn whether the retained Intehill portable-monitor controller can be
mounted internally with short HDMI/USB-C/button harnesses. Do not force the
panel out of the housing on the first attempt. The fallback design is still
valid if the monitor only opens enough to access its ports and button board.

## Before Opening

- Test and photograph the monitor working at 2560x1600 120 Hz before teardown.
- Remove all cables and let it sit for a few minutes before opening.
- Work on a clean towel or silicone mat so the glass cannot slide.
- Use plastic spudgers, guitar picks, painter's tape, tweezers, and small
  screwdrivers. Avoid metal pry tools near the glass or LCD edge.
- Keep a screw map even if you only find a few screws. Tape each screw near a
  quick sketch of where it came from.
- Photograph every step before unplugging anything.

## Where To Look First

- Check under rubber feet, labels, stand pads, VESA 75x75 covers, trim strips,
  and any decorative stickers before prying.
- Inspect the seam under bright side lighting. A plastic back cover usually has
  clips around the perimeter; a glass-front assembly may also use adhesive.
- If the rear cover does not lift after hidden screws are removed, warm the
  seam gently with a hair dryer on low. Keep it comfortable to touch; do not
  cook the LCD or concentrate heat in one spot.
- Start at a corner or port-side seam with a thin plastic pick. Slide, do not
  lever hard. Add extra picks as clips release so they do not snap back.

## Opening Safely

- Open the shell like a book. Do not pull the halves apart; the button board,
  speakers, touch panel, and display panel may be connected by short flexes.
- Stop immediately if the glass starts lifting separately from the rear shell.
  That usually means the adhesive/glass path is being stressed instead of the
  enclosure seam.
- Stop if a cable resists. Photograph the connector, identify the latch style,
  and release the latch before pulling the flex.
- Do not scrape near LCD edge bonds, touch-panel flexes, or speaker wires.
- Avoid isopropyl alcohol near the LCD edge unless you are intentionally
  softening adhesive and accept the risk; liquid can wick into polarizer layers.

## Photos To Capture

- Full inside view before anything is moved.
- Controller board top and bottom, including all silkscreen part numbers.
- HDMI and both USB-C connector area, with board labels visible.
- Button-board connector on the controller and the button board itself.
- Speaker connectors/wires and any amplifier markings.
- Display panel sticker, panel model, touch-controller part number, and cable
  part numbers.
- Cable routing and connector orientation before unplugging anything.

## Measurements Needed For Ducktop2

- Controller PCB outline, mounting hole positions, max component height, and
  port-side connector height.
- Exact button-board pin count, connector pitch, cable length, and button names.
- Speaker wire length, connector type, speaker impedance/power markings.
- Display/touch cable exit direction and minimum bend radius.
- Whether the HDMI and USB-C ports are on the same PCB or separate daughtercards.
- Whether the monitor accepts plain 5 V in HDMI-plus-touch mode, and steady
  current at full brightness, 2560x1600, and 120 Hz.
- Inrush/plug-in behavior from a bench supply or USB power meter if available.

## Decision Outcomes

- Best case: keep the Intehill controller PCB, mount it internally, and use
  short internal HDMI/USB-C/button-board harnesses.
- Middle case: leave the controller mechanically intact and design short
  internal right-angle plugs/adapters so no cable exits the enclosure.
- Hard case: abandon the enclosure/controller path and choose a raw panel plus
  known controller board. This requires a separate display-controller review.

Source page for the monitor family and selected 2.5K/120 Hz variant:
https://www.intehill.com/products/intehill-16-inch-120hz-touchscreen-portable-monitor-t16kb-t16pb
