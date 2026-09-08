# maker target

the RP2350 target builds with Pico SDK 2.2.0 and the exact TinyUSB submodule
in `dependencies.json`. the custom board header uses the 12 MHz crystal and
4 MiB flash in the schematic. no Pico board LED or VSYS pin defaults are
borrowed onto the maker fault and user-power pins.

exposed signals map to GPIO0..22 and GPIO26..28. GPIO29 enables the user
rails, GPIO24 senses the host USB gate and GPIO25 reads the user-power fault.
all user signals start as inputs without pulls. GPIO and ADC input modes are supported. bounded UART, SPI and I2C
transactions borrow their fixed pins only while those pins are passive.
transaction details and the host tool are in [software/maker](../../software/maker/README.md).

HID feature packets are 64 bytes: `MK2` plus version byte 1, increasing u32
sequence at offset 4, rail request at 8, authorization at 9, then 26 mode
bytes. remaining bytes must be zero. modes are 0 high impedance, 1 input,
2 ADC input, 3 low output and 4 high output. ADC mode is accepted only on
the three ADC pins. requests expire after 1 s unless a new sequence arrives.
USB loss, host-gate loss, watchdog or a power fault removes user rails and
makes the user signals passive. normal application watchdog period is 500 ms.

input reports carry the last sequence, fault at 8, rail readback at 9,
authorization state at 10, digital levels at 11..36, and three u16 ADC samples
at 40..45. byte 47 reports the startup guard and physical fault input, and
bytes 48..51 carry the last bus sequence. output modes only change when requested, avoiding repeated output
direction transitions in the steady-state loop.

U922 controls the header bus switches autonomously. there is no MCU-readable
OE feedback. a 250 ms startup guard does not prove the switch state. safe
firmware makes its pins passive; it cannot open that hardware switch on a
runtime command. external signals can still reach passive MCU pads once the
supervisor enables the switch. use the header's electrical limits.

## reproducible build

clone the SDK and checkout the commits in `dependencies.json`, then initialize
its `lib/tinyusb` submodule. use the complete Arm GNU 13.3.Rel1 toolchain,
which includes newlib. Homebrew's compiler-only package is not sufficient
for the Pico SDK target.

```sh
python3 firmware/tools/build_maker.py \
  --sdk /absolute/path/to/pico-sdk \
  --toolchain /absolute/path/to/arm-gnu-toolchain \
  --output .workbench/maker-build
```

the wrapper rejects different or modified SDK commits, builds ELF/BIN files,
creates a UF2 with the official RP2350 ARM secure family ID and compares its
payload with the binary. `build-manifest.json` records the artifact hashes.
no board is programmed by this command.

BOOTSEL plus RUN provides the ROM recovery path; SWD can program and read
back the ELF. the SDK clock bootstrap precedes `main`, so physical BOOTSEL/
SWD recovery must also be tested when startup does not reach the application
watchdog. GPIO modes, ADC readings, overcurrent behavior, watchdog timing,
USB loss and the actual flash boot all remain HIL tests.
