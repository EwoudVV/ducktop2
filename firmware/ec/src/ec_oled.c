#include "ducktop2/ec/ec_oled.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void set_line(char *line, const char *text) {
  /* Always NUL-terminate within the fixed buffer; snprintf truncates safely. */
  snprintf(line, EC_OLED_LINE_CHARS, "%s", text);
}

static const char *source_name(ec_source_id_t s) {
  switch (s) {
    case EC_SOURCE_PACK: return "PACK";
    case EC_SOURCE_AUX:  return "AUX";
    case EC_SOURCE_PD1:  return "PD1";
    case EC_SOURCE_PD2:  return "PD2";
    default:             return "none";
  }
}

static const char *fault_name(ec_fault_t f) {
  switch (f) {
    case EC_FAULT_NONE:                       return "none";
    case EC_FAULT_WATCHDOG:                   return "WATCHDOG";
    case EC_FAULT_SOURCE_MISSING:             return "SRC_MISSING";
    case EC_FAULT_SOURCE_REPORTED:            return "SRC_REPOR";
    case EC_FAULT_INPUT_CURRENT_INVALID:      return "I_INVALID";
    case EC_FAULT_VALIDATION_TIMEOUT:         return "VAL_TMEOUT";
    case EC_FAULT_IINDPM_APPLY_TIMEOUT:       return "IINDPM_TMO";
    case EC_FAULT_IINDPM_MISMATCH:            return "IINDPM_MIS";
    case EC_FAULT_PATH_GOOD_STUCK_HIGH:       return "PG_STUCK";
    case EC_FAULT_PATH_GOOD_TIMEOUT:          return "PG_TMEOUT";
    case EC_FAULT_PATH_GOOD_LOST:             return "PG_LOST";
    case EC_FAULT_CHARGER:                    return "CHARGER";
    case EC_FAULT_THERMAL:                    return "THERMAL";
    case EC_FAULT_THERMAL_DATA_INVALID:       return "THM_DATA";
    case EC_FAULT_RESET_INTERLOCK:            return "RST_INTER";
    case EC_FAULT_SERVICE_BUS:                return "SVC_BUS";
    case EC_FAULT_POWER_POLICY:               return "PWR_POL";
    case EC_FAULT_POWER_POLICY_APPLY_TIMEOUT: return "PWR_TMEOUT";
    case EC_FAULT_PACK_TELEMETRY:             return "PACK_TLM";
    case EC_FAULT_VSYS_INVALID:              return "VSYS_INV";
    case EC_FAULT_MU_POWER_GOOD_STUCK_HIGH:   return "MU_PG_STK";
    case EC_FAULT_MU_POWER_GOOD_TIMEOUT:      return "MU_PG_TMO";
    case EC_FAULT_MU_POWER_GOOD_LOST:         return "MU_PG_LOST";
    default:                                  return "UNKNOWN";
  }
}

static void format_temp(char *buf, size_t n, ec_fan_temp_dc_t dc) {
  int whole = (int)dc / 10;
  int frac = (int)dc % 10;
  if (frac < 0) {
    frac = -frac;
  }
  snprintf(buf, n, "%d.%dC", whole, frac);
}

static void format_hhmm(char *buf, size_t n, uint32_t seconds) {
  uint32_t h = seconds / 3600u;
  uint32_t m = (seconds % 3600u) / 60u;
  if (h > 99u) {
    /* Over 99 hours: show a saturated label so the display never lies about
     * the remaining minutes of a >99h figure. */
    snprintf(buf, n, "99h+");
    return;
  }
  snprintf(buf, n, "%uh%um", h, m);
}

static bool flag_set(const ec_telemetry_snapshot_t *t, uint16_t bit) {
  return (t->valid_flags & bit) != 0u;
}

void ec_oled_inputs_init(ec_oled_inputs_t *inputs) {
  memset(inputs, 0, sizeof(*inputs));
  /* EC_SOURCE_NONE is 0xff (not 0), so memset to zero leaves active_source as
   * PACK; set it explicitly so the composer renders "SRC none" by default. */
  inputs->active_source = EC_SOURCE_NONE;
  inputs->telemetry.active_input = EC_TELEMETRY_INPUT_NONE;
}

void ec_oled_compose(ec_oled_pages_t *pages, const ec_oled_inputs_t *inputs) {
  memset(pages, 0, sizeof(*pages));
  char line[EC_OLED_LINE_CHARS];

  const ec_telemetry_snapshot_t *t = &inputs->telemetry;

  /* ---------------- Left screen: power & battery ---------------- */

  /* Line 0: source + qualified input voltage. */
  if (inputs->active_source == EC_SOURCE_NONE) {
    set_line(pages->left.lines[0], "SRC none");
  } else if (inputs->source_voltage_valid &&
             inputs->source_input_voltage_mv > 0u) {
    uint16_t v_whole = inputs->source_input_voltage_mv / 1000u;
    uint16_t v_frac = (inputs->source_input_voltage_mv % 1000u) / 100u;
    snprintf(line, sizeof(line), "SRC %s %u.%uV", source_name(inputs->active_source),
             v_whole, v_frac);
    set_line(pages->left.lines[0], line);
  } else {
    snprintf(line, sizeof(line), "SRC %s ----V", source_name(inputs->active_source));
    set_line(pages->left.lines[0], line);
  }

  /* Line 1: SOC + charge state.  State from current sign; charger_enable is
   * the tiebreaker at zero current. */
  const char *state;
  const bool discharging =
      flag_set(t, EC_TELEMETRY_VALID_PACK_CURRENT) && (t->pack_current_ma < 0);
  const bool charging_commanded =
      flag_set(t, EC_TELEMETRY_VALID_PACK_CURRENT) && (t->pack_current_ma > 0);
  if (charging_commanded) {
    state = "CHG";
  } else if (discharging) {
    state = "DISC";
  } else if (inputs->charger_enable) {
    state = "CHG";
  } else {
    state = "IDLE";
  }
  if (flag_set(t, EC_TELEMETRY_VALID_SOC)) {
    snprintf(line, sizeof(line), "BAT %u%% %s", t->soc_percent, state);
  } else {
    snprintf(line, sizeof(line), "BAT --%% %s", state);
  }
  set_line(pages->left.lines[1], line);

  /* Line 2: pack voltage. */
  if (flag_set(t, EC_TELEMETRY_VALID_PACK_VOLTAGE)) {
    uint16_t v_whole = t->pack_voltage_mv / 1000u;
    uint16_t v_frac = (t->pack_voltage_mv % 1000u) / 100u;
    snprintf(line, sizeof(line), "V %u.%uV", v_whole, v_frac);
  } else {
    set_line(line, "V ----V");
  }
  set_line(pages->left.lines[2], line);

  /* Line 3: pack current, signed. */
  if (flag_set(t, EC_TELEMETRY_VALID_PACK_CURRENT)) {
    snprintf(line, sizeof(line), "I %+dmA", t->pack_current_ma);
  } else {
    set_line(line, "I ----mA");
  }
  set_line(pages->left.lines[3], line);

  /* Line 4: charge/discharge power. */
  if (flag_set(t, EC_TELEMETRY_VALID_PACK_POWER)) {
    if (charging_commanded) {
      snprintf(line, sizeof(line), "P %lumW CHG",
               (unsigned long)t->charge_power_mw);
    } else if (discharging) {
      snprintf(line, sizeof(line), "P %lumW DISC",
               (unsigned long)t->discharge_power_mw);
    } else {
      snprintf(line, sizeof(line), "P %lumW IDLE",
               (unsigned long)t->charge_power_mw);
    }
  } else {
    set_line(line, "P ----mW");
  }
  set_line(pages->left.lines[4], line);

  /* Line 5: time to empty (discharging) or time to full (charging). */
  if (discharging && flag_set(t, EC_TELEMETRY_VALID_TIME_TO_EMPTY)) {
    format_hhmm(line, sizeof(line), t->time_to_empty_s);
    set_line(pages->left.lines[5], "TTE ");
    strncat(pages->left.lines[5], line,
            EC_OLED_LINE_CHARS - strlen(pages->left.lines[5]) - 1u);
  } else if ((charging_commanded || inputs->charger_enable) &&
             flag_set(t, EC_TELEMETRY_VALID_TIME_TO_FULL)) {
    format_hhmm(line, sizeof(line), t->time_to_full_s);
    set_line(pages->left.lines[5], "TTF ");
    strncat(pages->left.lines[5], line,
            EC_OLED_LINE_CHARS - strlen(pages->left.lines[5]) - 1u);
  } else {
    set_line(pages->left.lines[5], "T  --");
  }

  /* Line 6: remaining / full capacity. */
  if (flag_set(t, EC_TELEMETRY_VALID_REMAINING_CAPACITY) &&
      flag_set(t, EC_TELEMETRY_VALID_FULL_CAPACITY)) {
    snprintf(line, sizeof(line), "CAP %lu/%lumAh",
             (unsigned long)t->remaining_capacity_mah,
             (unsigned long)t->full_capacity_mah);
  } else {
    set_line(line, "CAP ----/----mAh");
  }
  set_line(pages->left.lines[6], line);

  /* Line 7: cycles + health. */
  {
    char cycles_part[10];
    char health_part[10];
    if (flag_set(t, EC_TELEMETRY_VALID_CYCLE_COUNT)) {
      snprintf(cycles_part, sizeof(cycles_part), "%u", t->cycle_count);
    } else {
      set_line(cycles_part, "--");
    }
    if (flag_set(t, EC_TELEMETRY_VALID_HEALTH)) {
      snprintf(health_part, sizeof(health_part), "%u%%", t->health_percent);
    } else {
      set_line(health_part, "--");
    }
    snprintf(line, sizeof(line), "CYC %s H %s", cycles_part, health_part);
  }
  set_line(pages->left.lines[7], line);

  /* ---------------- Right screen: thermal, fan, system ---------------- */

  /* Line 0: fan duty + state; thermal fault overrides to FAULT. */
  if (inputs->fan.thermal_fault) {
    set_line(pages->right.lines[0], "FAN 100% FAULT");
  } else if (inputs->fan.running) {
    snprintf(line, sizeof(line), "FAN %u%% RUN", inputs->fan.duty_pct);
    set_line(pages->right.lines[0], line);
  } else {
    set_line(pages->right.lines[0], "FAN 0% STOP");
  }

  /* Line 1: skin temperature. */
  if (inputs->temps_valid) {
    char tbuf[12];
    format_temp(tbuf, sizeof(tbuf), inputs->skin_dc);
    snprintf(line, sizeof(line), "TSKIN %s", tbuf);
  } else {
    set_line(line, "TSKIN ----C");
  }
  set_line(pages->right.lines[1], line);

  /* Line 2: Mu coldplate temperature. */
  if (inputs->temps_valid) {
    char tbuf[12];
    format_temp(tbuf, sizeof(tbuf), inputs->mu_coldplate_dc);
    snprintf(line, sizeof(line), "TMU  %s", tbuf);
  } else {
    set_line(line, "TMU  ----C");
  }
  set_line(pages->right.lines[2], line);

  /* Line 3: throttle status. */
  if (inputs->fan.throttle_imminent) {
    set_line(pages->right.lines[3], "THROTTLE WARN");
  } else {
    set_line(pages->right.lines[3], "THROTTLE ok");
  }

  /* Line 4: radio daughterboard (hosts GNSS + VHF/UHF). */
  if (!inputs->radio_db_present) {
    set_line(pages->right.lines[4], "RAD no DB");
  } else if (inputs->radio_db_fault) {
    set_line(pages->right.lines[4], "RAD DB FAULT");
  } else {
    set_line(pages->right.lines[4], "RAD DB OK");
  }

  /* Line 5: maker controller. */
  if (inputs->maker_online) {
    set_line(pages->right.lines[5], "MAKER online");
  } else {
    set_line(pages->right.lines[5], "MAKER offline");
  }

  /* Line 6: EC firmware version. */
  if (inputs->firmware_version != NULL && inputs->firmware_version[0] != '\0') {
    snprintf(line, sizeof(line), "EC %s", inputs->firmware_version);
  } else {
    set_line(line, "EC ----");
  }
  set_line(pages->right.lines[6], line);

  /* Line 7: EC fault state. */
  snprintf(line, sizeof(line), "FAULT %s", fault_name(inputs->ec_fault));
  set_line(pages->right.lines[7], line);
}