from pathlib import Path
import re,subprocess
s=Path('kernel/drivers/power/supply/qcom/smb5-lib.c').read_text()
def fn(name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);e=b+1;depth=1
 while depth:
  depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
# Compile the real startup helpers; emulate register and regulator results.
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define CMD_APSD_REG 0x1341
#define APSD_RERUN_BIT 1
#define PR_MISC 0
#define EPROBE_DEFER 517
#define dev_warn(...) ((void)0)
#define smblib_dbg(...) ((void)0)
#define smblib_err(...) ((void)0)
union power_supply_propval {int intval;};
struct smb_charger {bool uusb_apsd_rerun_done;};
static int present=1,present_error,dpdm_error,write_error,writes,dpdm_calls;
static int smblib_get_prop_usb_present(struct smb_charger *c,union power_supply_propval *v){v->intval=present;return present_error;}
static int smblib_request_dpdm(struct smb_charger *c,bool en){dpdm_calls++;return dpdm_error;}
static int smblib_masked_write(struct smb_charger *c,int reg,int mask,int value){writes++;return write_error;}
'''
q=Path('kernel/drivers/power/supply/qcom/qpnp-smb5.c').read_text()
a=q.index('\t/* Retry cold-boot detection after the DPDM provider is ready. */')
b=q.index('\t/* Use ICL results from HW */',a)
probe='static int actual_probe_step(struct smb_charger *chg) { int rc = 0;\n'+q[a:b]+'return 0; }\n'
main=r'''
int main(void){
 struct smb_charger c={0};
 dpdm_error=-517;
 assert(smblib_rerun_apsd_if_required(&c)==-517);
 assert(!c.uusb_apsd_rerun_done && writes==0);
 dpdm_error=-5;assert(smblib_rerun_apsd_if_required(&c)==-5);assert(writes==0);
 dpdm_error=0;write_error=-5;
 assert(smblib_rerun_apsd_if_required(&c)==-5);assert(!c.uusb_apsd_rerun_done && writes==1);
 write_error=0;assert(smblib_rerun_apsd_if_required(&c)==0);assert(c.uusb_apsd_rerun_done && writes==2);
 c.uusb_apsd_rerun_done=false;present=0;dpdm_calls=0;writes=0;
 assert(smblib_rerun_apsd_if_required(&c)==0);assert(!c.uusb_apsd_rerun_done && !writes && !dpdm_calls);
 present_error=-5;assert(smblib_rerun_apsd_if_required(&c)==-5);assert(!writes && !dpdm_calls);
 present_error=0;present=1;dpdm_error=-517;write_error=0;writes=0;
 assert(actual_probe_step(&c)==-517);assert(writes==0);
 dpdm_error=-5;assert(actual_probe_step(&c)==0);assert(writes==0);
 puts("PASS real SMB5 startup helpers: DPDM defer/error, APSD write failure, success, no cable and presence error");
}
'''
Path('validation/charger_startup_actual.c').write_text(prefix+fn('smblib_rerun_apsd(struct')+'\n'+fn('smblib_rerun_apsd_if_required(')+probe+main)
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Wno-unused-parameter','-Werror','validation/charger_startup_actual.c','-o','validation/charger_startup_actual'],check=True)
subprocess.run(['validation/charger_startup_actual'],check=True)
