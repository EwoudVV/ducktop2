# visual direction

i want the desktop to feel like part of ducktop2 without making ordinary
applications awkward to use. dark surfaces, readable text, amber and cyan
accents, and a restrained HUD-like frame are the starting point.

this is a working style, not a requirement to skin every application.
readability and normal laptop use come first.

## palette

| Role | Hex | Use |
| --- | --- | --- |
| Deck black | `#080a0c` | Deep surfaces and terminal background |
| Graphite | `#101418` | Main desktop/window background |
| Panel | `#161b20` | Raised panels and inactive controls |
| Panel high | `#20262c` | Hover and selected surface |
| Text | `#e4e8e6` | Primary text |
| Muted text | `#8b949b` | Secondary labels |
| Amber | `#ffb000` | Main accent and active focus |
| Amber dim | `#9c6d00` | Borders and quiet framing |
| Cyan | `#00d7ff` | Secondary accent and links |
| Cyan dim | `#007d96` | Subtle grid/tick details |
| Green | `#44d66f` | Real healthy/ready state |
| Red | `#ff4d4f` | Real faults |

## text and windows

use a readable UI font such as Noto Sans or Inter, and a normal monospace
font such as JetBrains Mono or Fira Code for the terminal/status areas.
keep body text at a useful size and use normal letter spacing.

start from KDE-native window styling. use amber for focus and cyan for
secondary highlights, with modest corner rounding and limited transparency.
avoid visual effects that get in the way of reading or cost power without
adding anything useful.

## wallpaper and panel

the native wallpaper target is 2560x1600. keep space for windows and icons,
and leave live-looking data out of the artwork. no fake battery percentage,
temperature, clock, firmware version, or boot diagnostics.

the starting panel layout is a slim top bar: launcher/workspaces on the left,
active application in the middle, and the normal tray/audio/network/power/
clock controls on the right. a future EC widget can sit with the tray.

## terminal, login, and notifications

the terminal uses a dark background, amber prompt accents, cyan paths,
and ordinary readable command output. a drop-down terminal is optional.
notifications can use cyan for information, amber for attention, and red
for faults without novelty alarm effects.

keep login/boot themes simple and test them after recovery works. a logo
and framing are fine; progress or diagnostics should reflect real activity.

## later hardware widgets

battery, fan, temperature, display mode, radio, and GNSS widgets need valid
EC/OS data. show missing or stale values as unavailable. the wallpaper remains
decorative and the widgets report the actual system.

use original assets and standard desktop features. the theme should stay
easy to apply, undo, and maintain. [software roadmap](../README.md#work-order)
