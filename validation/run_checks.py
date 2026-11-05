import subprocess
for command in [['python3','validation/test_charger_startup.py'],['python3','validation/test_gpu_oc.py'],['python3','validation/test_dvfs.py'],['python3','validation/test_cpu_integration.py'],['python3','validation/test_gpu_integration.py'],['python3','validation/test_device_gate.py'],['python3','validation/test_filename_trans.py','KernelSU-Next/kernel/selinux/sepolicy.c'],['python3','validation/verify_binary.py']]:
 subprocess.run(command,check=True)
print('PASS host checks; physical device boot/root/FPS remain untested')
