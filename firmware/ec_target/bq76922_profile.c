#include "bq76922_profile.h"

/* Complete prototype register choices. Factory trim values below are nominal
 * template values; a unit image must preserve captured factory trims. Physical
 * current, cell, voltage, delay and thermal qualification is still disabled. */
static const bq76922_config_row_t prototype_rows[] = {
    {0x9236u, 1, {0x0du}}, /* REG1 Config */
    {0x9237u, 1, {0x00u}}, /* REG0 Config */
    {0x9239u, 1, {0x11u}}, /* Comm Type */
    {0x923au, 1, {0x10u}}, /* I2C Address */
    {0x92fau, 1, {0x02u}}, /* CFETOFF Pin Config */
    {0x92fbu, 1, {0x02u}}, /* DFETOFF Pin Config */
    {0x92fcu, 1, {0x8au}}, /* ALERT Pin Config */
    {0x92fdu, 1, {0x00u}}, /* TS1 Config */
    {0x92feu, 1, {0x00u}}, /* TS2 Config */
    {0x9303u, 1, {0x05u}}, /* DA Configuration */
    {0x9304u, 2, {0x13u, 0x00u}}, /* Vcell Mode */
    {0x926du, 2, {0x00u, 0x00u}}, /* Default Alarm Mask */
    {0x9343u, 2, {0x50u, 0x00u}}, /* Mfg Status Init */
    {0x9234u, 2, {0x82u, 0x28u}}, /* Power Config */
    {0x9261u, 1, {0xfcu}}, /* Enabled Protections A */
    {0x9262u, 1, {0x40u}}, /* Enabled Protections B */
    {0x9263u, 1, {0x60u}}, /* Enabled Protections C */
    {0x9265u, 1, {0x98u}}, /* CHG FET Protections A */
    {0x9266u, 1, {0x40u}}, /* CHG FET Protections B */
    {0x9267u, 1, {0x40u}}, /* CHG FET Protections C */
    {0x9269u, 1, {0xe4u}}, /* DSG FET Protections A */
    {0x926au, 1, {0x40u}}, /* DSG FET Protections B */
    {0x926bu, 1, {0x60u}}, /* DSG FET Protections C */
    {0x92c0u, 1, {0x00u}}, /* Enabled PF A */
    {0x92c1u, 1, {0x00u}}, /* Enabled PF B */
    {0x92c2u, 1, {0x07u}}, /* Enabled PF C */
    {0x92c3u, 1, {0x00u}}, /* Enabled PF D */
    {0x9308u, 1, {0x1du}}, /* FET Options */
    {0x9309u, 1, {0x01u}}, /* Chg Pump Control */
    {0x930eu, 1, {0x00u}}, /* Predischarge Timeout */
    {0x930fu, 1, {0x32u}}, /* Predischarge Stop Delta */
    {0x9275u, 1, {0x3cu}}, /* CUV Threshold */
    {0x9276u, 2, {0x01u, 0x00u}}, /* CUV Delay */
    {0x927bu, 1, {0x03u}}, /* CUV Recovery Hysteresis */
    {0x9278u, 1, {0x52u}}, /* COV Threshold */
    {0x9279u, 2, {0x01u, 0x00u}}, /* COV Delay */
    {0x927cu, 1, {0x03u}}, /* COV Recovery Hysteresis */
    {0x9280u, 1, {0x07u}}, /* OCC Threshold */
    {0x9281u, 1, {0x01u}}, /* OCC Delay */
    {0x9282u, 1, {0x0bu}}, /* OCD1 Threshold */
    {0x9283u, 1, {0x01u}}, /* OCD1 Delay */
    {0x9284u, 1, {0x0bu}}, /* OCD2 Threshold */
    {0x9285u, 1, {0x01u}}, /* OCD2 Delay */
    {0x9286u, 1, {0x02u}}, /* SCD Threshold */
    {0x9287u, 1, {0x01u}}, /* SCD Delay */
    {0x91a8u, 4, {0xf2u, 0x41u, 0x6fu, 0x40u}}, /* CC Gain */
    {0x91acu, 4, {0x6au, 0x1cu, 0x88u, 0x49u}}, /* Capacity Gain */
    {0x9180u, 2, {0x79u, 0x30u}}, /* Cell 1 Gain */
    {0x9182u, 2, {0x79u, 0x30u}}, /* Cell 2 Gain */
    {0x9188u, 2, {0x79u, 0x30u}}, /* Cell 5 Gain */
    {0x91b0u, 2, {0x00u, 0x00u}}, /* Vcell Offset */
    {0x930au, 2, {0x00u, 0x00u}}, /* Precharge Start Voltage */
    {0x930cu, 2, {0x00u, 0x00u}}, /* Precharge Stop Voltage */
    {0x925fu, 2, {0x02u, 0x00u}}, /* Protection Configuration */
    {0x9273u, 2, {0x32u, 0x00u}}, /* Body Diode Threshold */
    {0x926fu, 1, {0xfcu}}, /* SF Alert Mask A */
    {0x9270u, 1, {0x40u}}, /* SF Alert Mask B */
    {0x9271u, 1, {0x60u}}, /* SF Alert Mask C */
    {0x92c4u, 1, {0x00u}}, /* PF Alert Mask A */
    {0x92c5u, 1, {0x00u}}, /* PF Alert Mask B */
    {0x92c6u, 1, {0x07u}}, /* PF Alert Mask C */
    {0x92c7u, 1, {0x00u}}, /* PF Alert Mask D */
    {0x9335u, 1, {0x10u}}, /* Balancing Configuration */
    {0x928fu, 1, {0x01u}}, /* OCDL Latch Limit */
    {0x9290u, 1, {0xffu}}, /* OCDL Counter Dec Delay */
    {0x9291u, 1, {0xffu}}, /* OCDL Recovery Time */
    {0x9292u, 2, {0xffu, 0x7fu}}, /* OCDL Recovery Threshold */
    {0x9295u, 1, {0x01u}}, /* SCDL Latch Limit */
    {0x9296u, 1, {0xffu}}, /* SCDL Counter Dec Delay */
    {0x9297u, 1, {0xffu}}, /* SCDL Recovery Time */
    {0x9298u, 2, {0xffu, 0x7fu}}, /* SCDL Recovery Threshold */
    {0x9294u, 1, {0xffu}}, /* SCD Recovery Time */
    {0x928du, 2, {0xffu, 0x7fu}}, /* OCD Recovery Threshold */
    {0x9288u, 2, {0x00u, 0x80u}}, /* OCC Recovery Threshold */
    {0x92afu, 1, {0x03u}}, /* Recovery Time */
    {0x92b4u, 1, {0x00u}}, /* Load Detect Active Time */
    {0x92b5u, 1, {0xffu}}, /* Load Detect Retry Delay */
    {0x92b6u, 2, {0x01u, 0x00u}}, /* Load Detect Timeout */
    {0x923fu, 2, {0x00u, 0x00u}}, /* Shutdown Cell Voltage */
    {0x9241u, 2, {0x58u, 0x02u}}, /* Shutdown Stack Voltage */
    {0x9244u, 1, {0x55u}}, /* Shutdown Temperature */
    {0x9254u, 1, {0x00u}}, /* Auto Shutdown Time */
    {0x9315u, 2, {0x00u, 0x00u}}, /* Cell1 Interconnect */
    {0x9317u, 2, {0x00u, 0x00u}}, /* Cell2 Interconnect */
    {0x931du, 2, {0x00u, 0x00u}}, /* Cell5 Interconnect */
    {0x91d4u, 2, {0xffu, 0xffu}}, /* CUV Threshold Override disabled */
    {0x91d6u, 2, {0xffu, 0xffu}}, /* COV Threshold Override disabled */
    {0x92a3u, 1, {0x4bu}}, /* OTINT Threshold75C */
    {0x92a4u, 1, {0x00u}}, /* OTINT Delay0s */
    {0x92a5u, 1, {0x41u}}, /* OTINT Recovery65C */
};

const bq76922_profile_t ducktop2_bq76922_profile = {
    .rows = prototype_rows,
    .row_count = sizeof(prototype_rows) / sizeof(prototype_rows[0]),
    .complete = true,
    .qualified = false,
    .cell_voltage_qualified = false,
    .charge_voltage_qualified = false,
    .termination_qualified = false,
    .charge_voltage_mv = BQ76922_CHARGE_CV_MV,
    .charge_cell_max_mv = BQ76922_CHARGE_CELL_MAX_MV,
    .charge_spread_max_mv = BQ76922_CHARGE_SPREAD_MAX_MV,
    .cell_voltage_error_mv = BQ76922_CHARGE_CELL_ERROR_MAX_MV,
    .charge_max_rise_mv = 0,
    .discharge_cell_min_mv = 3100,
    .normal_charge_cell_min_mv = 3100,
    .cell_max_mv = 4200,
    .pack_min_mv = 9000,
    .current_gain_min_permille = 0,
    .current_offset_ma = 0,
    .current_lsb_ma = 1,
    .discharge_limit_ma = 8000,
    .charge_limit_ma = 3000,
    .dynamic_reserve_ma = 0,
    .sample_max_age_ms = 200,
    .config_max_age_ms = 10000
};
