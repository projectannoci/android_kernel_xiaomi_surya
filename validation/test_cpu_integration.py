from pathlib import Path
import subprocess,re
s=Path('kernel/kernel/sched/cpufreq_schedutil.c').read_text()
def function(name):
 a=s.index(name);a=s.rfind('static ',0,a);start=s.index('{',a);depth=1;b=start+1
 while depth:
  depth+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a:b]
Path('validation/cpu_actual.inc').write_text(function('sugov_up_down_rate_limit(')+'\n'+function('get_next_freq(struct'))
up=re.search(r'tunables->up_rate_limit_us = (\d+);',s).group(1)
down=re.search(r'tunables->down_rate_limit_us = (\d+);',s).group(1)
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-iquote','kernel/include/linux','-DTEST_UP='+up,'-DTEST_DOWN='+down,'validation/test_cpu_integration.c','-o','validation/test_cpu_integration'],check=True)
subprocess.run(['./validation/test_cpu_integration'],check=True)
