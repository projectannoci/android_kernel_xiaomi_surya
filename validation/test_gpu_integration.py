from pathlib import Path
import re, subprocess
s=Path('kernel/drivers/devfreq/governor_msm_adreno_tz.c').read_text()
a=s.index('static inline int devfreq_get_freq_level(')
b=s.index('static int tz_start(',a)
constants='\n'.join(re.findall(r'^#define (?:FLOOR|MIN_BUSY|CEILING)\s+[^\n]+',s,re.M))
Path('validation/gpu_actual.inc').write_text(constants+'\n'+s[a:b])
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Wno-unused-parameter','-Werror','-iquote','kernel/include/linux','validation/test_gpu_integration.c','-o','validation/test_gpu_integration'],check=True)
subprocess.run(['./validation/test_gpu_integration'],check=True)
