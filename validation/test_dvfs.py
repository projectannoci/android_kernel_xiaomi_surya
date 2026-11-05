from pathlib import Path
import subprocess
header=Path('kernel/include/linux/singularity_dvfs.h')
assert header.is_file(),'Singularity DVFS policy has not been implemented'
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-iquote','kernel/include/linux','validation/test_dvfs.c','-o','validation/test_dvfs'],check=True)
subprocess.run(['./validation/test_dvfs'],check=True)
