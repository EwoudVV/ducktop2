# Ducktop2 mainboard local DRC exceptions

Status: **REQUIRES FABRICATOR/ASSEMBLER CONFIRMATION**
Date: 2026-07-18

`ducktop2.kicad_dru` contains only these geometry-specific exceptions:

1. `MK430` IM68A130 microphone: the 0.6 mm acoustic NPTH sits inside Infineon's
   Figure 13 pad-4 ground ring. A 0.15 mm local copper/hole minimum is used;
   the actual current gap is approximately 0.19 mm. The global 0.25 mm rule is
   unchanged.
2. `J241` and `J251`: Molex 73251-1153 edge-launch SMA pads intentionally meet
   the routed board edge. The exception is scoped to each footprint and
   `Edge.Cuts` only.
3. `H1` and `H2`: the soldered Wurth M2 retention standoffs intentionally
   overlap the A1 Mu socket/module courtyard. No unrelated courtyard overlap is
   permitted.

Before ordering, send the microphone land pattern/acoustic hole, SMA launches,
and retention stack to the PCB fabricator and assembler for DFM confirmation.
Do not convert unrelated final DRC errors into additional exceptions without a
manufacturer drawing and written disposition.

Primary geometry sources:

- Infineon IM68A130V01 datasheet, Figure 13:
  <https://www.infineon.com/dgdl/Infineon-IM68A130-DataSheet-v01_10-EN.pdf?fileId=8ac78c8c85ecb34701860371623f1204>
- Molex 73251-1153 drawing:
  <https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/732/73251/732511150_sd.pdf>
