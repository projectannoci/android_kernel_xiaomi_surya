Singularity v1 @ProjectNoci — POCO X3 NFC surya — R5

R4 failed on the tester after original ROM boot/DTBO restoration. There is no
panic trace from the phone, so its precise failure remains unconfirmed.
R5 tests the root/probe hypothesis: SukiSU is removed and replaced by official
KernelSU Next v1.0.9, commit2241696498ce9dd742ce80b52c3ed6cca26e03ea.
KSU_VERSION12797 is pinned independently of Git history. Use the supplied
matching official Manager1.0.9; newer Manager compatibility is not claimed.

Manual hooks: do_execveat_common (after invalid filename rejection), faccessat,
vfs_statx, vfs_read (boot rc injection) and input_handle_event (safe mode).
The exec hook passes addresses of real fd/flags and correctly shaped native
or compat argv/envp structures. Native LSM hooks handle privileges/credentials.
KPROBES and KSU_KPROBES_HOOK are disabled. The old SukiSU tree is not included.
Reviewed path_umount backport retained; build-time source rewriting removed.
KernelSU policy code uses this vendor tree's native pointer-array layout and
4.14 filename-transition key/target bitmap, verified against a failing upstream
implementation fixture before applying the compatibility fix.

Kernel base remains f9fa6c63a4291960ac6ac87ad147a5e702acf2a0, Linux4.14.190,
from the SHA in the current ROM boot banner. Compiler stays Snapdragon14.1.5,
commit699941635db14af1f87a7c6fa6134b5dc3dc79c4 of the pinned compiler mirror.
The tested R4 schedutil headroom/500us-up/20ms-down and AdrenoTZ2ms load policy
remain. Drivers, native WALT/MGLRU/input boost and frequency/thermal caps remain.
No FPS, thermal or physical root/boot success is claimed.

Main package: R5_KSUN_Manual.zip. Diagnostic package: R5_NoRoot_Diagnostic.zip.
The diagnostic has the same kernel/performance/installer but CONFIG_KSU=n;
its shared release suffix is intentional to avoid a vermagic confound.
Use main first. If it remains stuck, the diagnostic distinguishes whether
root integration is involved; it does not itself provide root access.

Both ZIPs are kernel-only. Each repacks the currently installed ROM boot;
original ramdisk, DTB, header and unsigned AVB policy are preserved. No DTBO
write, full-boot payload or data formatting. Signed metadata aborts before write.
When recovery exposes readable console/dmesg ramoops or last_kmsg, the installer
makes a best-effort copy into a new Singularity-bootlogs folder, prints its path,
and leaves original logs intact. Logs are never uploaded automatically. A
missing/unwritable log location does not abort installation.

Build: ./build.sh (ROOT_MODE=ksun default) or ROOT_MODE=none ./build.sh.
CLANG_DIR defaults to ./toolchain14; AVBFIX_CC defaults to arm-linux-gnueabi-gcc.
Need make, gcc/g++, bc, flex, bison, OpenSSL/libelf headers, cross binutils,
ARM cross-GCC, zip and libtinfo5 for this compiler. No ROM image input needed.
All source, config, root compatibility patches and executed evidence included.
No ROM backups, ramdisk binaries or module-signing private key in this archive.
