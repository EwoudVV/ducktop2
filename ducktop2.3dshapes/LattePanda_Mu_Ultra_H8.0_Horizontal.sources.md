# mu ultra and socket model

this assembly contains the official bare Mu Ultra model and the TE
2309411-1 socket from the original Mu reference assembly. the old Mu and
its cooler are left out. the manufacturer's models are grey; the model
does not add a cooling assembly.

sources:

- [Mu Ultra mechanical files](https://github.com/LattePandaTeam/LattePanda-Mu-Ultra/tree/main/Mechanicals), `LattePanda Mu Ultra 3D Model.stp`, git blob `4cd7fa29fb5791ae09e31193036b65438f992f80`.
- [Mu reference assembly](https://github.com/LattePandaTeam/LattePanda-Mu/blob/main/Mechanicals/LattePanda_Mu_H8.0_Horizontal.step.7z), socket product `c-2309411-1-1-3d v1`. the extracted socket keeps its original geometry and placement within that assembly.
- [TE 2309411-1](https://www.te.com/en/product-2309411-1.html), 260-position socket with 8 mm overall height.

the source files use Y as the module's thickness axis. in KiCad, use model
rotation `(-90, 0, 180)` degrees and offset `(0, -32.5, 5.5)` mm, at scale
`(1, 1, 1)`. the offset references the module edge and the 5.5 mm supports.
the footprint's own position and rotation are separate and stay unchanged.

the native STEP export places the module PCB across the intended 60 mm
depth. the support-hole spacing is 63.6 mm, with the holes 57 mm from the
edge datum, matching H1/H2. the socket's contact centers match the 260-pad
pattern within 0.10 mm along the pad length and 0.001 mm across the pitch.

the model is for checking placement and packaging. cooler fit, screw
engagement, connector seating and the completed assembly still need their
physical checks. licence notices are in the adjacent `.LICENSE.txt` file.
