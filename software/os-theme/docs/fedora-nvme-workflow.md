# Fedora NVMe Workflow

This workflow assumes:

- Main laptop: M1 Max Mac.
- Helper machine: Windows 11 PC reachable as `ssh home-pc`.
- Target disk: external NVMe in a USB adapter.
- Target OS: Fedora KDE Plasma Desktop.

## Design Work

Use the M1 Mac for:

- Theme repo edits.
- Wallpaper and asset generation.
- Documentation.
- Script development.

Do not try to use the M1 Mac as the main Fedora x86 install/test environment. It is the wrong architecture for the target OS.

## Install/Test Work

Use the Windows 11 PC for:

- Creating Fedora installer media.
- Booting the Fedora installer.
- Installing Fedora to the external NVMe.
- Boot-testing the external NVMe.
- Applying and testing the Ducktop theme pack.

## Safe Disk Rule

Before any install or disk-writing command, identify the target NVMe by exact:

- Vendor/model.
- Size.
- Existing partitions.
- USB enclosure name if visible.

Do not proceed from drive letters alone. Drive letters are not a safety boundary.

## Practical Path

1. Download Fedora KDE Plasma Desktop ISO on the Windows PC.
2. Create installer USB with Fedora Media Writer or Rufus.
3. Shut down the Windows PC.
4. Attach the Fedora installer USB and the external NVMe.
5. Boot the Fedora installer.
6. In the installer, select only the external NVMe as the install target.
7. Use automatic partitioning for the first pass unless there is a specific reason not to.
8. Boot from the external NVMe.
9. Copy this theme pack to the Fedora install.
10. Run:

```bash
bash install/apply-theme.sh --install-packages
```

11. Log out and back in.
12. Only after basic boot/recovery works, test SDDM and Plymouth:

```bash
sudo bash install/system-theme.sh --install-sddm --install-plymouth
sudo bash install/system-theme.sh --enable-sddm --enable-plymouth
```

## Recovery Habit

Keep the installer USB around until the external NVMe has survived:

- A full update.
- Several reboots.
- One failed-theme recovery drill.

For early experiments, assume every login or boot theme can be wrong and keep a way back in.

## Theme Transfer Options

Simple copy from Mac:

```bash
scp -r software/os-theme home-pc:~/ducktop-os-theme
```

Then copy from Windows to the Fedora install, or use Git once the repo exists.

Better long-term:

- Put `ducktop-os-theme` in Git.
- Clone it directly on Fedora.
- Tag known-good versions before risky SDDM/Plymouth changes.
