#!/usr/bin/env bash
set -euo pipefail

# Ducktop2 eMMC setup: recovery/rescue OS + hibernation image + offline data.
# See docs/emmc-recovery.md before using. Never runs without --device and --yes.

RECOVERY_ROOT_SIZE_GIB=16
ESP_SIZE_GIB=1
HIBERNATE_MARGIN=1.10
MIN_SWAP_GIB=2
MIN_DEVICE_GIB=8
MAX_DEVICE_GIB=128

RECOVERY_PACKAGES=(
  fedora-release
  shadow-utils
  sudo
  systemd
  systemd-udev
  kernel-core
  kernel-modules-core
  kernel-modules-extra
  dracut
  dracut-network
  e2fsprogs
  dosfstools
  util-linux
  coreutils
  tar
  gzip
  rsync
  vim-minimal
  less
  NetworkManager
  openssh-server
  curl
  iproute
)

DEVICE=""
YES=0
DRY_RUN=0
CHECK=0
SKIP_OS=0
CONFIGURE_HIBERNATE=0
swap_gib=0
PASSWORD_HASH_FILE=""
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

usage() {
  cat <<'USAGE'
Usage: sudo bash install/emmc-recovery-setup.sh --device <dev> [options]

Sets up the Ducktop2 onboard eMMC as recovery OS + hibernation image.

Required:
  --device <dev>       eMMC block device, e.g. /dev/mmcblk0

Modes (default: full setup):
  --check              Validate environment and device; change nothing.
  --dry-run            Print the full plan and every command; change nothing.
  --yes                Actually perform the setup (required for real mode).
  --recovery-password-hash-file <file>
                       Required for a full build; one crypt password hash
                       for the local duck recovery account.
  --skip-os            Partitions and formatting only; skip
                       building the recovery OS root.
  --configure-hibernate
                       Configure the RUNNING system (daily driver on NVMe)
                       to resume from the eMMC swap partition.
  -h|--help            Show this help.

Safety: refuses to touch the running root, mounted partitions, or non-eMMC
devices.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)
      shift
      DEVICE="${1:-}"
      ;;
    --device=*) DEVICE="${1#--device=}" ;;
    --yes) YES=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --check) CHECK=1 ;;
    --skip-os) SKIP_OS=1 ;;
    --recovery-password-hash-file) shift; PASSWORD_HASH_FILE="${1:-}" ;;
    --configure-hibernate) CONFIGURE_HIBERNATE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
  shift
done

if [[ -z "$DEVICE" && "$CHECK" -eq 0 && "$CONFIGURE_HIBERNATE" -eq 0 ]]; then
  echo "Error: --device <dev> is required." >&2
  usage; exit 2
fi

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    echo "[run] $*"
    "$@"
  fi
}

die() {
  echo "Error: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required tool not found: $1"
}

detect_swap_gib() {
  local mem_total mem_bytes swap_bytes swap_gib_local
  if [[ -r /proc/meminfo ]]; then
    mem_total=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
  else
    mem_total=$((16 * 1024 * 1024))
  fi
  mem_bytes=$((mem_total * 1024))
  swap_bytes=$(( mem_bytes * 11 / 10 ))
  swap_gib_local=$(( (swap_bytes + 1073741823) / 1073741824 ))
  if ((swap_gib_local < MIN_SWAP_GIB)); then
    swap_gib_local=$MIN_SWAP_GIB
  fi
  printf '%s' "$swap_gib_local"
}

check_device() {
  [[ -b "$DEVICE" ]] || die "not a block device: $DEVICE"
  [[ "$DEVICE" =~ ^/dev/mmcblk[0-9]+$ ]] || die "expected a whole /dev/mmcblkN eMMC device"
  [[ "$(lsblk -dn -o TYPE "$DEVICE")" == disk ]] || die "target is not a whole disk"
  local kernel_name=${DEVICE##*/}
  [[ "$(cat "/sys/class/block/$kernel_name/device/type")" == MMC ]] || die "target is an SD card, not eMMC"
  [[ ! -e "/sys/class/block/$kernel_name/partition" ]] || die "target is a partition"
  local child active_swap
  while read -r child; do
    [[ -n "$child" ]] || continue
    [[ -z "$(ls -A "/sys/class/block/${child##*/}/holders")" ]] || die "$child has active block holders"
    while read -r active_swap; do
      [[ "$active_swap" != "$child" ]] || die "$child is active swap"
    done < <(swapon --show=NAME --noheadings --raw)
  done < <(lsblk -nrpo NAME "$DEVICE")

  local root_src mounted size_bytes size_gib needed
  root_src=$(findmnt -n -o SOURCE --target / || true)
  case "$root_src" in
    "$DEVICE"|"$DEVICE"*) die "device $DEVICE is the running root ($root_src)" ;;
  esac

  mounted=$(lsblk -no MOUNTPOINT "$DEVICE" 2>/dev/null | grep -v '^$' || true)
  if [[ -n "$mounted" ]]; then
    die "device $DEVICE has mounted partitions: $mounted"
  fi

  size_bytes=$(lsblk -bdn -o SIZE "$DEVICE")
  size_gib=$(( size_bytes / 1073741824 ))
  if (( size_gib < MIN_DEVICE_GIB || size_gib > MAX_DEVICE_GIB )); then
    die "device size ${size_gib} GiB outside eMMC range (${MIN_DEVICE_GIB}-${MAX_DEVICE_GIB} GiB)"
  fi

  needed=$(( ESP_SIZE_GIB + RECOVERY_ROOT_SIZE_GIB + swap_gib ))
  if (( needed + 1 > size_gib )); then
    die "device ${size_gib} GiB too small for layout needing ${needed} GiB plus 1 GiB minimum offline space (incl. ${swap_gib} GiB hibernate)"
  fi
  echo "device OK: $DEVICE (${size_gib} GiB, hibernate swap ${swap_gib} GiB)"
}

check_prereqs() {
  for tool in lsblk findmnt blkid swapon python3; do
    need_cmd "$tool"
  done
  if [[ "$DRY_RUN" -eq 0 && "$CONFIGURE_HIBERNATE" -eq 0 && "$CHECK" -eq 0 ]]; then
    for tool in sgdisk mkfs.fat mkfs.ext4 mkswap partprobe; do
      need_cmd "$tool"
    done
  fi
  if [[ "$DRY_RUN" -eq 0 && "$CHECK" -eq 0 && "$SKIP_OS" -eq 0 && "$CONFIGURE_HIBERNATE" -eq 0 ]]; then
    need_cmd dnf
  fi
}

plan() {
  echo "=== Ducktop2 eMMC setup plan ==="
  echo "Device:         $DEVICE"
  echo "ESP:            ${ESP_SIZE_GIB} GiB (FAT32, systemd-boot + recovery kernel)"
  echo "Recovery root:  ${RECOVERY_ROOT_SIZE_GIB} GiB (ext4, minimal Fedora)"
  echo "Hibernate swap: ${swap_gib} GiB (RAM*${HIBERNATE_MARGIN}, rounded up)"
  echo "Offline data:   remainder (ext4)"
  echo "Recovery OS:    $([[ "$SKIP_OS" -eq 1 ]] && echo skipped || echo built with dnf --installroot)"
  echo "================================"
}

if [[ "$CHECK" -eq 1 && -z "$DEVICE" && "$CONFIGURE_HIBERNATE" -eq 0 ]]; then
  check_prereqs
  echo "Environment OK (check mode; no device given)."
  exit 0
fi

check_prereqs
swap_gib=$(detect_swap_gib)

if [[ "$CONFIGURE_HIBERNATE" -eq 1 ]]; then
  hswap=$(blkid -L ducktop-hibernate || true)
  if [[ -z "$hswap" ]]; then
    die "no eMMC swap partition labeled ducktop-hibernate; run the full setup first"
  fi
  hswap_uuid=$(blkid -s UUID -o value "$hswap")
  [[ -n "$hswap_uuid" ]] || die "no swap UUID on $hswap"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] would configure resume=UUID=$hswap_uuid on the running system"
    echo "[dry-run] would rebuild initramfs with dracut --force"
    exit 0
  fi
  [[ "$(blkid -s TYPE -o value "$hswap")" == swap ]] || die "resume target is not swap"
  [[ "$hswap" =~ ^/dev/mmcblk[0-9]+p[0-9]+$ ]] || die "resume target is not an eMMC partition"
  resume_parent=$(lsblk -dn -o PKNAME "$hswap")
  [[ "$(cat "/sys/class/block/$resume_parent/device/type")" == MMC ]] || die "resume target is not eMMC"
  [[ "$(lsblk -bdn -o SIZE "$hswap")" -ge "$((swap_gib * 1073741824))" ]] || die "resume swap is below the planned hibernate size"
  [[ "$CHECK" -eq 0 ]] || { echo "resume target verified; no changes in check mode"; exit 0; }
  [[ "$YES" -eq 1 ]] || die "--configure-hibernate requires --yes"
  need_cmd dracut
  need_cmd grubby
  [[ "$EUID" -eq 0 ]] || die "must run as root (sudo)"
  echo "Configuring hibernate resume on the running system (UUID=$hswap_uuid)..."
  mkdir -p /etc/dracut.conf.d
  printf 'add_dracutmodules+=" resume "\n' > /etc/dracut.conf.d/99-ducktop-resume.conf
  local_grub=/etc/default/grub
  local_cmdline=/etc/kernel/cmdline
  mkdir -p /etc/kernel /etc/dracut.conf.d
  if [[ -f "$local_cmdline" ]]; then
    python3 "$SCRIPT_DIR/resume_config.py" "$local_cmdline" "$hswap_uuid"
  elif [[ -f "$local_grub" ]]; then
    python3 "$SCRIPT_DIR/resume_config.py" "$local_grub" "$hswap_uuid" --grub
  else
    die "no supported persistent kernel command-line configuration found"
  fi
  grubby --update-kernel=ALL --remove-args="resume resume_offset" --args="resume=UUID=$hswap_uuid"
  grubby --info=ALL | grep -q "resume=UUID=$hswap_uuid" || die "resume argument missing from boot entries"
  if ! grep -q "^UUID=$hswap_uuid[[:space:]]" /etc/fstab; then
    printf 'UUID=%s none swap defaults 0 0\n' "$hswap_uuid" >> /etc/fstab
  fi
  swapon "$hswap" 2>/dev/null || swapon --show=NAME --noheadings | grep -Fxq "$hswap" || die "swap activation failed"

  dracut --force
  echo "resume argument and initramfs updated; hibernate/resume still needs a real test on the Mu"
  exit 0
fi

check_device

if [[ "$DRY_RUN" -eq 1 ]]; then
  plan
  echo "[dry-run] nothing changed."
  exit 0
fi

if [[ "$CHECK" -eq 1 ]]; then
  echo "Device ready for setup."
  exit 0
fi

if [[ "$YES" -ne 1 ]]; then
  plan
  echo "Refusing to continue without --yes (nothing changed)." >&2
  exit 1
fi

[[ "$EUID" -eq 0 ]] || die "must run as root (sudo)"
if [[ "$SKIP_OS" -eq 0 ]]; then
  [[ -r "$PASSWORD_HASH_FILE" ]] || die "full setup requires --recovery-password-hash-file"
  [[ "$(wc -l < "$PASSWORD_HASH_FILE")" -le 1 ]] || die "password hash file must contain one line"
  grep -Eq '^\$(6|y)\$[^[:space:]:]+$' "$PASSWORD_HASH_FILE" || die "expected one SHA-512 or yescrypt password hash"
fi

echo "=== Partitioning $DEVICE ==="
run sgdisk -o "$DEVICE"
run sgdisk -n 1:0:+${ESP_SIZE_GIB}GiB -t 1:ef00 -c 1:ducktop-esp "$DEVICE"
run sgdisk -n 2:0:+${RECOVERY_ROOT_SIZE_GIB}GiB -t 2:8304 -c 2:ducktop-recovery-root "$DEVICE"
run sgdisk -n 3:0:+${swap_gib}GiB -t 3:8200 -c 3:ducktop-hibernate "$DEVICE"
run sgdisk -n 4:0:0 -t 4:8300 -c 4:ducktop-offline "$DEVICE"
run partprobe "$DEVICE"

echo "=== Formatting ==="
run mkfs.fat -F32 -n DUCKTOP-ESP "${DEVICE}p1"
run mkfs.ext4 -L ducktop-recovery "${DEVICE}p2"
run mkswap -L ducktop-hibernate "${DEVICE}p3"
run mkfs.ext4 -L ducktop-offline "${DEVICE}p4"

if [[ "$SKIP_OS" -eq 1 ]]; then
  echo "Layout done (recovery OS skipped)."
  exit 0
fi

echo "=== Building recovery OS (dnf --installroot) ==="
need_cmd dnf
release_ver=$(source /etc/os-release 2>/dev/null && printf '%s' "${VERSION_ID:-}")
[[ -n "$release_ver" ]] || die "cannot determine Fedora release version"
mnt=$(mktemp -d)
trap 'umount -R "$mnt" 2>/dev/null || true; rm -rf "$mnt"' EXIT
run mount "${DEVICE}p2" "$mnt"
run mkdir -p "$mnt/boot"
run mount "${DEVICE}p1" "$mnt/boot"

run dnf --releasever="$release_ver" \
  --installroot="$mnt" --setopt=install_weak_deps=False \
  install -y "${RECOVERY_PACKAGES[@]}"

run mount -t proc proc "$mnt/proc"
run mount -t sysfs sysfs "$mnt/sys"
run mount --rbind /dev "$mnt/dev"

kver=$(ls -1 "$mnt/usr/lib/modules" | head -1)
[[ -n "$kver" ]] || die "no kernel modules installed in recovery root"
run cp "$mnt/usr/lib/modules/$kver/vmlinuz" "$mnt/boot/vmlinuz-$kver"
run chroot "$mnt" dracut --no-hostonly --force "/boot/initramfs-$kver.img" "$kver"
[[ -s "$mnt/boot/vmlinuz-$kver" && -s "$mnt/boot/initramfs-$kver.img" ]] || die "recovery kernel/initramfs missing"

echo "=== Installing systemd-boot ==="
run bootctl --esp-path="$mnt/boot" --boot-path="$mnt/boot" install
run chroot "$mnt" systemctl set-default multi-user.target
run chroot "$mnt" systemctl enable NetworkManager
run chroot "$mnt" useradd --create-home --groups wheel duck
printf 'duck:%s\n' "$(cat "$PASSWORD_HASH_FILE")" | chroot "$mnt" chpasswd --encrypted
run chroot "$mnt" mkdir -p /data

echo "=== Writing boot loader config ==="
cat > "$mnt/boot/loader/loader.conf" <<EOF
default ducktop-recovery
timeout 3
console-mode max
EOF
cat > "$mnt/boot/loader/entries/ducktop-recovery.conf" <<EOF
title   Ducktop2 Recovery
linux   /vmlinuz-$kver
initrd  /initramfs-$kver.img
options root=LABEL=ducktop-recovery rw
EOF
cat > "$mnt/boot/loader/entries/ducktop-recovery-safe.conf" <<EOF
title   Ducktop2 Recovery (safe mode)
linux   /vmlinuz-$kver
initrd  /initramfs-$kver.img
options root=LABEL=ducktop-recovery rw rd.break=pre-mount
EOF

echo "=== Writing recovery fstab ==="
cat > "$mnt/etc/fstab" <<EOF
UUID=$(blkid -s UUID -o value "${DEVICE}p1") /boot vfat defaults,noatime 0 2
UUID=$(blkid -s UUID -o value "${DEVICE}p2") / ext4 defaults,noatime 0 1
UUID=$(blkid -s UUID -o value "${DEVICE}p3") swap swap defaults 0 0
UUID=$(blkid -s UUID -o value "${DEVICE}p4") /data ext4 defaults,noatime 0 2
EOF

run umount -R "$mnt"
trap - EXIT
rm -rf "$mnt"

echo ""
echo "eMMC setup complete."
echo "Next: set UEFI boot order NVMe-first/eMMC-fallback (Mu BIOS F7 boot menu)."
echo "Then, from the daily driver:"
echo "  sudo bash install/emmc-recovery-setup.sh --configure-hibernate --yes"
