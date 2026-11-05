from pathlib import Path
import os,subprocess,struct,json,hashlib
r=Path.cwd();out=r/'out';cfg=(out/'.config').read_text();mode=os.environ.get('VERIFY_MODE','ksun' if 'CONFIG_KSU=y\n' in cfg else 'none');data=(out/'arch/arm64/boot/Image').read_bytes()
assert data[56:60]==b'ARM\x64' and len(data)>1000000
assert struct.unpack_from('<Q',data,16)[0]>=len(data)
for key in ['CONFIG_SCHED_WALT=y','CONFIG_DM_CRYPT=y','CONFIG_DM_DEFAULT_KEY=y','CONFIG_F2FS_FS_ENCRYPTION=y','CONFIG_SCSI_UFS_CRYPTO_QTI=y','CONFIG_RD_LZ4=y','CONFIG_LTO_CLANG=y','CONFIG_THINLTO=y','CONFIG_MODULE_SIG_FORCE=y','CONFIG_MODVERSIONS=y','CONFIG_DEVFREQ_GOV_QCOM_ADRENO_TZ=y']:
 assert key+'\n' in cfg,key
assert 'CONFIG_KPROBES=y\n' not in cfg and 'CONFIG_KSU_KPROBES_HOOK=y\n' not in cfg
embedded=subprocess.check_output([str(r/'kernel/scripts/extract-ikconfig'),str(out/'arch/arm64/boot/Image')],text=True)
settings=lambda text:sorted(l for l in text.splitlines() if l.startswith('CONFIG_') or l.startswith('# CONFIG_'))
assert settings(cfg)==settings(embedded)
nm=str((Path(os.environ.get('CLANG_DIR','toolchain14'))/'bin/llvm-nm').resolve());symbols=subprocess.check_output([nm,str(out/'vmlinux')],text=True);names={l.split()[-1] for l in symbols.splitlines() if l.split()}
assert 'register_kprobe' not in names
refs={'fs/exec.o':'ksu_handle_execveat','fs/open.o':'ksu_handle_faccessat','fs/stat.o':'ksu_handle_stat','fs/read_write.o':'ksu_handle_vfs_read','drivers/input/input.o':'ksu_handle_input_handle_event'}
for file,symbol in refs.items():
 text=subprocess.check_output([nm,str(out/file)],text=True)
 if mode=='ksun':assert ('U '+symbol) in text,(file,symbol)
 else:assert symbol not in text,(file,symbol)
if mode=='ksun':
 assert 'CONFIG_KSU=y\n' in cfg and 'CONFIG_KSU_LSM_SECURITY_HOOKS=y\n' in cfg
 for symbol in ['kernelsu_init']+list(refs.values()):assert symbol in names,symbol
 ir=subprocess.check_output([str((Path(os.environ.get('CLANG_DIR','toolchain14'))/'bin/llvm-dis').resolve()),str(out/'drivers/kernelsu/core_hook.o'),'-o','-'],text=True)
 assert 'i32 12797' in ir, 'Driver API version not present in compiled root IR'
else:
 assert 'CONFIG_KSU=y\n' not in cfg and 'kernelsu_init' not in names
for name,digest in json.loads((r/'provenance.json').read_text())['performance_source_sha256'].items():
 assert hashlib.sha256((r/'kernel'/name).read_bytes()).hexdigest()==digest,name
release=(out/'include/config/kernel.release').read_text().strip();assert release=='4.14.190-Singularity-v1-ProjectNoci'
report={'mode':mode,'release':release,'image_bytes':len(data),'image_sha256':hashlib.sha256(data).hexdigest(),'arm64_image':True,'embedded_effective_config_exact':True,'probe_backend_absent':True,'manual_root_object_references':mode=='ksun','manual_root_linked':mode=='ksun','release_performance_source_hashes_verified':True,'device_boot':'untested','FPS':'unmeasured','vendor_module_ABI':'unknown without vendor modules'}
(r/'validation/evidence'/('binary-'+mode+'.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
