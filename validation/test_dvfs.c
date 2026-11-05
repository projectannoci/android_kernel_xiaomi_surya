#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "singularity_dvfs.h"
int main(void) {
 assert(singularity_cpu_util(0,1024,1)==0);
 assert(singularity_cpu_util(400,1024,1)==400);
 assert(singularity_cpu_util(511,1024,1)==511);
 assert(singularity_cpu_util(512,1024,1)==640);
 assert(singularity_cpu_util(800,1024,1)==928);
 assert(singularity_cpu_util(1000,1024,1)==1024);
 assert(singularity_cpu_util(2000,1024,1)==1024);
 assert(singularity_cpu_util(800,1024,0)==864);
 assert(singularity_cpu_util(0,0,1)==0);
 assert(singularity_cpu_util(ULONG_MAX,ULONG_MAX,1)==ULONG_MAX);
 assert(singularity_gpu_level(5,7,1,1900,2000)==3);
 assert(singularity_gpu_level(5,7,1,1800,2000)==3);
 assert(singularity_gpu_level(5,7,1,1799,2000)==4);
 assert(singularity_gpu_level(5,7,1,1500,2000)==4);
 assert(singularity_gpu_level(5,7,1,1499,2000)==5);
 assert(singularity_gpu_level(5,7,1,1200,2000)==5);
 assert(singularity_gpu_level(5,7,1,1199,2000)==6);
 assert(singularity_gpu_level(5,7,1,1600,2000)==4);
 assert(singularity_gpu_level(5,7,1,1300,2000)==5);
 assert(singularity_gpu_level(5,7,1,200,2000)==6);
 assert(singularity_gpu_level(5,7,-4,1900,2000)==1);
 assert(singularity_gpu_level(0,7,2,1900,2000)==0);
 assert(singularity_gpu_level(1,7,2,1900,2000)==0);
 assert(singularity_gpu_level(5,7,1,500,1000)==6);
 assert(singularity_gpu_level(5,7,1,2100,2000)==6);
 assert(singularity_gpu_level(5,7,INT_MAX,0,2000)==7);
 assert(singularity_gpu_level(5,7,INT_MIN,0,2000)==0);
 assert(singularity_gpu_level(0,0,1,1900,2000)==0);
 assert(singularity_gpu_level(5,7,1,ULLONG_MAX,ULLONG_MAX)==3);
 puts("PASS: CPU demand headroom; GPU burst/hysteresis; bounds, idle and invalid samples");
}
