#!/usr/bin/env python3
"""Repack the supplied Topaz boot and repair its existing unsigned AVB hash.

This never changes verification flags, signing algorithm, rollback counters or keys.
Signed vbmeta is rejected because this tool has no signing key.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, struct, subprocess, tempfile

def avb_hashes(data, repair=False):
    b=bytearray(data)
    if len(b)<64 or b[-64:-60]!=b'AVBf':
        raise ValueError('Expected original AVB footer')
    magic,major,minor,image_size,position,vbmeta_size,_=struct.unpack('>4sIIQQQ28s',b[-64:])
    if major!=1 or not 0<image_size<=position or position+vbmeta_size>len(b)-64 or vbmeta_size<256:
        raise ValueError('Invalid AVB image bounds')
    v=b[position:position+256]
    if v[:4]!=b'AVB0':raise ValueError('Invalid vbmeta magic')
    auth_size,aux_size=struct.unpack_from('>2Q',v,12)
    algorithm=struct.unpack_from('>I',v,28)[0]
    if algorithm!=0 or auth_size!=0:
        raise ValueError('Signed vbmeta requires its original signing key; refusing modification')
    if 256+auth_size+aux_size>vbmeta_size:raise ValueError('Invalid auxiliary bounds')
    offset,length=struct.unpack_from('>2Q',v,96)
    if offset+length>aux_size:raise ValueError('Invalid descriptor bounds')
    start=position+256+auth_size+offset;end=start+length;records=[]
    while start<end:
        if start+16>end:raise ValueError('Truncated descriptor')
        tag,following=struct.unpack_from('>2Q',b,start)
        stop=start+16+following
        if stop>end or stop<start:raise ValueError('Invalid descriptor length')
        if tag==2:
            if stop-start<132:raise ValueError('Truncated hash descriptor')
            old_size=struct.unpack_from('>Q',b,start+16)[0]
            algorithm_name=bytes(b[start+24:start+56]).split(b'\0')[0]
            name_len,salt_len,digest_len,flags=struct.unpack_from('>4I',b,start+56)
            p=start+132
            if p+name_len+salt_len+digest_len>stop:raise ValueError('Hash field overflow')
            name=bytes(b[p:p+name_len]);p+=name_len
            salt=bytes(b[p:p+salt_len]);p+=salt_len
            if name!=b'boot' or algorithm_name!=b'sha256' or digest_len!=32:
                raise ValueError('Unsupported hash descriptor')
            if old_size>len(b)-64:raise ValueError('Descriptor image size exceeds partition')
            previous=bytes(b[p:p+digest_len])
            was_valid=hashlib.sha256(salt+b[:old_size]).digest()==previous
            if repair:
                struct.pack_into('>Q',b,start+16,image_size)
                b[p:p+32]=hashlib.sha256(salt+b[:image_size]).digest()
            current_size=struct.unpack_from('>Q',b,start+16)[0]
            valid=hashlib.sha256(salt+b[:current_size]).digest()==b[p:p+32]
            records.append({'partition':'boot','previous_digest_valid':was_valid,
                'digest_valid':valid,'descriptor_image_size':current_size,
                'footer_image_size':image_size})
        start=stop
    if len(records)!=1:raise ValueError('Expected one boot hash descriptor')
    return bytes(b),{'vbmeta_algorithm':algorithm,'vbmeta_flags':struct.unpack_from('>I',v,120)[0],
        'hashes':records}

def run(args):
    boot=Path(args.boot).resolve();image=Path(args.image).resolve();dtb=Path(args.dtb).resolve()
    output=Path(args.output).resolve();tool=Path(args.magiskboot).resolve()
    original=boot.read_bytes()
    if args.expected_boot_sha256 and hashlib.sha256(original).hexdigest()!=args.expected_boot_sha256:
        raise ValueError('Reference boot differs from the pinned Topaz input')
    if original[:8]!=b'ANDROID!' or struct.unpack_from('<I',original,40)[0]!=2:
        raise ValueError('Expected Android boot header v2')
    if struct.unpack_from('<I',original,36)[0]!=4096 or len(original)!=134217728:
        raise ValueError('Unexpected reference boot geometry')
    _,original_avb=avb_hashes(original)
    if not original_avb['hashes'][0]['digest_valid']:raise ValueError('Original AVB hash invalid')
    command=([str(Path(args.qemu).resolve())] if args.qemu else [])+[str(tool)]
    env=dict(os.environ,PATCHVBMETAFLAG='false')
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        def call(extra,cwd):
            r=subprocess.run(command+extra,cwd=cwd,env=env,capture_output=True)
            if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
        call(['unpack','-h',str(boot)],tmp)
        ramdisk=(tmp/'ramdisk.cpio').read_bytes();header=(tmp/'header').read_bytes()
        shutil.copy2(image,tmp/'kernel');shutil.copy2(dtb,tmp/'dtb')
        candidate=tmp/'candidate.img'
        call(['repack',str(boot),str(candidate)],tmp)
        candidate_bytes,report=avb_hashes(candidate.read_bytes(),repair=True)
        if report['vbmeta_flags']!=original_avb['vbmeta_flags']:raise ValueError('Verification flags changed')
        if len(candidate_bytes)!=len(original):raise ValueError('Repack changed partition size')
        candidate.write_bytes(candidate_bytes)
        check=tmp/'check';check.mkdir()
        call(['unpack','-h',str(candidate)],check)
        checks={
            'kernel_exact':(check/'kernel').read_bytes()==image.read_bytes(),
            'dtb_exact':(check/'dtb').read_bytes()==dtb.read_bytes(),
            'ramdisk_archive_byte_exact':(check/'ramdisk.cpio').read_bytes()==ramdisk,
            'header_text_exact':(check/'header').read_bytes()==header,
            'header_regions_exact':all(original[a:b]==candidate_bytes[a:b] for a,b in [(12,16),(20,48),(48,576),(608,1660)]),
            'kernel_gzip_preserved':original[4096:4098]==candidate_bytes[4096:4098]==b'\x1f\x8b',
            'avb_hash_valid':report['hashes'][0]['digest_valid'],
            'vbmeta_flags_preserved':report['vbmeta_flags']==original_avb['vbmeta_flags']}
        if not all(checks.values()):raise ValueError(str(checks))
        output.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(candidate,output)
    report.update(checks)
    report.update(output_bytes=len(candidate_bytes),output_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        input_boot_sha256=hashlib.sha256(original).hexdigest())
    print(json.dumps(report,indent=2))
    if args.report:Path(args.report).write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ['boot','image','dtb','output','magiskboot']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--qemu');parser.add_argument('--report');parser.add_argument('--expected-boot-sha256')
    run(parser.parse_args())
