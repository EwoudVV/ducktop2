# ducktop2 OS and theme

this is the Fedora KDE setup and theme work for ducktop2. i want a dark,
readable desktop with a bit of the cyberdeck feel, while normal applications
still work and look normal.

the files are an early implementation. final Mu boot, EC integration,
recovery, and display validation still need hardware testing.
[project status](../../docs/design-status.md)

## what's here

- A visual spec, palette, and native 2560x1600 wallpaper source.
- KDE and Konsole color schemes, a terminal profile, and Starship settings.
- An optional Plasma panel layout.
- Staged SDDM and Plymouth themes.
- Package/setup scripts for a Fedora KDE install.
- An eMMC recovery/hibernation setup script that still needs target validation.

## start with the desktop

the working base is Fedora KDE Plasma Desktop. test ordinary desktop pieces
on an x86 install or VM before changing login and boot themes. the package
scripts and assumptions need checking against the Fedora/KDE version in use.

from this directory on the Fedora test system:

```sh
bash install/apply-theme.sh --install-packages
```

the script is intended to back up touched user configuration. inspect the
changes and confirm login/recovery before enabling the system themes.
`--panel` applies the optional panel layout.

## wallpaper and system themes

```sh
bash install/check-wallpaper-resolution.sh
```

the native wallpaper source targets 2560x1600. export it through
`install/export-native-wallpaper.sh` when changing the artwork.
static wallpaper should not contain fake battery, temperature, or system
readouts. live status belongs in real widgets fed by the EC/OS.

SDDM/Plymouth are separate steps in `install/system-theme.sh`. keep them
staged until the test system has a working recovery path and their behavior
has been checked. the desktop theme does not require them.

## recovery and hardware integration

the daily OS belongs on NVMe. the 64 GB eMMC is planned for recovery,
hibernation storage, and offline data. the setup script exists, but its disk,
boot, and resume behavior have not been released on hardware.
[eMMC plan](docs/emmc-recovery.md)

EC battery/telemetry transport, lid events, and hardware widgets remain
integration work. host-tested EC report code alone does not create an OS
battery device or a working widget.

- [visual direction](docs/design-spec.md)
- [firmware target status](../../firmware/README.md#stm32-target)

## work order

1. Test the existing wallpaper, colors, terminal, and panel on an x86 Fedora
   KDE install or VM, with readable scaling and normal applications.
2. Prepare the intended NVMe install. identify the disk by model, capacity,
   connection, and partitions before writing it. prove independent boot,
   updates, backups, and recovery.
3. Validate the eMMC setup and recovery implementation on the target.
4. Test login/boot themes after the desktop and recovery path work.
5. Validate graphics, display modes, storage, networking, USB, audio, and
   power states on the Mu.
6. Integrate the EC transport and OS service before claiming working battery,
   lid, fan, radio, or telemetry widgets.
