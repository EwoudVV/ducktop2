# Ducktop2 Onboard eMMC: Recovery OS + Hibernation Image

Status: design + setup script DONE (host-checked, not run on hardware).
Mu bring-up (OS roadmap Phase 5) is where this is executed.

## Role and constraints

The LattePanda Mu's 64 GB onboard eMMC is **not** daily storage and **not** RAM:

- eMMC is a block device at ~200-300 MB/s with millisecond latency. As swap for
  active work it would make the machine crawl; the daily driver runs from the
  2 TB NVMe (PCIe Gen3 x4).
- The eMMC exists to get the laptop back to a working state and to make
  suspend-to-disk possible without paying NVMe capacity for it.

Planned uses (verification record rows 9/17):

1. **Recovery/rescue OS** — boots if the NVMe is dead, unbootable, or mid-update.
2. **Hibernation image** — suspend-to-disk target for the daily driver (NVMe).
3. **Offline data** — APRS maps, logs, and field payloads that must survive a
   wiped or failed NVMe.

## Partition layout (GPT)

The eMMC is a full GPT disk so recovery and hibernation are self-contained and
device-independent. Kernel and recovery tools live on the eMMC itself; the
recovery OS never depends on the NVMe.

| # | Size | Type | Content |
| --- | --- | --- | --- |
| p1 | 1 GiB | EFI System | FAT32. systemd-boot + recovery kernel/initramfs |
| p2 | 16 GiB | Linux root | ext4. Minimal Fedora recovery OS |
| p3 | RAM + 10% | Linux swap | Hibernation image target (see sizing below) |
| p4 | remainder | Linux data | ext4. Offline APRS/maps/logs |

Total check: 1 + 16 + (RAM + 10%) + data = 64 GB (≈ 56 GiB usable), which holds
even the 32 GB RAM Mu variant: 1 + 16 + 35.2 + 3.8 ≈ 56 GiB.

### Sizing math

- Hibernation needs a contiguous image of used RAM plus swap headroom.
  `resume=` requires the image to fit in the swap partition at hibernate time.
- Rule: `swap_size = round_up(installed_RAM * 1.10, 1 GiB)`, minimum 2 GiB.
  - 16 GB variant (DFR1149): 18 GiB.
  - 32 GB variant (future): 36 GiB.
- The setup script reads `/proc/meminfo` and computes p3 automatically; it
  never assumes a fixed size.
- p4 gets everything left. On the 16 GB variant that is ~19-20 GiB of offline
  data capacity.

## Boot flow

1. Mu UEFI boot order: **NVMe first, eMMC second**. Each disk has its own
   bootloader; a dead or unbootable NVMe simply falls through to the eMMC.
2. Manual choice: the Mu BIOS boot menu (F7 at power-on) lists both disks.
3. Recovery boot shows a systemd-boot menu (timeout 3 s) with entries:
   - `Ducktop2 Recovery` — default, auto-boots after the timeout.
   - `Recovery (safe mode)` — `rd.break=pre-mount` style single-user,
     for diagnosing a broken recovery root.
4. The recovery OS runs entirely from eMMC; it never mounts or writes the NVMe
   unless the operator explicitly mounts it.

## Hibernation configuration (daily driver on NVMe)

The hibernate image goes to eMMC p3 so NVMe capacity is not consumed and the
image survives NVMe replacement.

- Kernel cmdline on the NVMe boot entry:
  `resume=UUID=<p3-swap-uuid>` (add `resume_offset=` automatically when the
  swap partition is on a swap-enabled filesystem).
- dracut: `/etc/dracut.conf.d/99-ducktop-resume.conf` with
  `add_dracutmodules+=" resume "`.
- systemd: `systemctl hibernate` / `systemctl hibernate-delayed`; verify with
  `systemctl hibernate --test` before first real use.
- The setup script's `--configure-hibernate` flag writes the dracut config,
  adds the kernel cmdline, and rebuilds the initramfs. It refuses to run if p3
  does not exist or has no swap UUID.

## Building the recovery OS

The script builds a minimal Fedora recovery root with `dnf --installroot`:

- Base: `fedora-release systemd systemd-udev kernel-core kernel-modules-core
  kernel-modules-extra dracut dracut-network e2fsprogs dosfstools util-linux
  coreutils tar gzip rsync vim-minimal less`
- Networking for restores: `NetworkManager openssh-server curl iproute`
- The script then installs systemd-boot into the eMMC ESP with `bootctl
  --esp-path=... --boot-path=...` and writes the two loader entries above.
- Only packages that exist in the current Fedora release are added; the list is
  editable at the top of the script.

## Recovery procedures

| Situation | Procedure |
| --- | --- |
| NVMe dead / unbootable | Power on; BIOS falls through to eMMC; recovery menu → `Ducktop2 Recovery`. Mount the NVMe from recovery with `lsblk`/`mount` and pull data to p4 or a USB stick. |
| Broken update on NVMe | Boot eMMC recovery, chroot or `dnf --installroot` the NVMe root, undo the transaction, reboot. |
| Need to reinstall daily driver | Boot recovery, wipe NVMe, install Fedora (or restore a backup) from the recovery environment. |
| Hibernate won't resume | Boot recovery; check `swapon p3` + `resume=UUID`; the recovery OS has the same kernel params tooling for diagnosis. |
| eMMC itself corrupted | eMMC is soldered; use a USB install stick + BIOS boot menu to boot the daily NVMe, then rerun the setup script with `--yes` to rebuild the eMMC. |

## Safety rules (baked into the script)

- The script is **not** automatic: it requires `--device <dev>`, prints the
  full plan, and requires `--yes` before touching anything.
- Refuses devices that are the running root, have mounted partitions, are
  flagged rotational-except-sd, or are not in the 8-128 GiB eMMC range.
- `--dry-run` prints every command without executing it; `--check` validates
  the environment and device without modifying anything.
- p3 size is computed from installed RAM, never assumed.
