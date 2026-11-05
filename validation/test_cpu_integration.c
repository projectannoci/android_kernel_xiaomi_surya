#include <stdbool.h>
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include "singularity_dvfs.h"
typedef int64_t s64;typedef uint64_t u64;
struct cpufreq_policy {unsigned int cpu;struct{unsigned int max_freq;}cpuinfo;unsigned int cur,min,max;};
struct sugov_policy {struct cpufreq_policy *policy;unsigned int next_freq,cached_raw_freq;u64 last_freq_update_time;s64 up_rate_delay_ns,down_rate_delay_ns;bool need_freq_update;};
static int cpu_perf_mask;
static int cpumask_test_cpu(unsigned int cpu,int mask){(void)mask;return cpu>=6;}
static int arch_scale_freq_invariant(void){return 1;}
#define trace_sugov_next_freq(...) ((void)0)
static unsigned int cpufreq_driver_resolve_freq(struct cpufreq_policy *p,unsigned int f){return f<p->min?p->min:f>p->max?p->max:f;}
#include "cpu_actual.inc"
int main(void){
 struct cpufreq_policy p={6,{2000000},1000000,300000,2000000};
 struct sugov_policy sg={.policy=&p,.next_freq=UINT_MAX,.last_freq_update_time=1000000000,.up_rate_delay_ns=TEST_UP*1000LL,.down_rate_delay_ns=TEST_DOWN*1000LL};
 assert(get_next_freq(&sg,512,1024)==1562500);
 assert(get_next_freq(&sg,0,1024)==300000);
 p.max=1200000;assert(get_next_freq(&sg,512,1024)==1200000);
 assert(get_next_freq(&sg,900,0)==300000);
 sg.next_freq=1000000;
 assert(sugov_up_down_rate_limit(&sg,1000100000,1500000));
 assert(!sugov_up_down_rate_limit(&sg,1000500000,1500000));
 assert(sugov_up_down_rate_limit(&sg,1010000000,500000));
 assert(!sugov_up_down_rate_limit(&sg,1020000000,500000));
 puts("PASS: real schedutil demand, idle, policy cap, 500 us up and 20 ms down limits");
}
