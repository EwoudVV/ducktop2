# Ducktop2 Cyberpunk OS Roadmap

## Phase 0: Visual System

Status: started.

- Define the Ducktop2 palette, typography, and shell rules.
- Generate a restrained 2560x1600 wallpaper.
- Build KDE color scheme.
- Build Konsole and Starship themes.
- Keep SDDM/Plymouth staged until recovery is easy.

Exit criteria:

- The look is recognizable as Ducktop2.
- Normal apps stay readable.
- Nothing depends on final PCB hardware.

## Phase 1: Fedora KDE Test Desktop

Target: Windows 11 PC or a Fedora VM.

- Install Fedora KDE.
- Apply `install/apply-theme.sh --install-packages`.
- Test Wayland session.
- Test 125%, 150%, and 175% scaling.
- Test light/dark contrast in Dolphin, Konsole, Settings, browser, text editor.
- Iterate color scheme if amber/cyan accents are too loud.

Exit criteria:

- The desktop feels usable for normal work.
- Terminal and panel feel cyberdeck-native.
- No theme choice makes apps hard to read.

## Phase 2: External NVMe Install

Target: NVMe connected to the Windows 11 PC.

- Create Fedora KDE installer USB.
- Boot installer on the Windows PC.
- Install Fedora to the external NVMe only.
- Confirm boot from external NVMe.
- Apply the Ducktop theme pack.
- Keep SDDM/Plymouth disabled until the install is easy to recover.

Exit criteria:

- External NVMe boots by itself.
- Theme applies cleanly after a fresh login.
- Backups are produced before config changes.

## Phase 3: Boot And Login Polish

Target: external NVMe after recovery path is proven.

- Install SDDM theme without enabling.
- Test SDDM theme in a disposable VM if possible.
- Enable SDDM theme.
- Install Plymouth theme without enabling.
- Enable Plymouth and rebuild initramfs.
- Confirm fallback boot works.

Exit criteria:

- Boot splash and login screen match the Ducktop HUD style.
- A broken login theme can be reverted quickly.

## Phase 4: Daily Driver Defaults

Target: external NVMe, still before final Ducktop hardware.

- Tune global shortcuts.
- Add Yakuake drop-down terminal on a function key.
- Configure Flatpak remotes and preferred apps.
- Set sensible update cadence.
- Add backup script skeleton.
- Add display validation script placeholder.

Exit criteria:

- The OS is pleasant enough to use on a normal PC.
- Theme is reproducible from repo scripts.

## Phase 5: LattePanda Mu Bring-Up

Target: N305/16 GB LattePanda Mu dev setup.

- Boot the themed NVMe.
- Confirm Intel graphics, sleep, Wi-Fi, audio, USB, and thermals.
- Confirm 2560x1600 panel at 120 Hz.
- Tune scaling and font sizes on the real panel.
- Add hardware-specific packages and udev rules.

Exit criteria:

- The same OS image works on real target hardware.
- Display mode and scaling are correct.

## Phase 6: Final Ducktop Integration

Target: fabricated PCB and assembled laptop.

- Add EC daemon.
- Add battery/fan tray widget.
- Add OLED status sync.
- Add GPS/radio status surfaces.
- Replace static wallpaper HUD zones with real widgets where useful.

Exit criteria:

- Cyberdeck polish is backed by real telemetry.
- The laptop feels custom without becoming fragile.
