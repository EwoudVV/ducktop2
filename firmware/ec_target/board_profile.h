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
#define DUCKTOP2_IINDPM_CAP_MA 2500u
#endif
#ifndef DUCKTOP2_PD_IINDPM_MARGIN_MA
#define DUCKTOP2_PD_IINDPM_MARGIN_MA 500u
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
#ifndef DUCKTOP2_USB_PD_INRUSH_MA
#define DUCKTOP2_USB_PD_INRUSH_MA 0u
#endif
#ifndef DUCKTOP2_USB_BRANCH_INRUSH_MA
#define DUCKTOP2_USB_BRANCH_INRUSH_MA 0u
#endif
#if DUCKTOP2_USB_POWER_QUALIFIED && (!DUCKTOP2_AUX_LOADS_QUALIFIED || !DUCKTOP2_USB_RIGHT_HARNESS_MA || !DUCKTOP2_USB_EFFICIENCY_PERCENT || !DUCKTOP2_USB_PD_INRUSH_MA || !DUCKTOP2_USB_BRANCH_INRUSH_MA)
#error "USB power requires qualified harness, efficiency, inrush and other load bounds"
#endif
#if DUCKTOP2_USB_ADMISSION_MA > 5500 || DUCKTOP2_USB_RIGHT_HARNESS_MA > 2500 || DUCKTOP2_USB_EFFICIENCY_PERCENT > 100
#error "USB profile exceeds the conservative design envelope"
#endif
#if DUCKTOP2_IINDPM_CAP_MA < 100 || DUCKTOP2_IINDPM_CAP_MA > 3300 || DUCKTOP2_IINDPM_CAP_MA % 10
#error "IINDPM must be a supported 10 mA step"
#endif
#if DUCKTOP2_PACK_BRIDGE_QUALIFIED && (!DUCKTOP2_PACK_QUALIFIED || !DUCKTOP2_GAUGE_QUALIFIED || !DUCKTOP2_PACK_USABLE_CURRENT_MA || !DUCKTOP2_AUX_LOADS_QUALIFIED)
#error "pack bridge requires qualified pack, gauge and complete load envelope"
#endif
#if DUCKTOP2_PACK_BOOT_QUALIFIED && (!DUCKTOP2_PACK_QUALIFIED || !DUCKTOP2_GAUGE_QUALIFIED || !DUCKTOP2_PACK_BOOT_BUDGET_MW || !DUCKTOP2_PACK_USABLE_CURRENT_MA || !DUCKTOP2_AUX_LOADS_QUALIFIED)
#error "pack boot requires a complete qualified source/load envelope"
#endif
#if DUCKTOP2_EXTERNAL_BOOT_QUALIFIED && (!DUCKTOP2_EXTERNAL_BOOT_BUDGET_MW || !DUCKTOP2_AUX_LOADS_QUALIFIED)
#error "external boot requires a complete qualified source/load envelope"
#endif
#if DUCKTOP2_CHARGING_QUALIFIED && (!DUCKTOP2_PACK_QUALIFIED || DUCKTOP2_PACK_CHARGE_CURRENT_MA < 50 || DUCKTOP2_PACK_CHARGE_CURRENT_MA > 5000 || DUCKTOP2_PACK_CHARGE_CURRENT_MA % 10 || DUCKTOP2_PACK_CHARGE_VOLTAGE_MV < 9000 || DUCKTOP2_PACK_CHARGE_VOLTAGE_MV > 12600 || DUCKTOP2_PACK_CHARGE_VOLTAGE_MV % 10)
#error "charging requires qualified 3S current and voltage limits"
#endif
#endif
