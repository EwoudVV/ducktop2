# gauge setup and recovery

`profile.json` is unresolved. there is no released chemistry ID, calibrated
golden image or learning-cycle result for the owned cells. the normal EC
keeps gauge-derived power authorization invalid while this remains open.

use bqStudio and a pack substitute to configure the exact BQ34Z100-G1
installation. establish series count, divider scaling, design capacity,
current shunt gain and offset, charge/discharge polarity, temperature setup,
ChemID and learning-cycle results. compare the gauge to external instruments
before exporting a golden FlashStream image. keep the image hash and that
evidence together. do not substitute a nominal capacity from a shop listing.

`flashstream.py` implements TI's W/C/X format, converts its 8-bit wire address
to the 7-bit Linux address, bounds each operation and stops on the first
failed comparison. by default it parses and validates only. apply mode
requires a reviewed `QUALIFIED_IMAGE` profile with an exact image hash, a
Linux I2C fixture bus, a pack substitute and an output report. it does not
unseal, reset or learn the gauge implicitly; those actions must be in the
reviewed image. recovery from ROM mode needs the matching TI recovery image
and fixture procedure, rather than replaying arbitrary writes.

```sh
python3 firmware/gauge/test_flashstream.py
python3 firmware/gauge/flashstream.py exact-image.bqfs --profile reviewed-profile.json
```

a programming pass means all operations and compare steps completed. it does
not mean calibration or real-cell validation passed. the tool records that
distinction. the fixture must isolate pack negative correctly and must not
bypass either shunt or the protection path through its ground lead.

format reference: TI [SLUA801](https://www.ti.com/lit/an/slua801/slua801.pdf).
