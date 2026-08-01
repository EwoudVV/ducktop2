#include "ducktop2/ec/ec_keymap.h"

#include <stddef.h>
#include <stdio.h>

static int failures;

#define CHECK(expression)                                                      \
  do {                                                                        \
    if (!(expression)) {                                                      \
      fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__, __LINE__,         \
              #expression);                                                   \
      ++failures;                                                             \
    }                                                                         \
  } while (0)

static void press(ec_keymap_matrix_t *m, uint8_t row, uint8_t col) {
  m->rows[row] |= EC_KEYMAP_COL_BIT(col);
}

static void clear_matrix(ec_keymap_matrix_t *m) {
  for (uint8_t i = 0u; i < EC_KEYMAP_ROWS; ++i) {
    m->rows[i] = 0u;
  }
}

/* Count occurrences of a keyboard usage in the 6KRO key slots. */
static uint8_t key_occurrences(const ec_hid_keyboard_report_t *kb,
                               uint8_t usage) {
  uint8_t n = 0u;
  for (uint8_t i = 0u; i < EC_HID_KEYBOARD_ROLLOVER; ++i) {
    if (kb->keys[i] == usage) {
      ++n;
    }
  }
  return n;
}

/* Count non-empty key slots. */
static uint8_t key_slot_count(const ec_hid_keyboard_report_t *kb) {
  uint8_t n = 0u;
  for (uint8_t i = 0u; i < EC_HID_KEYBOARD_ROLLOVER; ++i) {
    if (kb->keys[i] != EC_HID_KEY_NONE) {
      ++n;
    }
  }
  return n;
}

static bool consumer_has(const ec_hid_consumer_report_t *cons, uint16_t usage) {
  for (uint8_t i = 0u; i < cons->count; ++i) {
    if (cons->usages[i] == usage) {
      return true;
    }
  }
  return false;
}

static void process(const ec_keymap_matrix_t *m,
                    ec_hid_keyboard_report_t *kb,
                    ec_hid_consumer_report_t *cons) {
  ec_keymap_process(m, kb, cons);
}

static void test_empty_matrix_emits_nothing(void) {
  ec_keymap_matrix_t m = {{0}};
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(kb.modifiers == 0u);
  CHECK(kb.reserved == 0u);
  CHECK(key_slot_count(&kb) == 0u);
  CHECK(cons.count == 0u);
}

static void test_single_letter_emits_key(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 2u, 1u); /* A */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(kb.modifiers == 0u);
  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_A);
  CHECK(cons.count == 0u);
}

static void test_modifier_sets_modifier_byte(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 3u, 0u); /* left Shift */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(kb.modifiers == EC_HID_MOD_LSHIFT);
  CHECK(key_slot_count(&kb) == 0u);
  CHECK(cons.count == 0u);
}

static void test_shift_plus_letter_combines(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 3u, 0u);       /* left Shift */
  press(&m, 2u, 1u);       /* A */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(kb.modifiers == EC_HID_MOD_LSHIFT);
  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_A);
}

static void test_fn_key_is_not_reported(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u); /* Fn alone */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(kb.modifiers == 0u);
  CHECK(key_slot_count(&kb) == 0u);
  CHECK(cons.count == 0u);
  CHECK(ec_keymap_fn_held(&m));
}

static void test_number_row_without_fn_emits_digits(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 0u, 1u); /* 1 */
  press(&m, 0u, 10u); /* 0 */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(!ec_keymap_fn_held(&m));
  CHECK(key_slot_count(&kb) == 2u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_1) == 1u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_0) == 1u);
}

static void test_fn_plus_digits_emits_function_keys(void) {
  /* Fn + 1,2,3 -> F1,F2,F3 (held below 6KRO so no rollover error). */
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u); /* Fn */
  press(&m, 0u, 1u); /* 1 -> F1 */
  press(&m, 0u, 2u); /* 2 -> F2 */
  press(&m, 0u, 3u); /* 3 -> F3 */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(ec_keymap_fn_held(&m));
  CHECK(key_slot_count(&kb) == 3u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_F1) == 1u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_F2) == 1u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_F3) == 1u);
  /* No base-layer digits leak through while Fn is mapped. */
  CHECK(key_occurrences(&kb, EC_HID_KEY_1) == 0u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_ERROR_ROLLOVER) == 0u);
  CHECK(cons.count == 0u);
}

static void test_fn_plus_one_emits_f1_only(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u); /* Fn */
  press(&m, 0u, 1u); /* 1 -> F1 */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_F1);
  CHECK(kb.modifiers == 0u);
}

static void test_fn_plus_zero_emits_f10(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u);  /* Fn */
  press(&m, 0u, 10u); /* 0 -> F10 */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_F10);
}

static void test_fn_plus_esc_emits_grave(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u); /* Fn */
  press(&m, 0u, 0u); /* Esc -> `~ */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_GRAVE);
  CHECK(cons.count == 0u);
}

static void test_fn_plus_backspace_emits_delete(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u);  /* Fn */
  press(&m, 0u, 13u); /* Bksp -> Delete */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_DELETE);
}

static void test_fn_up_emits_brightness_up_consumer(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u);  /* Fn */
  press(&m, 3u, 11u); /* Up -> Brightness Up */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 0u);
  CHECK(cons.count == 1u);
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_BRIGHTNESS_UP));
}

static void test_fn_down_emits_brightness_down_consumer(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u);  /* Fn */
  press(&m, 4u, 10u); /* Down -> Brightness Down */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 0u);
  CHECK(cons.count == 1u);
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_BRIGHTNESS_DOWN));
}

static void test_fn_left_emits_volume_down_consumer(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u); /* Fn */
  press(&m, 4u, 9u); /* Left -> Volume Down */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(cons.count == 1u);
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_VOLUME_DOWN));
}

static void test_fn_right_emits_volume_up_consumer(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u);  /* Fn */
  press(&m, 4u, 11u); /* Right -> Volume Up */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(cons.count == 1u);
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_VOLUME_UP));
}

static void test_fn_passthrough_for_unmapped_keys(void) {
  /* Fn held but A has no Fn mapping: must pass through as plain A. */
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u); /* Fn */
  press(&m, 2u, 1u); /* A */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_A);
  CHECK(cons.count == 0u);
}

static void test_fn_plus_shift_plus_one_emits_shift_f1(void) {
  /* Modifier keys fall through the Fn layer and still combine. */
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u);  /* Fn */
  press(&m, 3u, 0u);  /* left Shift */
  press(&m, 0u, 1u);  /* 1 -> F1 */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(kb.modifiers == EC_HID_MOD_LSHIFT);
  CHECK(key_slot_count(&kb) == 1u);
  CHECK(kb.keys[0] == EC_HID_KEY_F1);
}

static void test_both_space_bars_emit_space(void) {
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 4u); /* left space */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);
  CHECK(kb.keys[0] == EC_HID_KEY_SPACE);

  clear_matrix(&m);
  press(&m, 4u, 5u); /* right space */
  process(&m, &kb, &cons);
  CHECK(kb.keys[0] == EC_HID_KEY_SPACE);
}

static void test_six_key_rollover(void) {
  /* A S D F G H (row 2, cols 1-6) - diode-isolated matrix supports n-key. */
  ec_keymap_matrix_t m = {{0}};
  for (uint8_t col = 1u; col <= 6u; ++col) {
    press(&m, 2u, col);
  }
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 6u);
  CHECK(kb.modifiers == 0u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_A) == 1u);
  CHECK(key_occurrences(&kb, EC_HID_KEY_H) == 1u);
  CHECK(cons.count == 0u);
}

static void test_seventh_key_reports_rollover_error(void) {
  /* A S D F G H J (row 2, cols 1-7) exceeds boot 6KRO. */
  ec_keymap_matrix_t m = {{0}};
  for (uint8_t col = 1u; col <= 7u; ++col) {
    press(&m, 2u, col);
  }
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  /* All six slots must read ErrorRollOver (0x01). */
  for (uint8_t i = 0u; i < EC_HID_KEYBOARD_ROLLOVER; ++i) {
    CHECK(kb.keys[i] == EC_HID_KEY_ERROR_ROLLOVER);
  }
}

static void test_all_four_consumer_keys_held(void) {
  /* Fn + Up + Down + Left + Right: all four consumer mappings active. */
  ec_keymap_matrix_t m = {{0}};
  press(&m, 4u, 1u);  /* Fn */
  press(&m, 3u, 11u); /* Up    -> Brightness Up */
  press(&m, 4u, 10u); /* Down  -> Brightness Down */
  press(&m, 4u, 9u);  /* Left  -> Volume Down */
  press(&m, 4u, 11u); /* Right -> Volume Up */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);

  CHECK(key_slot_count(&kb) == 0u);
  CHECK(cons.count == EC_HID_CONSUMER_MAX);
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_BRIGHTNESS_UP));
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_BRIGHTNESS_DOWN));
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_VOLUME_UP));
  CHECK(consumer_has(&cons, EC_HID_CONSUMER_VOLUME_DOWN));
}

static void test_reset_between_calls(void) {
  /* Each call fully rewrites the reports; a previous report must not leak. */
  ec_keymap_matrix_t m = {{0}};
  press(&m, 2u, 1u); /* A */
  ec_hid_keyboard_report_t kb;
  ec_hid_consumer_report_t cons;
  process(&m, &kb, &cons);
  CHECK(kb.keys[0] == EC_HID_KEY_A);

  clear_matrix(&m);
  process(&m, &kb, &cons);
  CHECK(kb.modifiers == 0u);
  CHECK(key_slot_count(&kb) == 0u);
  CHECK(cons.count == 0u);
}

int main(void) {
  test_empty_matrix_emits_nothing();
  test_single_letter_emits_key();
  test_modifier_sets_modifier_byte();
  test_shift_plus_letter_combines();
  test_fn_key_is_not_reported();
  test_number_row_without_fn_emits_digits();
  test_fn_plus_digits_emits_function_keys();
  test_fn_plus_one_emits_f1_only();
  test_fn_plus_zero_emits_f10();
  test_fn_plus_esc_emits_grave();
  test_fn_plus_backspace_emits_delete();
  test_fn_up_emits_brightness_up_consumer();
  test_fn_down_emits_brightness_down_consumer();
  test_fn_left_emits_volume_down_consumer();
  test_fn_right_emits_volume_up_consumer();
  test_fn_passthrough_for_unmapped_keys();
  test_fn_plus_shift_plus_one_emits_shift_f1();
  test_both_space_bars_emit_space();
  test_six_key_rollover();
  test_seventh_key_reports_rollover_error();
  test_all_four_consumer_keys_held();
  test_reset_between_calls();

  if (failures != 0) {
    fprintf(stderr, "ec_keymap_tests: %d failure(s)\n", failures);
    return 1;
  }
  puts("ec_keymap_tests: PASS");
  return 0;
}