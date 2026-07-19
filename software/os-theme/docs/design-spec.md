# Ducktop2 Visual Spec v0.1

## Intent

Ducktop2 should feel like a compact, high-end field laptop with a near-future HUD layer: sharp, dense, readable, and deliberate. The style should nod toward tactical/cyberpunk interfaces without copying any specific game's assets, fonts, icons, or layout.

The daily-driver rule wins: if a visual effect makes text harder to read, increases battery drain, or makes normal apps feel silly, it does not ship by default.

## Personality

- Compact, technical, and calm.
- Dark physical-instrument feel rather than neon nightclub.
- Amber as the primary system accent.
- Cyan as the secondary signal/accent.
- Red/orange only for real warnings.
- Motion is quick and purposeful.
- Static art must not pretend to show live telemetry.

## Palette

| Role | Hex | Use |
| --- | --- | --- |
| Deck Black | `#080a0c` | Deep surfaces, terminal background |
| Graphite | `#101418` | Main desktop/window background |
| Panel | `#161b20` | Raised panels, inactive chrome |
| Panel High | `#20262c` | Hover and selected surface |
| Text | `#e4e8e6` | Primary text |
| Muted Text | `#8b949b` | Secondary labels |
| Amber | `#ffb000` | Primary accent, active focus |
| Amber Dim | `#9c6d00` | Borders and inactive HUD lines |
| Cyan | `#00d7ff` | Secondary accent, links, comms |
| Cyan Dim | `#007d96` | Subtle grid/tick details |
| Green | `#44d66f` | Healthy/ready state |
| Red | `#ff4d4f` | Faults only |

## Typography

Use readable fonts first.

- UI: Noto Sans or Inter.
- Terminal/status: JetBrains Mono or Fira Code.
- Prompt/status text should be compact but not microscopic.
- Avoid novelty cyber fonts for body text.
- Letter spacing should stay normal.

## Wallpaper

The default wallpaper is a dark 2560x1600 HUD frame with empty zones for future real widgets. It is generated from exact-size SVG source and exported at the panel's native resolution, so the active wallpaper is not upscaled. It intentionally avoids fake CPU, battery, network, date, or firmware readouts.

Rules for future wallpapers:

- Leave calm space where windows and desktop icons naturally land.
- Keep fake labels generic or avoid them entirely.
- Do not include dates, version numbers, fake warnings, or static telemetry.
- Use high-contrast lines sparingly.
- Make low-power variants darker and quieter.

## Shell Layout

Preferred first layout:

- Single slim top panel.
- Left: app launcher and workspaces.
- Center: active app/window area.
- Right: system tray, audio, network, power, clock.
- Future: Ducktop status widget near the tray.

Avoid a large permanent sidebar at first. The 16-inch panel has room, but daily laptop use benefits from preserving horizontal app space.

## Window Styling

Start from Breeze Dark or a close KDE-native theme.

- Active window focus: amber.
- Links/secondary highlights: cyan.
- Keep corner radius modest.
- Avoid heavy transparency on normal windows.
- Use blur/transparency only on panels, launcher, and optional overlays.

## Terminal

The terminal is the strongest cyberdeck surface.

- Background: deck black.
- Prompt: amber user/host, cyan path/context.
- Errors: red.
- Success/ready: green.
- Keep command output standard and readable.
- Yakuake on a function key is recommended for the drop-down "deck console" feel.

## Notifications

Notifications should feel like HUD alerts but stay useful.

- Information: cyan accent.
- Power/thermal attention: amber accent.
- Faults: red accent.
- No novelty alarm animations by default.

## Login And Boot

Login and boot visuals should be minimal.

- `DUCKTOP2` mark.
- Dark HUD framing.
- Small progress/status elements.
- No fake boot diagnostics that imply hardware checks that are not happening.

## Future EC/Hardware Widgets

When the PCB and EC exist, add real data surfaces:

- Battery percentage, pack voltage/current, charge state.
- Fan RPM/mode.
- CPU temperature.
- Display refresh mode.
- OLED page/mode.
- GPS lock.
- Radio power/PTT armed state.

Safety principle: static art is decorative; live-looking status must be real.

## Explicit Non-Goals

- Do not clone Cyberpunk 2077 UI assets.
- Do not theme every application aggressively.
- Do not require an online theme store.
- Do not make SDDM/Plymouth the first thing enabled.
- Do not depend on a custom compositor or patched desktop shell.
