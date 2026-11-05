from pathlib import Path
import hashlib,os,stat,struct,subprocess,zipfile,json
r=Path.cwd();zpath=Path(os.environ['KERNEL_ZIP']);image=(r/'out/arch/arm64/boot/Image').read_bytes()
with zipfile.ZipFile(zpath) as z:
 assert z.testzip() is None
 names=z.namelist()
 for n in names:
  assert not n.startswith('/') and '..' not in Path(n).parts,n
  assert n not in ('boot.img','dtb','dtbo','dtbo.img','ramdisk.cpio'),n
 assert z.read('Image')==image
 assert image[56:60]==b'ARM\x64'
 assert struct.unpack_from('<Q',image,16)[0]>=len(image)
 assert b'Singularity v1 @ProjectNoci #1' in z.read('anykernel.sh')
 for n in ['META-INF/com/google/android/update-binary','tools/busybox','tools/magiskboot','tools/avbfix']:
  assert (z.getinfo(n).external_attr>>16)&stat.S_IXUSR,n
 for line in z.read('payload.sha256').decode().splitlines():
  digest,name=line.split();assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
 for n in ['anykernel.sh','tools/ak3-core.sh','META-INF/com/google/android/update-binary']:
  p=r/'validation'/('syntax-'+Path(n).name);p.write_bytes(z.read(n));subprocess.run(['sh','-n',str(p)],check=True);p.unlink()
report={'zip_crc':True,'built_image_exact':True,'arm64_image':True,'manifest':True,'installer_syntax':True,'executable_modes':True,'paths':True,'kernel_only_no_ROM_blobs':True,'zip_bytes':zpath.stat().st_size,'zip_sha256':hashlib.sha256(zpath.read_bytes()).hexdigest()}
(r/'validation/evidence/package.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
