### Singularity v1 @ProjectNoci #1 - kernel-only installer
properties() { '
kernel.string=Singularity v1 @ProjectNoci #1
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=1
device.name1=surya
supported.versions=13.0-99.9
supported.patchlevels=
'; }

block=/dev/block/bootdevice/by-name/boot
is_slot_device=0
ramdisk_compression=auto
patch_vbmeta_flag=0
. tools/ak3-core.sh

[ -s "$home/payload.sha256" ] || abort "Payload manifest missing."
(cd "$home" && sha256sum -c payload.sha256 >/dev/null 2>&1) || abort "Payload verification failed."

ui_print "Singularity v1 @ProjectNoci #1"
ui_print "surya / OSS vendor / Android 13+"
ui_print "KSU Next"

# Keep this ROM's original ramdisk archive, DTB and all other boot components.
# No ramdisk extraction/reconstruction and no DTBO partition operations.
# Preserve available kernel panic logs before the next boot can replace them.
# No mount, deletion or upload is performed; failure never blocks installation.
save_boot_log() {
  local source found target parent stamp file
  found=0
  for source in /sys/fs/pstore/console-ramoops* /sys/fs/pstore/dmesg-ramoops* /proc/last_kmsg; do
    [ -r "$source" ] && found=1 && break
  done
  [ "$found" = 1 ] || return 0
  stamp=$(date +%Y%m%d-%H%M%S 2>/dev/null)
  parent=
  for target in "${ZIPFILE%/*}" /sdcard/Download /sdcard /cache; do
    case "$target" in ''|.|/sideload*|/tmp|/tmp/*|/dev/*|/proc/*|/sys/*) continue;; esac
    [ -d "$target" ] && [ -w "$target" ] && parent="$target" && break
  done
  [ "$parent" ] || return 0
  target="$parent/Singularity-bootlogs-$stamp-$$"
  mkdir -p "$target" 2>/dev/null || return 0
  found=0
  for source in /sys/fs/pstore/console-ramoops* /sys/fs/pstore/dmesg-ramoops* /proc/last_kmsg; do
    [ -r "$source" ] || continue
    file=${source##*/}
    if cp "$source" "$target/$file.txt" 2>/dev/null; then
      chmod 644 "$target/$file.txt" 2>/dev/null
      found=1
    fi
  done
  [ "$found" = 1 ] && ui_print "Kernel log saved: $target"
  return 0
}
save_boot_log
split_boot
flash_boot
ui_print "Kernel installed; boot readback verified."
