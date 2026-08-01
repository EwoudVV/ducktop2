#include "ducktop2/ec/ec_keymap.h"

/*
 * Internal action representation.  Each matrix cell resolves to one of:
 *  - ACT_MODIFIER: payload is an EC_HID_MOD_* bitmask added to the report
 *    modifier byte (Ctrl/Shift/Alt/Super).
 *  - ACT_KEY: payload is a USB HID keyboard usage (0x04..0x65).  The Fn
 *    selector key itself is stored as ACT_NONE so it is consumed and never
 *    reported.
 *  - ACT_CONSUMER: payload is a USB HID Consumer-page (0x0C) usage, emitted
 *    in the consumer-control report while held.
 *  - ACT_NONE: no key at this matrix position (board gap or the Fn key).
 */
typedef enum {
  ACT_NONE = 0,
  ACT_MODIFIER,
  ACT_KEY,
  ACT_CONSUMER
} action_type_t;

typedef struct {
  uint8_t type;
  uint16_t payload;
} action_t;

#define K(u)   { ACT_KEY, (uint16_t)(u) }
#define MOD(u) { ACT_MODIFIER, (uint16_t)(u) }
#define CON(u) { ACT_CONSUMER, (uint16_t)(u) }
#define NONE   { ACT_NONE, 0u }

/*
 * Base layer for the fabricated 5x14 MX ULP keyboard.  Coordinates match
 * gen/generate_keyboard_daughterboard_sheet.py KEY_ROWS exactly.  Empty board
 * positions and the Fn selector (row 4, col 1) are ACT_NONE.
 */
static const action_t base_layer[EC_KEYMAP_ROWS][EC_KEYMAP_COLS] = {
  /* Row 0: Esc 1..0 - = Bksp */
  { K(EC_HID_KEY_ESC), K(EC_HID_KEY_1), K(EC_HID_KEY_2), K(EC_HID_KEY_3),
    K(EC_HID_KEY_4), K(EC_HID_KEY_5), K(EC_HID_KEY_6), K(EC_HID_KEY_7),
    K(EC_HID_KEY_8), K(EC_HID_KEY_9), K(EC_HID_KEY_0), K(EC_HID_KEY_MINUS),
    K(EC_HID_KEY_EQUAL), K(EC_HID_KEY_BKSP) },
  /* Row 1: Tab Q..P [ ] \ */
  { K(EC_HID_KEY_TAB), K(EC_HID_KEY_Q), K(EC_HID_KEY_W), K(EC_HID_KEY_E),
    K(EC_HID_KEY_R), K(EC_HID_KEY_T), K(EC_HID_KEY_Y), K(EC_HID_KEY_U),
    K(EC_HID_KEY_I), K(EC_HID_KEY_O), K(EC_HID_KEY_P), K(EC_HID_KEY_LBRACKET),
    K(EC_HID_KEY_RBRACKET), K(EC_HID_KEY_BSLASH) },
  /* Row 2: Caps A..L ; ' Enter _ (col 13 is a board gap) */
  { K(EC_HID_KEY_CAPS), K(EC_HID_KEY_A), K(EC_HID_KEY_S), K(EC_HID_KEY_D),
    K(EC_HID_KEY_F), K(EC_HID_KEY_G), K(EC_HID_KEY_H), K(EC_HID_KEY_J),
    K(EC_HID_KEY_K), K(EC_HID_KEY_L), K(EC_HID_KEY_SEMICOLON),
    K(EC_HID_KEY_QUOTE), K(EC_HID_KEY_ENTER), NONE },
  /* Row 3: ShiftL Z..M , . / Up ShiftR _ (col 13 is a board gap) */
  { MOD(EC_HID_MOD_LSHIFT), K(EC_HID_KEY_Z), K(EC_HID_KEY_X), K(EC_HID_KEY_C),
    K(EC_HID_KEY_V), K(EC_HID_KEY_B), K(EC_HID_KEY_N), K(EC_HID_KEY_M),
    K(EC_HID_KEY_COMMA), K(EC_HID_KEY_PERIOD), K(EC_HID_KEY_SLASH),
    K(EC_HID_KEY_UP), MOD(EC_HID_MOD_RSHIFT), NONE },
  /* Row 4: Ctrl Fn Super AltL SpaceL SpaceR AltR Menu _ Left Down Right _ _ */
  { MOD(EC_HID_MOD_LCTRL), NONE, MOD(EC_HID_MOD_LGUI), MOD(EC_HID_MOD_LALT),
    K(EC_HID_KEY_SPACE), K(EC_HID_KEY_SPACE), MOD(EC_HID_MOD_RALT),
    K(EC_HID_KEY_APPLICATION), NONE, K(EC_HID_KEY_LEFT), K(EC_HID_KEY_DOWN),
    K(EC_HID_KEY_RIGHT), NONE, NONE },
};

/*
 * Fn layer.  Only the user-confirmed mappings are populated; every other
 * cell falls through to base_layer when Fn is held, so Fn+A is still A.
 */
static const action_t fn_layer[EC_KEYMAP_ROWS][EC_KEYMAP_COLS] = {
  /* Row 0: Esc=`~, 1..0=F1..F10, Bksp=Delete (65% default). */
  { K(EC_HID_KEY_GRAVE), K(EC_HID_KEY_F1), K(EC_HID_KEY_F2), K(EC_HID_KEY_F3),
    K(EC_HID_KEY_F4), K(EC_HID_KEY_F5), K(EC_HID_KEY_F6), K(EC_HID_KEY_F7),
    K(EC_HID_KEY_F8), K(EC_HID_KEY_F9), K(EC_HID_KEY_F10), NONE, NONE,
    K(EC_HID_KEY_DELETE) },
  /* Row 1: no Fn mappings (passthrough). */
  { NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE,
    NONE, NONE },
  /* Row 2: no Fn mappings (passthrough). */
  { NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE,
    NONE, NONE },
  /* Row 3: Up=Brightness Up. */
  { NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE,
    CON(EC_HID_CONSUMER_BRIGHTNESS_UP), NONE, NONE },
  /* Row 4: Left=Vol Down, Down=Brightness Down, Right=Vol Up. */
  { NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE,
    CON(EC_HID_CONSUMER_VOLUME_DOWN), CON(EC_HID_CONSUMER_BRIGHTNESS_DOWN),
    CON(EC_HID_CONSUMER_VOLUME_UP), NONE, NONE },
};

bool ec_keymap_fn_held(const ec_keymap_matrix_t *matrix) {
  return (matrix->rows[4] & EC_KEYMAP_COL_BIT(1)) != 0u;
}

void ec_keymap_process(const ec_keymap_matrix_t *matrix,
                       ec_hid_keyboard_report_t *keyboard,
                       ec_hid_consumer_report_t *consumer) {
  const bool fn_held = ec_keymap_fn_held(matrix);
  uint8_t key_count = 0u;
  bool overflow = false;

  keyboard->modifiers = 0u;
  keyboard->reserved = 0u;
  for (uint8_t i = 0u; i < EC_HID_KEYBOARD_ROLLOVER; ++i) {
    keyboard->keys[i] = EC_HID_KEY_NONE;
  }
  consumer->count = 0u;
  for (uint8_t i = 0u; i < EC_HID_CONSUMER_MAX; ++i) {
    consumer->usages[i] = 0u;
  }

  for (uint8_t row = 0u; row < EC_KEYMAP_ROWS; ++row) {
    const uint16_t row_state = matrix->rows[row];
    if (row_state == 0u) {
      continue;
    }
    for (uint8_t col = 0u; col < EC_KEYMAP_COLS; ++col) {
      if ((row_state & EC_KEYMAP_COL_BIT(col)) == 0u) {
        continue;
      }
      /* The Fn selector key selects the layer and is never reported. */
      if (row == 4u && col == 1u) {
        continue;
      }

      action_t action = fn_held ? fn_layer[row][col] : base_layer[row][col];
      /* Fn mappings that are ACT_NONE pass through to the base mapping. */
      if (action.type == ACT_NONE && fn_held) {
        action = base_layer[row][col];
      }
      if (action.type == ACT_NONE) {
        continue;
      }

      switch (action.type) {
        case ACT_MODIFIER:
          keyboard->modifiers |= (uint8_t)action.payload;
          break;
        case ACT_KEY:
          if (key_count < EC_HID_KEYBOARD_ROLLOVER) {
            keyboard->keys[key_count] = (uint8_t)action.payload;
            ++key_count;
          } else {
            overflow = true;
          }
          break;
        case ACT_CONSUMER:
          if (consumer->count < EC_HID_CONSUMER_MAX) {
            consumer->usages[consumer->count] = action.payload;
            ++consumer->count;
          }
          break;
        case ACT_NONE:
        default:
          break;
      }
    }
  }

  /* USB HID boot protocol: report ErrorRollOver when more than six
   * non-modifier keys are held, so the host drops the phantom set instead of
   * emitting a random key.  The keyboard has per-key diodes, so real n-key
   * rollover is available once the interface moves past boot 6KRO. */
  if (overflow) {
    for (uint8_t i = 0u; i < EC_HID_KEYBOARD_ROLLOVER; ++i) {
      keyboard->keys[i] = EC_HID_KEY_ERROR_ROLLOVER;
    }
  }
}