from pathlib import Path
import subprocess, tempfile, os
package=Path(os.environ.get('PACKAGE_DIR','AnyKernel3'))
text=(package/'META-INF/com/google/android/update-binary').read_text()
start=text.index('do_devicecheck() {');end=text.index('do_levelcheck() {',start)
functions=text[start:end]
prelude='''ui_print() { :; }
abort() { exit 71; }
getprop() { case "$1" in ro.product.device|ro.build.product) echo "$TEST_DEVICE";; ro.product.vendor.device) echo "$TEST_VENDOR";; esac; }
file_getprop() {
  if [ "$1" = /system/build.prop ]; then echo "$TEST_ANDROID"; else sed -n "s/^$2=//p" "$1"; fi
}
'''
for device,vendor,android,allowed in [('surya','','13',True),('surya','','14',True),('surya','','15',True),('surya','','16',True),('vayu','','13',False),('karna','','13',False),('','','13',False),('surya','','12',False),('','surya','13',True)]:
    env=dict(os.environ,TEST_DEVICE=device,TEST_VENDOR=vendor,TEST_ANDROID=android)
    run=subprocess.run(['bash','-c',prelude+functions+'\ndo_devicecheck; do_versioncheck\n'],cwd=package,env=env,capture_output=True)
    assert (run.returncode==0)==allowed,(device,vendor,android,run.returncode,run.stderr)
    print('PASS',device or 'unknown',vendor or '-',android,'accept' if allowed else 'reject')
