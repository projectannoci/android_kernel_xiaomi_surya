#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CLANG_DIR=${CLANG_DIR:-"$ROOT/toolchain14"}
JOBS=${JOBS:-8}
ROOT_MODE=${ROOT_MODE:-ksun}
AVBFIX_CC=${AVBFIX_CC:-arm-linux-gnueabi-gcc}
export PATH="$CLANG_DIR/bin:$PATH"
export ARCH=arm64
export KBUILD_BUILD_USER=ProjectNoci
export KBUILD_BUILD_HOST=Singularity
export KBUILD_BUILD_VERSION=1
args=(HOSTCC=gcc HOSTCXX=g++ O="$ROOT/out" CC=clang LD=ld.lld AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump STRIP=llvm-strip CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32=arm-linux-gnueabi- LLVM=1 LLVM_IAS=1)
make -C "$ROOT/kernel" "${args[@]}" singularity_defconfig
case "$ROOT_MODE" in
  ksun) ;;
  none)
    "$ROOT/kernel/scripts/config" --file "$ROOT/out/.config" --disable KSU
    make -C "$ROOT/kernel" "${args[@]}" olddefconfig
    ;;
  *) echo "ROOT_MODE must be ksun or none" >&2; exit 1;;
esac
make -C "$ROOT/kernel" "${args[@]}" -j"$JOBS" Image
mkdir -p "$ROOT/dist" "$ROOT/out/package"
"$AVBFIX_CC" -Os -nostdlib -static -fno-pie -no-pie -fno-builtin -fomit-frame-pointer -fno-stack-protector -fno-unwind-tables -fno-asynchronous-unwind-tables -march=armv7-a -marm -Wl,--build-id=none -Wl,-e,_start -o "$ROOT/out/avbfix" "$ROOT/installer-tools/avbfix.c"
# Stage only installer files, never historical ROM boot/DTB/DTBO fixtures.
stage=$(mktemp -d "$ROOT/out/package/kernelonly.XXXXXX")
trap 'rm -rf "$stage"' EXIT
cp -a "$ROOT/AnyKernel3/tools" "$ROOT/AnyKernel3/META-INF" "$stage/"
cp "$ROOT/AnyKernel3/anykernel.sh" "$ROOT/AnyKernel3/banner" "$ROOT/AnyKernel3/LICENSE" "$stage/"
cp "$ROOT/out/arch/arm64/boot/Image" "$stage/Image"
cp "$ROOT/out/avbfix" "$stage/tools/avbfix"
chmod 755 "$stage/tools/avbfix"
if [ "$ROOT_MODE" = none ]; then
  sed -i 's/Performance R5 \/ KSU Next manual/Performance R5 \/ diagnostic no root/' "$stage/anykernel.sh"
  artifact="$ROOT/dist/Singularity_v1_ProjectNoci_surya_R5_NoRoot_Diagnostic.zip"
else
  artifact="$ROOT/dist/Singularity_v1_ProjectNoci_1_surya_Final_KSUN.zip"
fi
rm -f "$artifact"
(cd "$stage"; sha256sum Image tools/avbfix > payload.sha256; zip -qr9 "$artifact" .)
echo "$artifact"
