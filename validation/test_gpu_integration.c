#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "singularity_dvfs.h"
#define TAG ""
#define EINVAL 22
#define pr_err(...) ((void)0)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
struct devfreq_dev_status {unsigned long total_time,busy_time,current_frequency;void *private_data;};
struct devfreq;
struct profile {int max_state;unsigned long *freq_table;int (*get_dev_status)(void *,struct devfreq_dev_status *);};
struct devfreq {void *data;struct profile *profile;struct {void *parent;} dev;};
struct devfreq_msm_adreno_tz_data {struct {int64_t total_time,busy_time;} bin;int disable_busy_time_burst,ctxt_aware_enable;};
static struct devfreq_dev_status sample={2000,1900,500,0};
static int firmware_error=0;
static int get_status(void *parent,struct devfreq_dev_status *s) {*s=sample;return 0;}
static void compute_work_load(struct devfreq_dev_status *s,struct devfreq_msm_adreno_tz_data *p,struct devfreq *d){}
static unsigned int dsi_panel_get_refresh_rate(void){return 60;}
static int __secure_tz_update_entry3(unsigned int *data,unsigned int size,int *val,unsigned int valsize,struct devfreq_msm_adreno_tz_data *p){*val=1;return firmware_error;}
#include "gpu_actual.inc"
int main(void){
 unsigned long table[]={900,800,700,600,500,400},freq;
 struct profile profile={6,table,get_status};
 struct devfreq_msm_adreno_tz_data priv={0};struct devfreq d={&priv,&profile,{0}};
 assert(tz_get_target_freq(&d,&freq)==0);assert(freq==700);
 assert(priv.bin.total_time==0&&priv.bin.busy_time==0);
 priv=(struct devfreq_msm_adreno_tz_data){0};sample.total_time=1000;sample.busy_time=900;
 assert(tz_get_target_freq(&d,&freq)==0&&freq==500);
 priv=(struct devfreq_msm_adreno_tz_data){0};sample.total_time=2000;sample.busy_time=1900;firmware_error=-5;
 assert(tz_get_target_freq(&d,&freq)==-5&&freq==500);
 assert(priv.bin.total_time==0&&priv.bin.busy_time==0);
 priv=(struct devfreq_msm_adreno_tz_data){0};priv.disable_busy_time_burst=1;firmware_error=0;
 assert(tz_get_target_freq(&d,&freq)==0&&freq==400);
 puts("PASS: real Adreno TZ callback: 2 ms burst, short window, TZ errors, disabled burst");
}
