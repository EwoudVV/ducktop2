#ifndef DUCKTOP2_BOARD_PROFILE_H
#define DUCKTOP2_BOARD_PROFILE_H

/* Qualification switches stay false until the named electrical/assembly
 * evidence is released. These are build inputs, never runtime host grants. */
#ifndef DUCKTOP2_PACK_QUALIFIED
#define DUCKTOP2_PACK_QUALIFIED 0
#endif
#ifndef DUCKTOP2_GAUGE_QUALIFIED
#define DUCKTOP2_GAUGE_QUALIFIED 0
#endif
#ifndef DUCKTOP2_CHARGING_QUALIFIED
#define DUCKTOP2_CHARGING_QUALIFIED 0
#endif
#ifndef DUCKTOP2_EXTERNAL_BOOT_QUALIFIED
#define DUCKTOP2_EXTERNAL_BOOT_QUALIFIED 0
#endif
#ifndef DUCKTOP2_EXTERNAL_BOOT_BUDGET_MW
#define DUCKTOP2_EXTERNAL_BOOT_BUDGET_MW 0u
#endif
#ifndef DUCKTOP2_PACK_BRIDGE_QUALIFIED
#define DUCKTOP2_PACK_BRIDGE_QUALIFIED 0
#endif
#ifndef DUCKTOP2_PACK_BOOT_QUALIFIED
#define DUCKTOP2_PACK_BOOT_QUALIFIED 0
#endif
#ifndef DUCKTOP2_PACK_BOOT_BUDGET_MW
#define DUCKTOP2_PACK_BOOT_BUDGET_MW 0u
#endif
#ifndef DUCKTOP2_AUX_QUALIFIED_CURRENT_MA
#define DUCKTOP2_AUX_QUALIFIED_CURRENT_MA 500u
#endif
#ifndef DUCKTOP2_PD_ALLOW_20V
#define DUCKTOP2_PD_ALLOW_20V 1
#endif
#ifndef DUCKTOP2_IINDPM_CAP_MA
#define DUCKTOP2_IINDPM_CAP_MA 4400u
#endif
#ifndef DUCKTOP2_PD_IINDPM_MARGIN_MA
#define DUCKTOP2_PD_IINDPM_MARGIN_MA 250u
#endif
#ifndef DUCKTOP2_PACK_USABLE_CURRENT_MA
#define DUCKTOP2_PACK_USABLE_CURRENT_MA 0u
#endif
#ifndef DUCKTOP2_PACK_CHARGE_CURRENT_MA
#define DUCKTOP2_PACK_CHARGE_CURRENT_MA 0u
#endif
#ifndef DUCKTOP2_PACK_CHARGE_VOLTAGE_MV
#define DUCKTOP2_PACK_CHARGE_VOLTAGE_MV 0u
#endif
/* These are current-transfer qualification envelopes, not guarantees at
 * every operating point. The offsets are in nominal-shunt current units.
 * Qualification includes Kelvin routing, IC error, temperature and drift. */
#ifndef DUCKTOP2_CHARGER_CURRENT_QUALIFIED
#define DUCKTOP2_CHARGER_CURRENT_QUALIFIED 0u
#endif
#ifndef DUCKTOP2_ADAPTER_SENSE_MIN_PERMILLE
#define DUCKTOP2_ADAPTER_SENSE_MIN_PERMILLE 919u
#endif
#ifndef DUCKTOP2_ADAPTER_SENSE_MAX_PERMILLE
#define DUCKTOP2_ADAPTER_SENSE_MAX_PERMILLE 1081u
#endif
#ifndef DUCKTOP2_ADAPTER_GAIN_MIN_PERMILLE
#define DUCKTOP2_ADAPTER_GAIN_MIN_PERMILLE 975u
#endif
#ifndef DUCKTOP2_ADAPTER_GAIN_MAX_PERMILLE
#define DUCKTOP2_ADAPTER_GAIN_MAX_PERMILLE 1025u
#endif
#ifndef DUCKTOP2_ADAPTER_OFFSET_MA
#define DUCKTOP2_ADAPTER_OFFSET_MA 50u
#endif
#ifndef DUCKTOP2_CHARGE_SENSE_MIN_PERMILLE
#define DUCKTOP2_CHARGE_SENSE_MIN_PERMILLE 869u
#endif
#ifndef DUCKTOP2_CHARGE_GAIN_MAX_PERMILLE
#define DUCKTOP2_CHARGE_GAIN_MAX_PERMILLE 1020u
#endif
#ifndef DUCKTOP2_CHARGE_OFFSET_MA
#define DUCKTOP2_CHARGE_OFFSET_MA 60u
#endif
/* Design allocations, not measured qualification. Raw USB/AUX standby bypasses the input shunt. VSYS-fed standby passes
 * through the battery shunt; reserve its load within the total pack budget. */
#ifndef DUCKTOP2_RAW_AON_RESERVE_MW
#define DUCKTOP2_RAW_AON_RESERVE_MW 6500u
#endif
#ifndef DUCKTOP2_PACK_AON_RESERVE_MA
#define DUCKTOP2_PACK_AON_RESERVE_MA 800u
#endif
#ifndef DUCKTOP2_STANDBY_RESERVE_MW
#define DUCKTOP2_STANDBY_RESERVE_MW 1000u
#endif
#ifndef DUCKTOP2_MU_THROTTLE_QUALIFIED
#define DUCKTOP2_MU_THROTTLE_QUALIFIED 0
#endif
/* Other non-Mu/display demand includes every uncontrolled load.
 * The target separately adds its complete controlled USB5 reservation. */
#ifndef DUCKTOP2_AUX_WORST_CASE_MW
#define DUCKTOP2_AUX_WORST_CASE_MW 0u
#endif
#ifndef DUCKTOP2_AUX_LOADS_QUALIFIED
#define DUCKTOP2_AUX_LOADS_QUALIFIED 0
#endif
/* USB5 qualification includes the complete loom, ripple, hot branch losses,
 * inrush, converter efficiency, sense layout and all-mode VCONN envelope.
 * AUX_WORST_CASE_MW covers other auxiliary loads; USB reservations are added.
 * No host request can turn a qualification switch on. */
#ifndef DUCKTOP2_USB_POWER_QUALIFIED
#define DUCKTOP2_USB_POWER_QUALIFIED 0
#endif
#ifndef DUCKTOP2_USB_ADMISSION_MA
#define DUCKTOP2_USB_ADMISSION_MA 5500u
#endif
#ifndef DUCKTOP2_USB_RIGHT_HARNESS_MA
#define DUCKTOP2_USB_RIGHT_HARNESS_MA 0u
#endif
#ifndef DUCKTOP2_USB_EFFICIENCY_PERCENT
#define DUCKTOP2_USB_EFFICIENCY_PERCENT 0u
#endif
/* ISL9241 ADC resolution is not a guaranteed absolute accuracy. These
 * bounds need assembled calibration across temperature, operating state,
 * life and the full measurement-to-shutoff interval before USB admission. */
#ifndef DUCKTOP2_VSYS_SENSE_QUALIFIED
#define DUCKTOP2_VSYS_SENSE_QUALIFIED 0
#endif
#ifndef DUCKTOP2_VSYS_MAX_OVERESTIMATE_MV
#define DUCKTOP2_VSYS_MAX_OVERESTIMATE_MV 0u
#endif
#ifndef DUCKTOP2_VSYS_MAX_FALL_MV
#define DUCKTOP2_VSYS_MAX_FALL_MV 0u
#endif
#ifndef DUCKTOP2_USB_PD_INRUSH_MA
#define DUCKTOP2_USB_PD_INRUSH_MA 0u
#endif
#ifndef DUCKTOP2_USB_BRANCH_INRUSH_MA
#define DUCKTOP2_USB_BRANCH_INRUSH_MA 0u
#endif
#if DUCKTOP2_USB_POWER_QUALIFIED && (!DUCKTOP2_CHARGER_CURRENT_QUALIFIED || !DUCKTOP2_AUX_LOADS_QUALIFIED || !DUCKTOP2_USB_RIGHT_HARNESS_MA || DUCKTOP2_USB_EFFICIENCY_PERCENT < 80 || !DUCKTOP2_VSYS_SENSE_QUALIFIED || !DUCKTOP2_VSYS_MAX_OVERESTIMATE_MV || !DUCKTOP2_VSYS_MAX_FALL_MV || !DUCKTOP2_USB_PD_INRUSH_MA || !DUCKTOP2_USB_BRANCH_INRUSH_MA)
#error "USB power requires qualified charger current, harness, VSYS measurement/fall, efficiency, inrush and other load bounds"
#endif
#if DUCKTOP2_USB_ADMISSION_MA > 5500 || DUCKTOP2_USB_RIGHT_HARNESS_MA > 2500 || DUCKTOP2_USB_EFFICIENCY_PERCENT > 100
#error "USB profile exceeds the conservative design envelope"
#endif
#if DUCKTOP2_IINDPM_CAP_MA < 200 || DUCKTOP2_IINDPM_CAP_MA > 4400 || DUCKTOP2_IINDPM_CAP_MA % 4
#error "ISL9241 input limit must be 200..4400 mA in 4 mA steps"
#endif
#if (DUCKTOP2_PACK_BRIDGE_QUALIFIED || DUCKTOP2_PACK_BOOT_QUALIFIED) && (DUCKTOP2_PACK_USABLE_CURRENT_MA <= DUCKTOP2_PACK_AON_RESERVE_MA || DUCKTOP2_PACK_USABLE_CURRENT_MA > 3000)
#error "pack load budget must reserve AON current and stay below the BMS low trip corner"
#endif
#if DUCKTOP2_PACK_BRIDGE_QUALIFIED && (!DUCKTOP2_MU_THROTTLE_QUALIFIED || !DUCKTOP2_PACK_QUALIFIED || !DUCKTOP2_GAUGE_QUALIFIED || !DUCKTOP2_PACK_USABLE_CURRENT_MA || !DUCKTOP2_AUX_LOADS_QUALIFIED)
#error "pack bridge requires qualified pack, gauge and complete load envelope"
#endif
#if DUCKTOP2_PACK_BOOT_QUALIFIED && (!DUCKTOP2_MU_THROTTLE_QUALIFIED || !DUCKTOP2_PACK_QUALIFIED || !DUCKTOP2_GAUGE_QUALIFIED || !DUCKTOP2_PACK_BOOT_BUDGET_MW || !DUCKTOP2_PACK_USABLE_CURRENT_MA || !DUCKTOP2_AUX_LOADS_QUALIFIED)
#error "pack boot requires a complete qualified source/load envelope"
#endif
#if DUCKTOP2_EXTERNAL_BOOT_QUALIFIED && (!DUCKTOP2_CHARGER_CURRENT_QUALIFIED || !DUCKTOP2_MU_THROTTLE_QUALIFIED || !DUCKTOP2_EXTERNAL_BOOT_BUDGET_MW || !DUCKTOP2_AUX_LOADS_QUALIFIED)
#error "external boot requires qualified charger current and a complete source/load envelope"
#endif
#if DUCKTOP2_CHARGING_QUALIFIED && (!DUCKTOP2_CHARGER_CURRENT_QUALIFIED || !DUCKTOP2_PACK_QUALIFIED || !DUCKTOP2_GAUGE_QUALIFIED || DUCKTOP2_PACK_CHARGE_CURRENT_MA < 148 || DUCKTOP2_PACK_CHARGE_CURRENT_MA > 3000 || DUCKTOP2_PACK_CHARGE_VOLTAGE_MV < 10200 || DUCKTOP2_PACK_CHARGE_VOLTAGE_MV > 12528 || DUCKTOP2_PACK_CHARGE_VOLTAGE_MV % 8)
#error "charging requires qualified current transfer and 3S current/voltage limits"
#endif
#if DUCKTOP2_ADAPTER_SENSE_MIN_PERMILLE < 1 || DUCKTOP2_ADAPTER_SENSE_MIN_PERMILLE > 1000 || DUCKTOP2_ADAPTER_SENSE_MAX_PERMILLE < 1000 || DUCKTOP2_ADAPTER_GAIN_MIN_PERMILLE < 1 || DUCKTOP2_ADAPTER_GAIN_MIN_PERMILLE > 1000 || DUCKTOP2_ADAPTER_GAIN_MAX_PERMILLE < 1000 || DUCKTOP2_CHARGE_SENSE_MIN_PERMILLE < 1 || DUCKTOP2_CHARGE_SENSE_MIN_PERMILLE > 1000 || DUCKTOP2_CHARGE_GAIN_MAX_PERMILLE < 1000
#error "invalid charger current-transfer bounds"
#endif
#endif
