# maker bus commands

`maker_tool.py` performs one bounded transaction and then returns the user
rails and GPIO to their passive state. it requires `--authorize`, waits for
the startup guard, and never retries a timed-out transaction. `--rails`
explicitly enables the user power rails while the transaction runs. this
software has not been run against a physical maker controller.

```sh
python3 software/maker/maker_tool.py --hidraw /dev/hidrawN --authorize uart --tx 4142 --read 2 --rate 115200
python3 software/maker/maker_tool.py --hidraw /dev/hidrawN --authorize --rails i2c --address 0x55 --tx 10 --read 2
python3 software/maker/maker_tool.py --hidraw /dev/hidrawN --authorize spi --tx 9f000000 --read 4 --mode 0
```

select the maker HID device, product 0x2329 under VID 0x1209. the EC uses a
different product ID. each transaction permits up to 32 transmit and 32
receive bytes, with a 1..100 ms timeout. it requires a current authorization
lease with enough time left to finish. unrelated GPIO settings are retained
by the protocol; this one-shot tool deliberately starts and ends all-off.

| bus | fixed MCU pins | supported settings |
| --- | --- | --- |
| UART0 | GP0 TX, GP1 RX | 8N1, 300..115200 baud, optional write then exact-length read |
| I2C1 | GP2 SDA, GP3 SCL | 7-bit addresses 0x08..0x77, 10..100 kHz, combined write/read with repeated START |
| SPI0 | GP16 MISO, GP17 CS, GP18 SCK, GP19 MOSI | 8-bit MSB-first, modes 0..3, 10 kHz..1 MHz, active-low CS |

SPI full-duplex lengths must match. a read-only SPI transfer clocks 0xff bytes;
a write-only transfer drains and discards received data. I2C needs external
pull-ups and SPI CS needs an external inactive-state pull-up. the target
removes its pin drive after each transaction. bus rates are software bounds,
not evidence of cable signal integrity or external-device compatibility.

pins must be in `MAKER_IO_HIGH_IMPEDANCE` before a transaction can borrow them.
GPIO input/output/ADC assignments on any required bus pin cause a conflict.
requests are rechecked after pending GPIO configuration has been applied.

## packets

all packets are 64-byte unnumbered HID feature/input reports, with
little-endian integers. Linux feature ioctls prepend a zero report-ID byte.
normal GPIO authorization uses the existing `MK2` version 1 packet.

bus requests start with `MB2` and version byte 1. sequence u32 is at 4, bus
kind at 8 (UART 1, I2C 2, SPI 3), flags at 9 (SPI mode; otherwise zero),
TX/RX lengths at 10/11, baud or clock u32 at 12, timeout u16 at 16 and I2C
address at 18. bytes 19..31 are zero; TX bytes start at 32, with zero padding.
sequences advance independently of GPIO-control sequences. accepted or
rejected requests with a fresh sequence consume it; they cannot be replayed
after a fault-clear.

responses start with `MR2` and version 1. they echo the sequence at 4 and bus
kind at 9. status is at 8, received length at 10, actual configured rate u32
at 12, elapsed milliseconds u16 at 16, and returned data at 32. status values
0..7 mean success, invalid request, lease unavailable, pin conflict, timeout,
I/O error, replay and busy. partial UART bytes may be returned with an error;
that does not mean the requested transaction completed.

UART/SPI polling loops check an absolute deadline and live authorization.
I2C write and read share one absolute deadline. the power-fault interrupt
immediately makes the user pins and rails passive; cleanup resets the bus
peripherals. failures clear authorization and latch a transaction fault.
a fresh all-off control request can clear a removed fault, followed by a
new authorization. a transaction is never silently retried.

host tests exercise the parser and actual target driver loops with simulated
peripherals. physical bus timing, overcurrent interruption, USB behavior and
external-device transactions remain HIL tests.

```sh
python3 -B software/maker/test_maker_tool.py
sh firmware/tools/run_host_tests.sh
```
