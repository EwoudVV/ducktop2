#ifndef DUCKTOP2_KEYBOARD_RGB_H
#define DUCKTOP2_KEYBOARD_RGB_H
#include <stdbool.h>
#include <stdint.h>

/* Call these from the main loop, not from an interrupt handler. */
void keyboard_rgb_init(void);
bool keyboard_rgb_request(bool enable, uint32_t now_ms);
void keyboard_rgb_service(uint32_t now_ms);
bool keyboard_rgb_set_key(uint8_t index, uint8_t red, uint8_t green, uint8_t blue);
void keyboard_rgb_set_all(uint8_t red, uint8_t green, uint8_t blue);
void keyboard_rgb_set_brightness(uint8_t brightness);
bool keyboard_rgb_ready(void);
bool keyboard_rgb_faulted(void);
#endif
