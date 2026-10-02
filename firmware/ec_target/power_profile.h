#ifndef DUCKTOP2_POWER_PROFILE_H
#define DUCKTOP2_POWER_PROFILE_H
#include "board_profile.h"
#include "ducktop2/ec/ec_policy.h"

static inline ec_policy_config_t ec_target_power_config(void)
{
    ec_policy_config_t c=ec_policy_default_config();
    c.iindpm_cap_ma=DUCKTOP2_IINDPM_CAP_MA;
    c.iindpm_step_ma=4u;c.minimum_iindpm_ma=200u;
    c.pd_iindpm_margin_ma=DUCKTOP2_PD_IINDPM_MARGIN_MA;
    c.raw_aon_reserve_mw=DUCKTOP2_RAW_AON_RESERVE_MW;
    c.standby_reserve_mw=DUCKTOP2_STANDBY_RESERVE_MW;
    c.input_shunt_min_permille=DUCKTOP2_ADAPTER_SENSE_MIN_PERMILLE;
    c.input_shunt_max_permille=DUCKTOP2_ADAPTER_SENSE_MAX_PERMILLE;
    c.input_current_gain_min_permille=DUCKTOP2_ADAPTER_GAIN_MIN_PERMILLE;
    c.input_current_gain_max_permille=DUCKTOP2_ADAPTER_GAIN_MAX_PERMILLE;
    c.input_current_offset_ma=DUCKTOP2_ADAPTER_OFFSET_MA;
    c.minimum_charge_budget_mw=1850u;
    c.path_good_timeout_ms=400u;
    /* 5.5A rail allocation includes the fan and divider/current-limit corners. */
    c.normal_mu_edp_budget_mw=60000u;
    c.enforce_pack_current_limit=
        DUCKTOP2_PACK_HARDWARE_REVISION==DUCKTOP2_PACK_REV_GUARDED_8A;
    return c;
}
#endif
