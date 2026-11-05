"""Run the kernel-only package with original and synthetic alternate-ROM inputs.
All block paths are mapped to regular files. ARM utilities run under qemu-arm.
"""
from pathlib import Path
import os, shutil, struct, subprocess, tempfile, importlib.util, hashlib, json, shlex

root=Path.cwd();(root/'evidence').mkdir(exist_ok=True);package=Path(os.environ.get('PACKAGE_DIR',root/'AnyKernel3')).resolve();qemu=Path(os.environ.get('QEMU_ARM',root/'host-tools/usr/bin/qemu-arm')).resolve()
bb=package/'tools/busybox';mb=package/'tools/magiskboot'
env=dict(os.environ,LD_LIBRARY_PATH=os.environ.get('HOST_LIB',str(root/'host-tools/usr/lib/x86_64-linux-gnu')))
original=Path(os.environ['REFERENCE_BOOT']).resolve()
spec=importlib.util.spec_from_file_location('avb_reference',root/'validation/repack_boot.py')
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
result=[]
def command(args,cwd):
    r=subprocess.run([str(qemu),str(mb)]+args,cwd=cwd,env=env,capture_output=True)
    assert r.returncode==0,r.stderr.decode(errors='replace')

with tempfile.TemporaryDirectory() as outer:
    outer=Path(outer);bindir=outer/'bin';bindir.mkdir()
    for applet in subprocess.check_output([str(qemu),str(bb),'--list'],env=env,text=True).splitlines():
        path=bindir/applet
        path.write_text('#!/bin/sh\nexec '+shlex.join([str(qemu),str(bb),applet])+' "$@"\n');path.chmod(0o755)
    bridge=outer/'busybox-bridge'
    bridge.write_text('#!/bin/sh\nexec '+shlex.join([str(qemu),str(bb)])+' "$@"\n');bridge.chmod(0o755)
    variant=outer/'variant';variant.mkdir()
    command(['unpack','-h',str(original)],variant)
    (variant/'marker.txt').write_text('Synthetic alternate ROM ramdisk, not a tested real ROM\n')
    command(['cpio','ramdisk.cpio','add 0644 rom-variant.txt '+str(variant/'marker.txt')],variant)
    data=bytearray((variant/'dtb').read_bytes());struct.pack_into('>I',data,28,1);(variant/'dtb').write_bytes(data)
    header=(variant/'header').read_text().replace('cmdline=','cmdline=noci_fixture=2 ',1);(variant/'header').write_text(header)
    command(['repack',str(original),str(variant/'boot.img')],variant)
    data=bytearray((variant/'boot.img').read_bytes());position=struct.unpack_from('>Q',data,len(data)-44)[0]
    struct.pack_into('>Q',data,position+112,42)
    desc_off,desc_len=struct.unpack_from('>2Q',data,position+96);at=position+256+desc_off;end=at+desc_len
    while at<end:
        tag,following=struct.unpack_from('>2Q',data,at)
        if tag==2:
            name_len,salt_len=struct.unpack_from('>2I',data,at+56);salt_at=at+132+name_len
            for i in range(salt_len):data[salt_at+i]^=0x5a
        at+=16+following
    data,_=reference.avb_hashes(data,repair=True);(variant/'boot.img').write_bytes(data)
    for name,input_boot in [('current_rom_original',original),('synthetic_other_rom',variant/'boot.img'),('helper_failure',original),('write_failure',original),('bad_readback',original)]:
        if os.environ.get('TEST_FIXTURES') and name not in os.environ['TEST_FIXTURES'].split(','): continue
        home=outer/name;home.mkdir();tools=home/'tools';tools.mkdir()
        fake=home/'fake-dev';targets=fake/'bootdevice/by-name';targets.mkdir(parents=True)
        shutil.copy2(input_boot,targets/'boot');shutil.copy2(Path(os.environ['REFERENCE_DTBO']).resolve(),targets/'dtbo')
        dtbo_before=(targets/'dtbo').read_bytes()
        shutil.copy2(package/'Image',home/'Image')
        # Only executable loader paths are remapped for emulation; actual payload hashes remain verified.
        manifest=(package/'payload.sha256').read_text().replace('  tools/avbfix','  '+str(package/'tools/avbfix'))
        (home/'payload.sha256').write_text(manifest)
        (tools/'magiskboot').write_text('#!/bin/sh\nexec '+shlex.join([str(qemu),str(mb)])+' "$@"\n');(tools/'magiskboot').chmod(0o755)
        (tools/'avbfix').write_text('#!/bin/sh\n[ "$TEST_MODE" = helper_failure ] && exit 1\nexec '+shlex.join([str(qemu),str(package/'tools/avbfix')])+' "$1" '+shlex.quote(str(bridge))+' "$3"\n');(tools/'avbfix').chmod(0o755)
        core=(package/'tools/ak3-core.sh').read_text();core=core[:core.rfind('setup_ak;')].replace('/dev/block',str(fake))
        core+='''
ui_print(){ :; }
abort(){ echo "ABORT: $*" >&2; exit 70; }
blockdev(){ case "$1" in --getsize64) wc -c < "$2";; --getro) echo 0;; --setrw|--setro) :;; *) return 1;; esac; }
dd(){
 echo "$*" >> "$home/write-intent"
 write_target=
 for arg in "$@"; do case "$arg" in of=*) write_target=${arg#of=};; esac; done
 if test "$write_target" = "$block" && test "$TEST_MODE" = write_failure; then return 1; fi
 command dd "$@" || return $?
 if test "$write_target" = "$block" && test "$TEST_MODE" = bad_readback; then
   printf X | command dd of="$block" bs=1 seek=4096 conv=notrunc
 fi
}
'''
        (tools/'ak3-core.sh').write_text(core)
        (home/'anykernel.sh').write_text((package/'anykernel.sh').read_text().replace('/dev/block',str(fake)))
        r=subprocess.run([str(qemu),str(bb),'ash','anykernel.sh'],cwd=home,
            env=dict(env,PATH=str(bindir)+':'+os.environ['PATH'],OUTFD='1',TEST_MODE=name),capture_output=True,timeout=90)
        (root/('evidence/'+name+'-installer.log')).write_bytes(r.stdout+r.stderr)
        if name in ('helper_failure','write_failure','bad_readback'):
            assert r.returncode==70,(name,r.stderr.decode(errors='replace'))
            if name!='bad_readback':assert (targets/'boot').read_bytes()==input_boot.read_bytes()
            if name=='helper_failure':assert 'of='+str(targets/'boot') not in (home/'write-intent').read_text()
            if name=='bad_readback':assert b'Boot readback verification failed' in r.stderr
            assert (targets/'dtbo').read_bytes()==dtbo_before
            result.append({'fixture':name,'rejected':True,'dtbo_unchanged':True})
            print('PASS kernel-only failure guard:',name,flush=True)
            continue
        assert r.returncode==0,r.stderr.decode(errors='replace')
        before=home/'before';after=home/'after';before.mkdir();after.mkdir()
        command(['unpack','-h',str(input_boot)],before);command(['unpack','-h',str(targets/'boot')],after)
        assert (after/'kernel').read_bytes()==(package/'Image').read_bytes()
        for component in ['ramdisk.cpio','dtb','header']:
            assert (before/component).read_bytes()==(after/component).read_bytes(),(name,component)
        assert (targets/'dtbo').read_bytes()==dtbo_before
        writes=(home/'write-intent').read_text();assert 'of='+str(targets/'dtbo') not in writes
        assert 'of='+str(targets/'boot') in writes
        output=(targets/'boot').read_bytes();_,report=reference.avb_hashes(output)
        def compressed_ramdisk(data):
            page=struct.unpack_from('<I',data,36)[0];kernel_size,ramdisk_size=struct.unpack_from('<I',data,8)[0],struct.unpack_from('<I',data,16)[0]
            offset=page+(kernel_size+page-1)//page*page
            return data[offset:offset+ramdisk_size]
        compressed_before=compressed_ramdisk(input_boot.read_bytes());compressed_after=compressed_ramdisk(output)
        assert compressed_before[:4]==compressed_after[:4], 'Ramdisk compression changed'
        if name=='current_rom_original' and os.environ.get('REPACK_OUTPUT'):
            Path(os.environ['REPACK_OUTPUT']).write_bytes(output)
        assert report['hashes'][0]['digest_valid'] and report['vbmeta_flags']==0
        pos1=struct.unpack_from('>Q',input_boot.read_bytes(),input_boot.stat().st_size-44)[0]
        pos2=struct.unpack_from('>Q',output,len(output)-44)[0]
        assert input_boot.read_bytes()[pos1:pos1+256]==output[pos2:pos2+256]
        result.append({'fixture':name,'kernel_exact':True,'ramdisk_cpio_byte_exact':True,'ramdisk_compression_preserved':True,'compressed_ramdisk_byte_exact':compressed_before==compressed_after,'dtb_byte_exact':True,
            'dtbo_unchanged_no_write':True,'header_preserved':True,'avb_hash_valid':True,'vbmeta_header_preserved':True})
        print('PASS kernel-only:',name,flush=True)
(root/'evidence/kernelonly-installer-result.json').write_text(json.dumps(result,indent=2))
print('Synthetic fixture proves component preservation only, not real multi-ROM device boot.')
