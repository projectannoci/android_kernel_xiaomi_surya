
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
int smblib_rerun_apsd(struct smb_charger *chg)
{
	int rc;

	smblib_dbg(chg, PR_MISC, "re-running APSD\n");

	rc = smblib_masked_write(chg, CMD_APSD_REG,
				APSD_RERUN_BIT, APSD_RERUN_BIT);
	if (rc < 0)
		smblib_err(chg, "Couldn't re-run APSD rc=%d\n", rc);

	return rc;
}
int smblib_rerun_apsd_if_required(struct smb_charger *chg)
{
	union power_supply_propval val;
	int rc;

	rc = smblib_get_prop_usb_present(chg, &val);
	if (rc < 0) {
		smblib_err(chg, "Couldn't get usb present rc = %d\n", rc);
		return rc;
	}

	if (!val.intval)
		return 0;

	rc = smblib_request_dpdm(chg, true);
	if (rc < 0) {
		smblib_err(chg, "Couldn't to enable DPDM rc=%d\n", rc);
		return rc;
	}

	rc = smblib_rerun_apsd(chg);
	if (rc < 0)
		return rc;

	chg->uusb_apsd_rerun_done = true;

	return 0;
}static int actual_probe_step(struct smb_charger *chg) { int rc = 0;
	/* Retry cold-boot detection after the DPDM provider is ready. */
	rc = smblib_rerun_apsd_if_required(chg);
	if (rc == -EPROBE_DEFER)
		return rc;
	if (rc < 0)
		dev_warn(chg->dev, "Initial APSD retry failed rc=%d\n", rc);

return 0; }

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
