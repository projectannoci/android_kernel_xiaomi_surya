
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

static int adreno_of_parse_pwrlevels(struct adreno_device *adreno_dev,
		struct device_node *node)
{
	struct kgsl_device *device = KGSL_DEVICE(adreno_dev);
	struct kgsl_pwrctrl *pwr = &device->pwrctrl;
	struct device_node *child;
	int ret;

	/* ADD the GPU OPP table if we define it */
	if (of_find_property(device->pdev->dev.of_node,
			"operating-points-v2", NULL)) {
		ret = dev_pm_opp_of_add_table(&device->pdev->dev);
		if (ret) {
			KGSL_CORE_ERR("Unable to set the GPU OPP table: %d\n",
					ret);
			return ret;
		}
	}

	pwr->num_pwrlevels = 0;

	for_each_child_of_node(node, child) {
		unsigned int index;
		struct kgsl_pwrlevel *level;

		if (adreno_of_read_property(child, "reg", &index))
			return -EINVAL;

		if (index >= KGSL_MAX_PWRLEVELS) {
			KGSL_CORE_ERR("Pwrlevel index %d is out of range\n",
				index);
			continue;
		}

		if (index >= pwr->num_pwrlevels)
			pwr->num_pwrlevels = index + 1;

		level = &pwr->pwrlevels[index];

		if (adreno_of_read_property(child, "qcom,gpu-freq",
			&level->gpu_freq))
			return -EINVAL;

		if (adreno_of_read_property(child, "qcom,bus-freq",
			&level->bus_freq))
			return -EINVAL;

		if (of_property_read_u32(child, "qcom,bus-min",
			&level->bus_min))
			level->bus_min = level->bus_freq;

		if (of_property_read_u32(child, "qcom,bus-max",
			&level->bus_max))
			level->bus_max = level->bus_freq;
	}

	return 0;
}
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
