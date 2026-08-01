# Ducktop2 Target Port Status

Generated: 2026-07-30
Version: `0.3.0-policy`
EC: STM32F407VGT6 (LQFP-100)
Maker: RP2350A

## Current Status

All 42 HIL rows in `release/hil_matrix.csv` are **NOT_RUN**. No HIL evidence yet.

**2026-07-30 Completion: Steps 1–4 (foundation) are DONE.** A working ARM GCC toolchain was set up, the firmware compiles cleanly with `-Wall -Wextra -Wpedantic -Werror` on GCC 16.1.0, and produces `ducktop2_ec.bin` (9,228 bytes). The binary initializes the STM32F407VGT6 with HSE 8 MHz → PLL → 168 MHz core, SysTick 1 ms tick, I2C1 master at 400 kHz, GPIO safe-state on all pins, and calls `ec_controller_step()` at 50 Hz. See below for file inventory.

**2026-07-31 Addition: host-tested keyboard Fn-layer keymap.** `ec/src/ec_keymap.c`
(+ `ec/include/ducktop2/ec/ec_keymap.h`) translates the fabricated 5×14 MX ULP
matrix state into a USB HID boot-6KRO keyboard report plus a 4-slot consumer
report, applying the user-confirmed Fn layer: Fn+1..0→F1..F10, Fn+Esc→grave,
Fn+Bksp→Delete, Fn+Up/Down→Brightness ±, Fn+Left/Right→Volume ∓. Pure C, no
hardware dependence; 22 host tests in `tests/test_ec_keymap.c` cover every
mapping, Fn passthrough, modifier combine, 6KRO overflow (ErrorRollOver),
consumer concurrency, and report reset. Wired into `run_host_tests.sh` and
`CMakeLists.txt` (new `ducktop2_ec_keymap` library + `ec_keymap_tests`).
Remaining target-side work for the keyboard is the matrix scan (drive rows/read
cols per the diode orientation in `generate_keyboard_daughterboard_sheet.py`)
and the USB HID interface — both target-only steps; the keymap logic itself is
complete and host-verified.

---

## 1. I2C Bus Topology

The EC uses a single I2C1 peripheral (PB6=SCL, PB7=SDA) with a TCA9548A mux to isolate the service buses:

| Bus | Address (7-bit) | Device | Notes |
|-----|-----------------|--------|-------|
| **I2C1 root** | — | STM32F407 controller | PB6/SCL, PB7/SDA, AF4 |
| TCA9548A | **0x70** | I2C mux (U45) | A0/A1/A2=GND → 0x70 |
| TCA9539PWR | **0x74** | Source manager I/O expander (U44) | Resettable, on root bus |
| Ch0 (OLED A) | 0x3C | SSD1306 display L | Behind TCA9548A ch0 |
| Ch1 (OLED B) | 0x3C | SSD1306 display R | Behind TCA9548A ch1 |
| Ch2 (PD1 svc) | **0x20** | TPS25751A #1 | Behind TCA9548A ch2 |
| Ch3 (PD2 svc) | **0x21** | TPS25751A #2 | Behind TCA9548A ch3 |

**On the root I2C1 bus (direct):**
- TCA9539PWR @ **0x74** — "source manager" I/O expander (PD1_PATH_EN, PD2_PATH_EN, PD1_EFUSE_FAULT_N, PD2_EFUSE_FAULT_N)
- TCA9548A @ **0x70** — I2C mux for OLEDs and PD service buses

**Behind TCA9548A channels:**
- Ch0: OLED A (SSD1306 @ 0x3C)
- Ch1: OLED B (SSD1306 @ 0x3C)
- Ch2: TPS25751A PD1 service bus (7-bit addr **0x20**, matches `EC_PD1_TCPC_I2C_ADDRESS_7BIT`)
- Ch3: TPS25751A PD2 service bus (7-bit addr **0x21**, matches `EC_PD2_TCPC_I2C_ADDRESS_7BIT`)

**Not on EC I2C bus — these are behind the BQ25798's I2C target (separate):**
- BQ25798 charger: default 7-bit addr **0x6B** (PROG/ADDR = VCC or GND depends on strap)
- BQ34Z100 fuel gauge: default 7-bit addr **0x55** (standard TI default)

**Note:** The BQ25798 and BQ34Z100 are on their own I2C bus separate from the EC I2C1. The EC programs BQ25798 via I2C transactions — verify whether they share the same I2C1 bus or a different one. From the schematic, BQ25798/CE is controlled by CHG_ENABLE (PA4), and CHG_INT_N (PA2) is the interrupt. The I2C for the charger/gauge VSYS domain may need different pull-up voltages.

---

## 2. STM32F407 Pin Assignment (Complete)

### Power / System
| Pin | Signal | STM32 Function | Notes |
|-----|--------|----------------|-------|
| PH0 | HSE_IN | OSC_IN | 8 MHz crystal |
| PH1 | HSE_OUT | OSC_OUT | |
| PC14 | LSE_IN | OSC32_IN | 32.768 kHz |
| PC15 | LSE_OUT | OSC32_OUT | |
| PA13 | SWDIO | SWDIO | |
| PA14 | SWCLK | SWCLK | |
| BOOT0 | BOOT0 | BOOT0 | Pulled low for flash boot |

### I2C1 (Main system bus)
| Pin | Signal | AF | Notes |
|-----|--------|----|-------|
| PB6 | I2C_SCL | AF4 | I2C1_SCL |
| PB7 | I2C_SDA | AF4 | I2C1_SDA |

### USB
| Pin | Signal | Notes |
|-----|--------|-------|
| PA11 | MCU_USB_DM | USB OTG FS DM |
| PA12 | MCU_USB_DP | USB OTG FS DP |

### UARTs
| Pin | Signal | Peripheral | Notes |
|-----|--------|-----------|-------|
| PA9 | GNSS_UART_TX | USART1_TX | |
| PA10 | GNSS_UART_RX | USART1_RX | |
| PB10 | RADIO_VHF_UART_TX | USART3_TX | |
| PB11 | RADIO_VHF_UART_RX | USART3_RX | |
| PC6 | RADIO_UHF_UART_TX | USART6_TX | |
| PC7 | RADIO_UHF_UART_RX | USART6_RX | |

### ADC (Thermal)
| Pin | Signal | ADC Channel | Notes |
|-----|--------|------------|-------|
| PA6 | AUX_DC_ADC | ADC1_IN3 | AUX DC input voltage |
| PA7 | THERM_SKIN_ADC | ADC1_IN7 | Skin temperature |
| PB0 | THERM_MU_ADC | ADC1_IN8 | Mu coldplate temperature |

### PWM / Timer
| Pin | Signal | Timer | Notes |
|-----|--------|-------|-------|
| PE9 | FAN_PWM | TIM1_CH1 | Blower PWM (25 kHz recommended, open-drain) |

### Source Manager / Power Control (via TCA9539PWR @ 0x74)
| Signal | Direction | Notes |
|--------|-----------|-------|
| PD1_PATH_EN | Output to TCA9539 | PD1 path enable (drives TPS26630 EN/UVLO) |
| PD2_PATH_EN | Output to TCA9539 | PD2 path enable |
| PD1_EFUSE_FAULT_N | Input from TCA9539 | PD1 TPS26630 fault status |
| PD2_EFUSE_FAULT_N | Input from TCA9539 | PD2 TPS26630 fault status |
| SOURCE_MGR_INT_N | Input to PC13 | TCA9539 interrupt |

### Charger Interface (direct GPIO)
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PA1 | BQ_ALERT | Input | BQ34Z100 alert |
| PA2 | CHG_INT_N | Input | BQ25798 interrupt |
| PA4 | CHG_ENABLE | Output | BQ25798 /CE enable (active high) |
| PA3 | PMIC_QON_ASSERT | Output | BQ25798 QON pulse |

### Mu Module Interface
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PA0 | MU_PWRBTN_N | Output | Open-drain power button |
| PA5 | MU_RSTBTN_N | Output | Mu reset button |
| PE13 | MU_12V_ENABLE | Output | TPS552892 EN |
| PE14 | MU_S0_HIGH | Input | Mu PSON/S0 status |
| PE15 | MU_12V_PG | Input | Power-good from TPS552892 |

### Service Mux Reset
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PB12 | SERVICE_MUX_RESET_REQ_N | Output | AND-gated with NRST → TCA9548A RESET_N |

### Keyboard Matrix
| Pins | Signals | Direction | Notes |
|------|---------|-----------|-------|
| PE0–PE7 | KB_ROW0–KB_ROW7 | Output (row drive) | 8 rows |
| PD0–PD15 | KB_COL0–KB_COL15 | Input (column scan) | 16 columns |
| PC0 | KB_RGB_PWR_EN | Output | RGB LED power enable |
| PC1 | KB_RGB_FAULT_N | Input | RGB overcurrent fault |
| PD15 | KB_RGB_DATA_3V3 | Output | RGB LED data line |

### Keyboard / Trackpad
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PB1 | TRACKPAD_FAULT_N | Input | Trackpad power switch fault |

### Radio Daughterboard
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PB5 | RADIO_DB_PWR_EN | Output | Power enable for radio board |
| PB8 | GNSS_EXTINT | Input | GNSS interrupt |
| PB13 | GNSS_RESET_N | Output | GNSS reset |
| PB14 | GNSS_PPS | Input | GNSS pulse-per-second |
| PB15 | RADIO_VHF_PTT_N | Output | VHF push-to-talk |
| PC2 | RADIO_VHF_RF_SEL_3V3 | Output | VHF RF switch |
| PC3 | RADIO_UHF_RF_SEL_3V3 | Output | UHF RF switch |
| PC8 | RADIO_UHF_PTT_N | Output | UHF push-to-talk |
| PC9 | RADIO_VHF_PD_N | Output | VHF power-down |
| PC10 | RADIO_UHF_PD_N | Output | UHF power-down |
| PC11 | RADIO_VHF_SQL | Input | VHF squelch |
| PC12 | RADIO_UHF_SQL | Input | UHF squelch |
| RADIO_DB_PRESENT_N | Input | Daughterboard presence (active low) |
| RADIO_DB_FAULT_N | Input | Daughterboard fault (active low) |
| RADIO_DB_PG | Input | Daughterboard power-good |

### Audio
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PE11 | AUDIO_MIC_EN | Output | Microphone power enable |
| PE12 | AUDIO_AMP_EC_EN | Output | Amplifier enable |

### PD Controller Monitoring
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PC4 | PD1_VALID_N | Input | PD1 valid (TPS25751A) |
| PB2 | PD2_VALID_N | Input | PD2 valid |
| PE8 | PD1_TCPC_IRQ_N | Input | PD1 TPS25751A IRQ |
| PB4 | PD2_TCPC_IRQ_N | Input | PD2 TPS25751A IRQ |
| PB9 | PD_PROTECT_FAULT_N | Input | PD protection fault (TPS26630) |

### Other
| Pin | Signal | Direction | Notes |
|-----|--------|-----------|-------|
| PB3 | INTERNAL_USB_VBUS_FAULT_N | Input | USB hub fault |
| PA8 | WIFI_W_DISABLE1_N_EC | Output | Wi-Fi disable |
| PA15 | WIFI_W_DISABLE2_N_EC | Output | Bluetooth disable |
| PE10 | LID_CLOSED_N | Input | Lid switch |
| PC5 | FAN_TACH | Input | Fan tachometer |
| PC13 | (SOURCE_MGR_INT_N) | Input | TCA9539 interrupt |

---

## 3. Schematic-vs-Firmware Issues Found

### Confirmed matches (no issue):
- PB6/PB7 = I2C1_SCL/SDA → matches STM32 AF4 I2C1
- PE9/TIM1_CH1 = FAN_PWM → correct timer for PWM fan
- PA6/PA7/PB0 = ADCs → available ADC1 channels
- PB10/PB11 = USART3 → matches alternate function
- PC6/PC7 = USART6 → matches alternate function
- PA9/PA10 = USART1 → matches alternate function

### Potential issues requiring verification:

1. **BQ25798 / BQ34Z100 I2C bus**: The schematic shows the charger and gauge on a separate I2C bus, NOT on the EC I2C1 bus. Verify the actual I2C pull-up voltage domain — if they're on VSYS domain (not MCU_3V3), level translation may be needed, or they may share the EC I2C1 bus with MCU_3V3 pull-ups. This needs PCB netlist verification.

2. **TCA9539PWR vs PCA9539**: Schematic shows TCA9539PWR at 0x74, but the firmware header `ec_telemetry.h` says `EC_SOURCE_MANAGER_I2C_ADDRESS_7BIT 0x74` — this matches. However TCA9539 vs PCA9539 difference: TCA9539 is the automotive-grade, PCA9539 is the standard. Both use the same I2C protocol.

3. **FAN_PWM (PE9, TIM1_CH1)**: The schematic says "25 kHz open-drain PWM" and "firmware never drives the fan PWM node high." The Delta fan expects 25 kHz open-drain. PE9 on TIM1_CH1 can do this but needs AF1 (TIM1). Confirm STM32CubeMX configuration uses AF1 for PE9.

4. **FAN_TACH (PC5)**: Fan tachometer is on PC5. This is not a timer input on STM32F407 (it's a basic GPIO). Consider using a timer input capture pin (e.g., PA0/TIM2_CH1, PA6/TIM3_CH1) if RPM measurement via input capture is desired. If only edge counting or polling is needed, PC5 is fine as GPIO input.

5. **I2C pull-up resistors**: Verify on schematic that SCL/SDA have appropriate pull-ups (typically 4.7kΩ to MCU_3V3 for 100 kHz, 2.2kΩ for 400 kHz). The SCL/SDA bus has TCA9548A, TCA9539PWR, plus the mux channels.

6. **OLED I2C address conflict**: Both OLEDs are 0x3C but behind separate TCA9548A channels — this is correct, no conflict.

---

## 4. Inventory of Existing Code

### Policy Core (host-tested, complete)

| File | Provides |
|------|---------|
| `ec/include/ducktop2/ec/ec_policy.h` | `ec_inputs_t`, `ec_outputs_t`, `ec_controller_t`, `ec_controller_step()`, `ec_controller_request_source()`, etc. |
| `ec/include/ducktop2/ec/ec_commit.h` | `ec_commit_apply()`, `ec_commit_force_safe()`, `ec_commit_driver_t` abstraction |
| `ec/include/ducktop2/ec/ec_telemetry.h` | `ec_telemetry_build_snapshot()`, `ec_telemetry_bq34z100_minutes_to_seconds()`, address constants |
| `ec/src/ec_policy.c` | Implementation: policy state machine, source validation, power budgeting |
| `ec/src/ec_commit.c` | Implementation: sequential ordered commit with rollback |
| `ec/src/ec_telemetry.c` | Implementation: snapshot builder, minute-to-second conversion |
| `maker/include/ducktop2/maker/maker_policy.h` | RP2350 maker controller API |
| `maker/src/maker_policy.c` | RP2350 maker policy implementation |

### Tests (host-tested)

| File | Tests |
|------|-------|
| `tests/test_ec_policy.c` | Policy state machine vectors |
| `tests/test_ec_commit.c` | Commit sequencing and rollback |
| `tests/test_ec_telemetry.c` | Telemetry building |
| `tests/test_maker_policy.c` | Maker controller tests |
| `tests/vectors/ec_policy_vectors.csv` | Regression vectors |
| `tests/vectors/maker_policy_vectors.csv` | Regression vectors |

### TPS25751A Configuration (released, not redistributable)

The TPS25751A EEPROM configuration is **released** — the JSON source config `ducktop2_dual_role_config.json` and the generated binaries exist in `tps25751a/generated/` (with expected SHA-256 hashes in `release_manifest.json`). The config is DRP with 5V/9V/15V sink PDOs at 3A, one 5V/900mA source PDO.

### What Does NOT Exist (must be written)

| Item | Status |
|------|--------|
| STM32F407 startup code (Reset_Handler, vector table) | **MISSING** |
| STM32F407 linker script (flash.ld, sram.ld) | **MISSING** |
| STM32 HAL/LL driver abstraction (I2C, GPIO, TIM, ADC, USART) | **MISSING** |
| I2C target driver (`ec_commit_write_fn`) | **MISSING** |
| TPS25751A I2C read transactions (PDO 0x31, RDO 0x32, PD Status 0x35) | **MISSING** |
| BQ25798 I2C driver (IINDPM, VSYSMIN, charger enable) | **MISSING** |
| BQ34Z100 I2C driver (SOC, voltage, current, time, capacity) | **MISSING** |
| TCA9548A mux select driver | **MISSING** |
| TCA9539PWR I/O expander driver | **MISSING** |
| ADC driver (PA6 AUX_DC, PA7 skin, PB0 Mu temp) | **MISSING** |
| TIM1 PWM driver (PE9 fan) | **MISSING** |
| Fan tachometer reader (PC5) | **MISSING** |
| USB device descriptor / CDC or HID | **MISSING** |
| OLED SSD1306 I2C driver | **MISSING** |
| Watchdog timer setup (IWDG) | **MISSING** |
| `main.c` with init + superloop | **MISSING** |
| STM32CubeMX `.ioc` configuration file | **MISSING** |
| ARM GCC toolchain CMake preset | **MISSING** |
| `.elf` / `.bin` build artifacts | **MISSING** |
| Programming / recovery documentation | **MISSING** |

---

## 5. Target Port Roadmap

### Step 1: Toolchain and CMake Setup (trivial)
- Create `firmware/ec_target/` directory for STM32 target files
- Add ARM GCC CMake preset in `CMakePresets.json` (arm-gcc-debug, arm-gcc-release)
- Create `cmake/arm-none-eabi.cmake` toolchain file
- Verify `arm-none-eabi-gcc` compilation with a minimal main.c

### Step 2: Linker Script and Startup Code (moderate)
- Create `ec_target/stm32f407vg.ld` — 1MB flash at 0x08000000, 192KB RAM at 0x20000000
- Create `ec_target/startup_stm32f407vg.s` — Reset_Handler, vector table, SystemInit call
- Create `ec_target/system_stm32f4xx.c` — minimal clock config (HSE 8MHz → PLL → 168MHz SYSCLK, USB 48MHz from PLL Q)
- **Important**: HSE = 8 MHz crystal. PLL settings: PLLM=8, PLLN=336, PLLP=2 → 168 MHz SYSCLK, PLLQ=7 → 48 MHz USB

### Step 3: GPIO and Basic I/O (trivial)
- Create `ec_target/gpio.c/h` — pin initialization matching the assignment table above
- All outputs start in safe state (low/off), all inputs configured with appropriate pull-up/down
- PB12 (SERVICE_MUX_RESET_REQ_N) driven low to hold mux in reset during init

### Step 4: I2C Driver and Bus Probe (moderate)
- Create `ec_target/i2c.c/h` — STM32 I2C1 master driver (polling or IRQ)
- Initial bus probe: scan TCA9548A @ 0x70, TCA9539PWR @ 0x74
- Write TCA9548A mux channel select function
- Write TCA9539PWR I/O expander driver (read/write port registers)
- **Dependency**: step 3 (GPIO), step 2 (clock)

### Step 5: Source Manager Communication (moderate)
- Program TCA9539PWR to read PD1_EFUSE_FAULT_N, PD2_EFUSE_FAULT_N
- Program TCA9539PWR to drive PD1_PATH_EN, PD2_PATH_EN
- Implement the `ec_commit_write_fn` callback that maps `EC_COMMIT_PD1_PATH_ENABLE`, `EC_COMMIT_PD2_PATH_ENABLE` to TCA9539PWR writes
- **Dependency**: step 4 (I2C driver)

### Step 6: TPS25751A Service-Bus Transactions (moderate)
- Select TCA9548A ch2, read TPS25751A@0x20 registers 0x31, 0x32, 0x35
- Select TCA9548A ch3, read TPS25751A@0x21 registers 0x31, 0x32, 0x35
- Implement contract validation (live PD Status + PDO + RDO must agree)
- Populate `ec_source_observation_t.present`, `.negotiated_voltage_mv`, `.qualified_input_current_ma`
- **Dependency**: step 4 (I2C)

### Step 7: Power Control (moderate)
- Wire up CHG_ENABLE = PA4
- Wire up MU_12V_ENABLE = PE13
- Wire up MU_12V_PG = PE15 input
- Wire up PD1_PATH_EN / PD2_PATH_EN (via TCA9539)
- Wire up all eFuse fault inputs
- Implement `EC_COMMIT_CHARGER_ENABLE`, `EC_COMMIT_MU_12V_ENABLE`, `EC_COMMIT_CHARGER_IINDPM_MA`, `EC_COMMIT_CHARGE_BUDGET_MW`, `EC_COMMIT_MU_EDP_BUDGET_MW` in the commit driver
- 5V AUX qualification path (500 mA initial, drop to 250 mA IINDPM)
- **Dependency**: steps 5, 6

### Step 8: BQ25798 I2C Driver (moderate)
- Create `ec_target/bq25798.c/h` — I2C transactions to program IINDPM, VSYSMIN
- Charger register map: charge current, input current limit, VSYSMIN, charger enable/disable
- Read back IINDPM for mismatch checking
- TS_IGNORE=1, STOP_WD_CHG=1
- **Note**: BQ25798 may be on the EC I2C1 bus or a separate bus — verify from PCB
- **Dependency**: step 4 (I2C)

### Step 9: BQ34Z100 I2C Driver (moderate)
- Create `ec_target/bq34z100.c/h` — read SOC, voltage, current, time-to-empty, time-to-full, remaining/full capacity, cycle count, health
- Populate `ec_telemetry_inputs_t` with validity flags
- Use correct sign convention: Current() positive=charging, negative=discharging
- TimeToEmpty/TimeToFull: reject 0xffff before converting minutes→seconds
- **Note**: BQ34Z100 may share same bus as BQ25798
- **Dependency**: step 4 (I2C)

### Step 10: ADC, PWM, Fan, Thermal (trivial-moderate)
- Create `ec_target/adc.c/h` — PA6 (AUX_DC), PA7 (skin), PB0 (Mu): 12-bit, single conversion or scan
- Create `ec_target/pwm.c/h` — TIM1_CH1 on PE9 for 25 kHz fan PWM
- Create `ec_target/tach.c/h` — PC5 as GPIO input for fan tach (or timer capture if re-pinned)
- Populate `ec_inputs_t.thermal_ok` and `.thermal_data_valid`
- **Dependency**: step 2 (clock)

### Step 11: Main Firmware Loop (complex)
- Create `ec_target/main.c` with init sequence:
  1. Configure GPIOs as inputs, hold resets asserted (step 3)
  2. Initialize IWDG (4-second timeout, or appropriate)
  3. Call `ec_commit_force_safe()` through bounded I2C driver
  4. Release source manager and service mux resets
  5. Probe all I2C devices
  6. Read TPS25751A contracts, BQ34Z100 telemetry, charger status
  7. Call `ec_controller_step()` at a fixed rate (e.g., 50 Hz / 20 ms)
  8. Apply outputs via `ec_commit_apply()`
  9. Feed watchdog after completion
- **Dependency**: all previous steps

### Step 12: Host USB and Debug (moderate)
- Configure USB OTG FS in device mode (PA11/PA12)
- Implement CDC ACM virtual COM port for debug logging
- Or use SWO/SWO printf via SWD
- **Dependency**: step 2 (clock — USB requires precise 48 MHz)

### Step 13: OLED Display Driver (trivial)
- Create `ec_target/oled.c/h` — SSD1306 I2C driver behind TCA9548A ch0/ch1
- Use `ec_telemetry_snapshot_t` to render fields with validity-bit checks
- **Dependency**: step 4 (I2C), step 11 (telemetry)

### Step 14: Optional Loads and Radio (trivial-moderate)
- Implement keyboard RGB enable (PC0, PC1, PD15)
- Implement radio daughterboard power sequencing (PB5, RADIO_DB_PG, RADIO_DB_FAULT_N, RADIO_DB_PRESENT_N)
- Implement audio amp/mic enables (PE11, PE12)
- **Dependency**: step 11

### Step 15: HIL Testing and Evidence (complex)
- Execute each of the 42 HIL tests from `hil_matrix.csv`
- Record evidence with SHA-256
- Update `target_release.json` with binary hashes
- **Dependency**: all previous steps

---

## 6. Estimated Complexity Summary

| Step | Description | Complexity | Depends On |
|------|-------------|-----------|------------|
| 1 | Toolchain + CMake | trivial | — |
| 2 | Linker + startup + clock | moderate | 1 |
| 3 | GPIO init | trivial | 2 |
| 4 | I2C driver | moderate | 2, 3 |
| 5 | Source manager (TCA9539) | moderate | 4 |
| 6 | TPS25751A transactions | moderate | 4 |
| 7 | Power control wiring | moderate | 5, 6 |
| 8 | BQ25798 driver | moderate | 4 |
| 9 | BQ34Z100 driver | moderate | 4 |
| 10 | ADC/PWM/tach/thermal | trivial-moderate | 2 |
| 11 | Main loop + policy | complex | 3–10 |
| 12 | USB + debug | moderate | 2 |
| 13 | OLED display | trivial | 4, 11 |
| 14 | Optional loads | trivial-moderate | 11 |
| 15 | HIL testing | complex | 11–14 |

---

## 7. Minimal Viable Target Port (MVP)

The minimal target that can power up the EC, blink an LED, and establish I2C communication:

1. **Steps 1–4**: Toolchain, startup, GPIO, I2C
2. **Step 5**: TCA9539 source manager — read eFuse faults, control path enables
3. **Step 6**: TPS25751A PD contract reads — validate PDO+RDO+Status
4. **Step 7**: Power control for PD1 bootstrap path with charger off
5. **Step 11**: Basic main loop calling `ec_controller_step()` + `ec_commit_apply()`

This MVP would enable executing HIL tests EC-PD1-001, EC-PD2-001, EC-PD-COLD-001, EC-PD-5V-001, EC-PD-SVC-001.

---

## 8. Required Tools and SDKs

| Tool | Purpose | Version |
|------|---------|---------|
| ARM GCC | Compiler for STM32F407 | `arm-none-eabi-gcc` >= 10.3 |
| CMake | Build system | >= 3.20 |
| STM32CubeMX | Peripheral/clock config generator | Optional (can hand-write init) |
| ST-Link probe | SWD programming and debug | Any (V2, V3, or clone) |
| openocd or pyocd | Flash tool | latest |
| Python 3 | Verification contracts | >= 3.8 |

STM32CubeMX is **not required** — the clock tree is straightforward (8 MHz HSE → PLL → 168 MHz core, 48 MHz USB), and pin mux assignments are documented above. A hand-written `stm32f4xx_hal_msp.c` or direct register writes work fine.

---

## 9. Startup Order (per firmware/release/README.md)

```
1. GPIO input safe state + resets asserted
2. IWDG init + brownout detection
3. ec_commit_force_safe() via I2C → TCA9539 all off
4. Release TCA9539 reset + TCA9548A reset
5. I2C probe: verify TCA9548A@0x70, TCA9539@0x74
6. Read TPS25751A@0x20 (ch2) and @0x21 (ch3) — Active PDO 0x31, Active RDO 0x32, PD Status 0x35
7. Read BQ34Z100 telemetry (if on same bus)
8. Read BQ25798 charger status
9. ec_controller_step() → ec_commit_apply()
10. Feed watchdog, loop
```

---

## 10. Completed Files (ec_target/)

```
ec_target/
├── CMakeLists.txt                   # ARM GCC CMake, -nostdlib -ffreestanding
├── arm-none-eabi-toolchain.cmake    # Standalone toolchain file for presets
├── STM32F407VGTx_FLASH.ld          # 1 MB flash, 128 KB SRAM, 64 KB CCM
├── startup_stm32f407vgtx.s         # Full vector table (82 entries), .data/.bss init
├── system_stm32f4xx.c              # 168 MHz PLL: HSE 8M → PLL=336, PLLP=2, PLLQ=7
├── stm32f4xx.h                     # Register map: RCC, GPIO, I2C, TIM, ADC, IWDG, NVIC
├── gpio.h                          # GPIO function declarations (all pins)
├── gpio.c                          # gpio_init_all(): 50+ pin configs, ADC, TIM1 PWM
├── i2c.h                           # I2C1 + TCA9548A + TCA9539 API
├── i2c.c                           # I2C master (400 kHz FM), mux, expander
├── main.c                          # Init sequence + 50 Hz policy loop
├── libc_stubs.c                    # memcpy, memset, memcmp, __aeabi_uldivmod
└── include/                        # Freestanding C headers
    ├── stdint.h
    ├── stddef.h
    ├── stdbool.h
    ├── limits.h
    └── string.h
```

## 11. Integration Status per Steps 1-8

| Step # | Description | Status |
|--------|-------------|--------|
| 1 | Critical MCU pins as inputs, resets asserted | ✅ `gpio_init_all()` configures all pins, outputs in safe state |
| 2 | Watchdog + brownout init | ⏳ IWDG struct defined in stm32f4xx.h, init not yet in main.c |
| 3 | `ec_commit_force_safe()` through bounded driver | ✅ `commit_write()` callback handles all 11 commands. TCA9539 PD path control implemented. |
| 4 | Release resets, recover I2C bus | ✅ Service mux reset REQ_N released after I2C init, bus probed for TCA9548A |
| 5 | Read TPS25751A, BQ25798, BQ34Z100 telemetry | ⏳ PD contracts read via `i2c1_read(0x31/0x32/0x35)`. BQ charger/gauge: stubs only |
| 6 | `ec_controller_step()` → `ec_commit_apply()` | ✅ Main loop: read_inputs → step → apply → snapshot → DelayMs(20) |
| 7 | AUX current qualification at 500 mA → 250 mA IINDPM | ⏳ Charger IINDPM BQ25798 I2C writes not yet implemented |
| 8 | Watchdog after policy + commit + telemetry | ⏳ IWDG struct defined, not yet activated in main.c |

## 12. Build Instructions

```bash
# Prerequisites: arm-none-eabi-gcc (Homebrew: brew install arm-none-eabi-gcc)
# cmake (Homebrew: brew install cmake)

# From firmware/ directory:
cmake -S ec_target -B build/arm-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/arm-debug

# Output:
#   build/arm-debug/ducktop2_ec       # ELF (121 KB)
#   build/arm-debug/ducktop2_ec.bin   # Raw binary (9,228 bytes)

# Flash via ST-Link:
# openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
#   -c "program build/arm-debug/ducktop2_ec.bin 0x08000000 verify reset exit"
```
