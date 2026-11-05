from pathlib import Path
import subprocess
s=Path('kernel/drivers/gpu/msm/adreno.c').read_text()
def fn(name):
    a=s.index(name); a=s.rfind('static ',0,a); b=s.index('{',a); depth=1; e=b+1
    while depth:
        depth+=(s[e]=='{')-(s[e]=='}'); e+=1
    return s[a:e]
prefix=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#define EINVAL 22
#define KGSL_MAX_PWRLEVELS 16
#define KGSL_CORE_ERR(...) ((void)0)
#define IS_ERR(p) ((intptr_t)(p)<0)
struct device_node {struct device_node *child,*next; unsigned int reg,freq,bus;};
struct device {struct device_node *of_node;};
struct platform_device {struct device dev;};
struct kgsl_pwrlevel {unsigned int gpu_freq,bus_freq,bus_min,bus_max;};
struct kgsl_pwrctrl {unsigned int num_pwrlevels; struct kgsl_pwrlevel pwrlevels[16];};
struct kgsl_device {struct platform_device *pdev;struct kgsl_pwrctrl pwrctrl;};
struct adreno_device {struct kgsl_device dev;};
struct clk {int unused;}; struct dev_pm_opp {int unused;};
static struct clk clock_obj; static struct dev_pm_opp opp_obj;
static int chip618=1,machine=1,clock_error=0,opp_error=0,rounded=0;
static unsigned int corner=384;
#define KGSL_DEVICE(p) (&(p)->dev)
#define for_each_child_of_node(n,c) for((c)=(n)->child;(c);(c)=(c)->next)
static inline int adreno_is_a618(struct adreno_device *a){return chip618;}
static inline int of_machine_is_compatible(const char *s){return machine;}
static inline void *of_find_property(struct device_node *n,const char *s,void *p){return 0;}
static inline int dev_pm_opp_of_add_table(struct device *d){return 0;}
static inline struct clk *clk_get(struct device *d,const char *n){return (clock_error==1 || (clock_error==2 && !strcmp(n,"src_clk")))?(void*)-1:&clock_obj;}
static inline long clk_round_rate(struct clk *c,unsigned long f){return rounded?rounded:(long)f;}
static inline void clk_put(struct clk *c){}
static inline struct dev_pm_opp *dev_pm_opp_find_freq_exact(struct device *d,unsigned long f,bool en){return opp_error?(void*)-1:&opp_obj;}
static inline unsigned long dev_pm_opp_get_voltage(struct dev_pm_opp *o){return corner;}
static inline void dev_pm_opp_put(struct dev_pm_opp *o){}
static inline void dev_info(struct device *d,const char *f,...){}
static int adreno_of_read_property(struct device_node *n,const char *s,unsigned int *p){
 if(!strcmp(s,"reg"))*p=n->reg;else if(!strcmp(s,"qcom,gpu-freq"))*p=n->freq;else if(!strcmp(s,"qcom,bus-freq"))*p=n->bus;else return -1;return 0;}
static inline int of_property_read_u32(struct device_node *n,const char *s,unsigned int *p){return -1;}
'''
helpers=fn('singularity_apply_gpu_oc(') if 'static void singularity_apply_gpu_oc(' in s else ''
main=r'''
int main(void){
 struct device_node idle={0,0,2,0,0},low={0,&idle,1,565000000,9},top={0,&low,0,825000000,12},root={&top};
 struct platform_device p={0};struct adreno_device a={.dev.pdev=&p};
 assert(adreno_of_parse_pwrlevels(&a,&root)==0);
 assert(a.dev.pwrctrl.pwrlevels[0].gpu_freq==825000000);
 assert(a.dev.pwrctrl.num_pwrlevels==3 && a.dev.pwrctrl.pwrlevels[1].gpu_freq==565000000);
 assert(a.dev.pwrctrl.pwrlevels[2].gpu_freq==0 && a.dev.pwrctrl.pwrlevels[0].bus_freq==12);
 for(int mode=0;mode<6;mode++){
  chip618=mode!=0;machine=mode!=1;clock_error=mode==2;opp_error=mode==3;rounded=mode==4?825000000:0;corner=mode==5?0:384;
  assert(adreno_of_parse_pwrlevels(&a,&root)==0);
  assert(a.dev.pwrctrl.pwrlevels[0].gpu_freq==825000000);
 }
 chip618=machine=1;clock_error=opp_error=rounded=0;corner=384;
 clock_error=2;assert(adreno_of_parse_pwrlevels(&a,&root)==0);assert(a.dev.pwrctrl.pwrlevels[0].gpu_freq==825000000);clock_error=0;
 top.freq=610000000;assert(adreno_of_parse_pwrlevels(&a,&root)==0);assert(a.dev.pwrctrl.pwrlevels[0].gpu_freq==610000000);
 top.freq=700000000;assert(adreno_of_parse_pwrlevels(&a,&root)==0);assert(a.dev.pwrctrl.pwrlevels[0].gpu_freq==700000000);
 top.freq=800000000;assert(adreno_of_parse_pwrlevels(&a,&root)==0);assert(a.dev.pwrctrl.pwrlevels[0].gpu_freq==800000000);
 top.freq=500000000;assert(adreno_of_parse_pwrlevels(&a,&root)==0);assert(a.dev.pwrctrl.pwrlevels[0].gpu_freq==500000000);
 puts("PASS real KGSL parser: original speed-bin frequencies, indices, bus votes and idle retained");
}
'''
Path('validation/gpu_oc_actual.c').write_text(prefix+helpers+'\n'+fn('adreno_of_parse_pwrlevels(')+main)
subprocess.run(['gcc','-std=c11','-Wno-unused-function','validation/gpu_oc_actual.c','-o','validation/gpu_oc_actual'],check=True)
subprocess.run(['validation/gpu_oc_actual'],check=True)
