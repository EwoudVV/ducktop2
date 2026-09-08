#ifndef DUCKTOP2_SSD1306_H
#define DUCKTOP2_SSD1306_H
#include "ducktop2/ec/ec_telemetry.h"
#include <stdbool.h>
#include <stdint.h>
void ssd1306_status_step(const ec_telemetry_snapshot_t *telemetry, uint16_t flags,
                         uint16_t fault, uint16_t rpm, uint8_t duty,
                         int16_t skin_dc, int16_t mu_dc, uint32_t now_ms);
void ssd1306_render_line(const char *text, uint8_t page[128]);
#endif
