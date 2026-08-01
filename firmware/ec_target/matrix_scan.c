#include "matrix_scan.h"
#include "stm32f4xx.h"

#include <stddef.h> /* NULL (matrix_config_valid port-null check) */

/*
 * Keyboard matrix hardware scan (STM32F407VGT6, LQFP100).
 *
 * Derived port/pin table (cross-checked three ways: the EC MCU sheet
 * gen/generate_ec_mcu_sheet.py assigns the package pins, the pin review
 * gen/generate_pin_review_table.py lines 511-516 repeats them, and the
 * STM32F407VGTx.kicad_sym symbol resolves package pin -> port/pin):
 *
 *     KB_ROW0 = PE0 (pkg 97)   KB_COL0  = PD0  (pkg 81)   KB_COL8  = PD8  (pkg 55)
 *     KB_ROW1 = PE1 (pkg 98)   KB_COL1  = PD1  (pkg 82)   KB_COL9  = PD9  (pkg 56)
 *     KB_ROW2 = PE2 (pkg 1)    KB_COL2  = PD2  (pkg 83)   KB_COL10 = PD10 (pkg 57)
 *     KB_ROW3 = PE3 (pkg 2)    KB_COL3  = PD3  (pkg 84)   KB_COL11 = PD11 (pkg 58)
 *     KB_ROW4 = PE4 (pkg 3)    KB_COL4  = PD4  (pkg 85)   KB_COL12 = PD12 (pkg 59)
 *                              KB_COL5  = PD5  (pkg 86)   KB_COL13 = PD13 (pkg 60)
 *                              KB_COL6  = PD6  (pkg 87)
 *                              KB_COL7  = PD7  (pkg 88)
 *
 * Spares (not part of the 5x14 matrix, left to their existing config):
 * KB_ROW5-7 = PE5-7, KB_COL14 = PD14, KB_COL15 = PD15 (PD15 is now the
 * keyboard RGB data line per pin review line 491).
 *
 * The scan polarity is locked by the diode orientation in the schematic:
 * columns are push-pull outputs driven LOW one at a time (all others HIGH),
 * rows are inputs with pull-ups, and a pressed key reads LOW on its row.
 */

/* Rows: PE0..PE4. */
#define MATRIX_ROW_PORT GPIOE
/* Columns: PD0..PD13 (PD14/PD15 are spare/RGB and must not be touched). */
#define MATRIX_COL_PORT GPIOD

typedef struct {
    GPIO_TypeDef *port;
    uint8_t pin;
} matrix_pin_t;

/* Single source of truth for the mapping above; validated at init. */
static const matrix_pin_t s_row_pins[MATRIX_SCAN_ROWS] = {
    { MATRIX_ROW_PORT, 0u }, { MATRIX_ROW_PORT, 1u },
    { MATRIX_ROW_PORT, 2u }, { MATRIX_ROW_PORT, 3u },
    { MATRIX_ROW_PORT, 4u },
};

static const matrix_pin_t s_col_pins[MATRIX_SCAN_COLS] = {
    { MATRIX_COL_PORT, 0u },  { MATRIX_COL_PORT, 1u },
    { MATRIX_COL_PORT, 2u },  { MATRIX_COL_PORT, 3u },
    { MATRIX_COL_PORT, 4u },  { MATRIX_COL_PORT, 5u },
    { MATRIX_COL_PORT, 6u },  { MATRIX_COL_PORT, 7u },
    { MATRIX_COL_PORT, 8u },  { MATRIX_COL_PORT, 9u },
    { MATRIX_COL_PORT, 10u }, { MATRIX_COL_PORT, 11u },
    { MATRIX_COL_PORT, 12u }, { MATRIX_COL_PORT, 13u },
};

_Static_assert(MATRIX_SCAN_ROWS == EC_KEYMAP_ROWS,
               "matrix row count must match the keymap contract");
_Static_assert(MATRIX_SCAN_COLS == EC_KEYMAP_COLS,
               "matrix column count must match the keymap contract");
_Static_assert(sizeof(s_row_pins) / sizeof(s_row_pins[0]) == MATRIX_SCAN_ROWS,
               "row pin table must have MATRIX_SCAN_ROWS entries");
_Static_assert(sizeof(s_col_pins) / sizeof(s_col_pins[0]) == MATRIX_SCAN_COLS,
               "column pin table must have MATRIX_SCAN_COLS entries");

/* Debounced matrix and debounce state.  Zero-init: all-release, safe until
 * the first successful init. */
static ec_keymap_matrix_t s_matrix;
static uint8_t s_counters[MATRIX_SCAN_KEY_COUNT];
static uint32_t s_last_sample_ms;
static bool s_ready;

/* Belt-and-suspenders validation of the static config tables.  The tables
 * are compile-time constants so this can only trip on a future edit, but the
 * fail-safe contract says an invalid mapping must never report keys. */
static bool matrix_config_valid(void)
{
    for (uint32_t i = 0u; i < MATRIX_SCAN_ROWS; i++) {
        if (s_row_pins[i].port == NULL || s_row_pins[i].pin >= 16u) {
            return false;
        }
    }
    for (uint32_t i = 0u; i < MATRIX_SCAN_COLS; i++) {
        if (s_col_pins[i].port == NULL || s_col_pins[i].pin >= 16u) {
            return false;
        }
    }
    return true;
}

void matrix_scan_init(void)
{
    if (s_ready) {
        return;
    }

    /* The gpio.c defaults drive rows as outputs and leave the column pins as
     * pull-down inputs; this driver owns the matrix pins and reconfigures
     * them for the schematic's scan direction. */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIODEN | RCC_AHB1ENR_GPIOEEN;

    if (!matrix_config_valid()) {
        return; /* stay uninitialized: every tick reports all-release */
    }

    for (uint32_t r = 0u; r < MATRIX_SCAN_ROWS; r++) {
        GPIO_TypeDef *port = s_row_pins[r].port;
        uint32_t shift = (uint32_t)s_row_pins[r].pin * 2u;

        port->MODER = (port->MODER & ~(3u << shift))
                    | (GPIO_MODER_INPUT << shift);
        port->PUPDR = (port->PUPDR & ~(3u << shift))
                    | (GPIO_PUPDR_PU << shift);
    }

    for (uint32_t c = 0u; c < MATRIX_SCAN_COLS; c++) {
        GPIO_TypeDef *port = s_col_pins[c].port;
        uint32_t shift = (uint32_t)s_col_pins[c].pin * 2u;

        /* Drive the idle level HIGH before switching to output so the pin
         * never glitches low while the driver is configured. */
        port->ODR |= (1u << s_col_pins[c].pin);
        port->MODER = (port->MODER & ~(3u << shift))
                    | (GPIO_MODER_OUTPUT << shift);
        port->PUPDR &= ~(3u << shift); /* push-pull: no internal pull */
    }

    s_ready = true;
}

/* A few microseconds for the column driver change to propagate through the
 * 1k series resistors and the FFC/keyboard capacitance (a few RC time
 * constants, ~100 pF so tau ~ 100 ns) before the row levels are read.  The
 * 15 ms debounce window absorbs any residual settling on the first samples. */
static void matrix_settle(void)
{
    volatile uint32_t n = 64u;
    while (n-- != 0u) {
    }
}

void matrix_scan_tick(uint32_t now_ms)
{
    if (!s_ready) {
        return; /* fail-safe: s_matrix stays all-release */
    }

    uint16_t raw_rows[MATRIX_SCAN_ROWS] = { 0u, 0u, 0u, 0u, 0u };

    for (uint32_t c = 0u; c < MATRIX_SCAN_COLS; c++) {
        /* Drive column c LOW; every other column HIGH (inactive). */
        for (uint32_t k = 0u; k < MATRIX_SCAN_COLS; k++) {
            if (k == c) {
                s_col_pins[k].port->ODR &= ~(1u << s_col_pins[k].pin);
            } else {
                s_col_pins[k].port->ODR |= (1u << s_col_pins[k].pin);
            }
        }
        matrix_settle();

        /* A pressed key on this column pulls its row LOW. */
        for (uint32_t r = 0u; r < MATRIX_SCAN_ROWS; r++) {
            if ((s_row_pins[r].port->IDR & (1u << s_row_pins[r].pin)) == 0u) {
                raw_rows[r] |= (uint16_t)(1u << c);
            }
        }
    }

    /* All columns back to inactive HIGH before the next tick. */
    for (uint32_t k = 0u; k < MATRIX_SCAN_COLS; k++) {
        s_col_pins[k].port->ODR |= (1u << s_col_pins[k].pin);
    }

    matrix_debounce_step(raw_rows, s_matrix.rows, s_counters,
                         &s_last_sample_ms, now_ms,
                         MATRIX_SCAN_DEBOUNCE_MS);
}

void matrix_scan_get_matrix(ec_keymap_matrix_t *out)
{
    for (uint32_t r = 0u; r < MATRIX_SCAN_ROWS; r++) {
        out->rows[r] = s_matrix.rows[r];
    }
}
