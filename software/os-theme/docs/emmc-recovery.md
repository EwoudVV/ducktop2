# eMMC recovery and hibernation

updated 4 september 2026. the plan and setup script exist, but they have not
been validated on the Mu.

## intended use

the daily OS runs on NVMe. the Mu's 64 GB eMMC is intended to hold a small
recovery OS, a hibernation swap partition, and remaining space for offline
data. the recovery system should boot independently when the NVMe install
is unavailable.

hibernation is tied to the saved OS and filesystem state. it is not a way
to continue a session after replacing or reinstalling the NVMe. do not
modify filesystems from another boot and then resume their old hibernation
image. [Linux kernel guidance](https://docs.kernel.org/power/swsusp.html)

## partition plan in the script

| Partition | Intended allocation | Role |
| --- | --- | --- |
| 1 | 1 GiB | EFI system partition |
| 2 | 16 GiB | Recovery root |
| 3 | Detected RAM x 1.10, rounded up to GiB, minimum 2 GiB | Hibernation swap |
| 4 | Remaining space | Offline data |

64 GB decimal is about 59.6 GiB before other allowances. use the actual
device capacity and installed RAM.
partition sizing alone does not prove hibernation will fit and resume under
the chosen kernel, memory load, and power configuration.

## existing script

[`install/emmc-recovery-setup.sh`](../install/emmc-recovery-setup.sh) has
environment/device checks, preview flags, a destructive setup path, and a
separate resume-configuration path. read those paths before using them.
its device checks use `/dev/mmcblk*`, mounted/root checks, and size limits;
verify the actual block-device identity as well.

on the intended Linux target, these flags are the starting points for
inspection, using the verified device path:

```sh
bash install/emmc-recovery-setup.sh --check
bash install/emmc-recovery-setup.sh --device /dev/mmcblk0 --dry-run
```

the `/dev/mmcblk0` path is an example, not a disk selection. the full setup
uses `--yes` and repartitions/formats the chosen device. `--configure-hibernate`
changes the running OS's resume configuration. neither operation was run
during the documentation update.

## work before using it as recovery

1. Review device/root/mount detection, active swap, partition sizing, and all
   write paths against the actual target environment.
2. Verify filesystem labels/UUIDs, mount points, recovery packages, EFI
   layout, kernel/initramfs installation, and boot entries agree.
3. Check the script's behavior on a disposable test disk/VM where possible,
   then perform a controlled installation on the intended target.
4. Prove recovery boot with the NVMe unavailable. confirm networking,
   diagnostics, backup access, and the intended treatment of other disks.
5. Configure and test hibernation separately using the installed kernel,
   initramfs, and systemd documentation. do not copy the old generic
   hibernate command examples as proof of a valid setup.
6. Record normal boot, failed-update recovery, hibernate/resume, and a rebuild
   path if the eMMC installation is lost.

the documentation cleanup does not approve or change the installer. any
script corrections belong in a separate implementation change with tests
for its actual disk/boot behavior.
