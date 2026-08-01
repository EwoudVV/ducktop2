# Ducktop2 OS Theme

Early visual system for the Ducktop2 Fedora KDE desktop.

This pack aims for a clean cyberdeck/HUD look that is still comfortable as a daily laptop. It uses original assets and standard KDE customization points instead of copied game UI or fragile full-desktop skinning.

The checked-in wallpaper is generated from the native SVG source at 2560x1600.
The visual direction is still experimental; see the
[`design spec`](docs/design-spec.md) and [`roadmap`](docs/roadmap.md) before
changing it.

## Current Scope

- Ducktop2 visual spec v0.1
- Native vector-derived 2560x1600 wallpaper
- KDE color scheme
- Konsole color scheme and profile
- Starship shell prompt
- Optional Plasma panel layout script
- Staged SDDM and Plymouth theme prototypes
- Fedora package list and installer scripts

## Recommended Base

Use Fedora KDE Plasma Desktop for the first NVMe install. Move to Fedora Kinoite later only after the hardware and EC integration are stable.

## Quick Apply On Fedora KDE

From this directory:

```bash
bash install/apply-theme.sh --install-packages
```

Then log out and back in. The script installs the user-level theme pieces and backs up touched config files under:

```text
~/.local/share/ducktop-theme-backups/
```

The script does not enable the SDDM login theme or Plymouth boot theme by default. Those are staged separately because a broken login theme is annoying on a fresh machine.

## Resolution Check

The target Ducktop2 panel is 2560x1600. Verify the native SVG source and active PNG wallpaper assets with:

```bash
bash install/check-wallpaper-resolution.sh
```

Regenerate the wallpaper from vector source with:

```bash
bash install/export-native-wallpaper.sh
```

## Optional Panel Layout

After the first login, you can apply the prototype top-panel layout with:

```bash
bash install/apply-theme.sh --panel
```

This uses Plasma's scripting interface and should be treated as experimental.

## System Themes

Install SDDM/Plymouth files without enabling them:

```bash
sudo bash install/system-theme.sh --install-sddm --install-plymouth
```

Enable them later, once the Fedora NVMe is easy to recover:

```bash
sudo bash install/system-theme.sh --enable-sddm --enable-plymouth
```

## eMMC Recovery And Hibernate

The 64 GB onboard eMMC is the recovery/rescue OS + hibernation image target.
Design and setup tooling:

- [`docs/emmc-recovery.md`](docs/emmc-recovery.md) — layout, sizing math, boot
  flow, hibernate config, recovery procedures.
- [`install/emmc-recovery-setup.sh`](install/emmc-recovery-setup.sh) — guarded
  setup (partition, build recovery OS, bootloader, hibernate resume). It
  requires `--device` and `--yes`, and has `--check` / `--dry-run` preview
  modes. Execute during Mu bring-up (roadmap Phase 5):

```bash
sudo bash install/emmc-recovery-setup.sh --device /dev/mmcblk0 --check
sudo bash install/emmc-recovery-setup.sh --device /dev/mmcblk0 --dry-run
sudo bash install/emmc-recovery-setup.sh --device /dev/mmcblk0 --yes
```

After the daily driver runs, configure hibernate resume onto the eMMC swap:

```bash
sudo bash install/emmc-recovery-setup.sh --configure-hibernate
```

## Design Rule

Ducktop2 should feel like a real laptop with a cyberdeck-native shell, not a novelty desktop. Keep live-looking telemetry out of static images. Real status belongs in widgets and the future EC daemon.
