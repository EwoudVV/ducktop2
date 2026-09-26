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
    c.minimum_charge_budget_mw=1000u;
    c.path_good_timeout_ms=400u;
    c.normal_mu_edp_budget_mw=66000u;
    return c;
}
#endif
