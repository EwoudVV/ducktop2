#ifndef DUCKTOP2_EC_KEYMAP_H
#define DUCKTOP2_EC_KEYMAP_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Ducktop2 keyboard keymap and Fn-layer translation.
 *
 * The fabricated MX ULP keyboard daughterboard (see
 * gen/generate_keyboard_daughterboard_sheet.py) is a 5x14 switch matrix with
 * one diode per key (no firmware ghost-mask needed).  The EC target scans the
 * matrix into a row-major bitmask and this pure module translates the current
 * matrix state into a USB HID boot-protocol keyboard report plus a small
 * consumer-control report, applying the user-confirmed Fn layer:
 *
 *   Fn + 1..0          -> F1..F10
 *   Fn + Esc           -> `~ (grave)
 *   Fn + Bksp          -> Delete        (standard 65% laptop default)
 *   Fn + Up            -> Brightness Up
 *   Fn + Down          -> Brightness Down
 *   Fn + Left          -> Volume Down
 *   Fn + Right         -> Volume Up
 *
 * Keys not listed in the Fn layer pass through to their base mapping while Fn
 * is held (normal-laptop behaviour: Fn only changes the listed keys).  The Fn
 * key itself is consumed as a layer selector and is never reported.  Modifier
 * keys (Ctrl/Shift/Alt/Super) set the HID modifier byte; held consumer usages
 * stay asserted so the host applies its own auto-repeat rate.
 *
 * This module is pure C with no hardware dependence so it runs in the host test
 * harness alongside ec_policy/ec_commit/ec_telemetry.
 */

#define EC_KEYMAP_ROWS 5u
#define EC_KEYMAP_COLS 14u

/* USB HID keyboard usage IDs (HID Usage Tables 1.12, page 7). */
#define EC_HID_KEY_NONE 0x00u
#define EC_HID_KEY_A 0x04u
#define EC_HID_KEY_B 0x05u
#define EC_HID_KEY_C 0x06u
#define EC_HID_KEY_D 0x07u
#define EC_HID_KEY_E 0x08u
#define EC_HID_KEY_F 0x09u
#define EC_HID_KEY_G 0x0Au
#define EC_HID_KEY_H 0x0Bu
#define EC_HID_KEY_I 0x0Cu
#define EC_HID_KEY_J 0x0Du
#define EC_HID_KEY_K 0x0Eu
#define EC_HID_KEY_L 0x0Fu
#define EC_HID_KEY_M 0x10u
#define EC_HID_KEY_N 0x11u
#define EC_HID_KEY_O 0x12u
#define EC_HID_KEY_P 0x13u
#define EC_HID_KEY_Q 0x14u
#define EC_HID_KEY_R 0x15u
#define EC_HID_KEY_S 0x16u
#define EC_HID_KEY_T 0x17u
#define EC_HID_KEY_U 0x18u
#define EC_HID_KEY_V 0x19u
#define EC_HID_KEY_W 0x1Au
#define EC_HID_KEY_X 0x1Bu
#define EC_HID_KEY_Y 0x1Cu
#define EC_HID_KEY_Z 0x1Du
#define EC_HID_KEY_1 0x1Eu
#define EC_HID_KEY_2 0x1Fu
#define EC_HID_KEY_3 0x20u
#define EC_HID_KEY_4 0x21u
#define EC_HID_KEY_5 0x22u
#define EC_HID_KEY_6 0x23u
#define EC_HID_KEY_7 0x24u
#define EC_HID_KEY_8 0x25u
#define EC_HID_KEY_9 0x26u
#define EC_HID_KEY_0 0x27u
#define EC_HID_KEY_ENTER 0x28u
#define EC_HID_KEY_ESC 0x29u
#define EC_HID_KEY_BKSP 0x2Au
#define EC_HID_KEY_TAB 0x2Bu
#define EC_HID_KEY_SPACE 0x2Cu
#define EC_HID_KEY_MINUS 0x2Du
#define EC_HID_KEY_EQUAL 0x2Eu
#define EC_HID_KEY_LBRACKET 0x2Fu
#define EC_HID_KEY_RBRACKET 0x30u
#define EC_HID_KEY_BSLASH 0x31u
#define EC_HID_KEY_SEMICOLON 0x33u
#define EC_HID_KEY_QUOTE 0x34u
#define EC_HID_KEY_GRAVE 0x35u
#define EC_HID_KEY_COMMA 0x36u
#define EC_HID_KEY_PERIOD 0x37u
#define EC_HID_KEY_SLASH 0x38u
#define EC_HID_KEY_CAPS 0x39u
#define EC_HID_KEY_F1 0x3Au
#define EC_HID_KEY_F2 0x3Bu
#define EC_HID_KEY_F3 0x3Cu
#define EC_HID_KEY_F4 0x3Du
#define EC_HID_KEY_F5 0x3Eu
#define EC_HID_KEY_F6 0x3Fu
#define EC_HID_KEY_F7 0x40u
#define EC_HID_KEY_F8 0x41u
#define EC_HID_KEY_F9 0x42u
#define EC_HID_KEY_F10 0x43u
#define EC_HID_KEY_DELETE 0x4Cu
#define EC_HID_KEY_LEFT 0x50u
#define EC_HID_KEY_DOWN 0x51u
#define EC_HID_KEY_UP 0x52u
#define EC_HID_KEY_RIGHT 0x4Fu
#define EC_HID_KEY_APPLICATION 0x65u
/* ErrorRollOver per USB HID 1.11 boot protocol. */
#define EC_HID_KEY_ERROR_ROLLOVER 0x01u

/* USB HID keyboard modifier bitmap (reported in the modifier byte). */
#define EC_HID_MOD_LCTRL  0x01u
#define EC_HID_MOD_LSHIFT 0x02u
#define EC_HID_MOD_RSHIFT 0x20u
#define EC_HID_MOD_LALT   0x04u
#define EC_HID_MOD_RALT   0x40u
#define EC_HID_MOD_LGUI   0x08u
/* Super maps to left GUI; a right-GUI modifier key is not present on this
 * fabricated board. */
#define EC_HID_MOD_RGUI 0x80u

/* USB HID Consumer Control usages (Usage Page 0x0C). */
#define EC_HID_CONSUMER_MUTE 0x00E2u
#define EC_HID_CONSUMER_BRIGHTNESS_UP 0x006Fu
#define EC_HID_CONSUMER_BRIGHTNESS_DOWN 0x0070u
#define EC_HID_CONSUMER_VOLUME_UP 0x00E9u
#define EC_HID_CONSUMER_VOLUME_DOWN 0x00EAu

/*
 * USB HID boot-protocol keyboard report: one modifier byte, one reserved
 * byte, and up to six simultaneously-pressed non-modifier keycodes.  This is
 * the universal normal-laptop interface and is what the EC will emit over USB.
 */
#define EC_HID_KEYBOARD_ROLLOVER 6u
typedef struct {
  uint8_t modifiers;
  uint8_t reserved;
  uint8_t keys[EC_HID_KEYBOARD_ROLLOVER];
} ec_hid_keyboard_report_t;

/*
 * Consumer-control report: up to four simultaneously-held consumer usages
 * (volume/brightness).  Held usages stay asserted so the host applies its own
 * auto-repeat ramp; no host-side key repeat needs to be reimplemented here.
 */
#define EC_HID_CONSUMER_MAX 4u
typedef struct {
  uint16_t usages[EC_HID_CONSUMER_MAX];
  uint8_t count;
} ec_hid_consumer_report_t;

/*
 * Matrix state: one uint16_t per row, bit i set means the key at (row, col i)
 * is currently pressed (post-debounce).  Direction-agnostic: the target may
 * drive rows and read columns or vice-versa, as long as it fills this array.
 */
typedef struct {
  uint16_t rows[EC_KEYMAP_ROWS];
} ec_keymap_matrix_t;

/* Build a row bitmask from a single column index (helper for tests/target). */
#define EC_KEYMAP_COL_BIT(col) ((uint16_t)(1u << (col)))

/* Translate the current matrix state into the two HID reports.  Both reports
 * are fully overwritten each call (call at the EC step rate, e.g. 50 Hz). */
void ec_keymap_process(const ec_keymap_matrix_t *matrix,
                       ec_hid_keyboard_report_t *keyboard,
                       ec_hid_consumer_report_t *consumer);

/* True if the Fn layer-selector key (row 4, col 1) is currently pressed. */
bool ec_keymap_fn_held(const ec_keymap_matrix_t *matrix);

#ifdef __cplusplus
}
#endif

#endif /* DUCKTOP2_EC_KEYMAP_H */