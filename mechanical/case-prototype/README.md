# case prototype

editable CadQuery geometry for the first case fit study. the current saved
boards are the mechanical baseline. PCB files are read, never saved by these
scripts. the case is not ready for manufacture.

start with `hinge-fit.md`, `hinge-datums.json` and the drawings. the first
small prints are under `exports/hinge-tests/`. the retained Framework models
and drawings include their source revision, hashes, copyright and license.

from the repo root:

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 mechanical/case-prototype/inventory_boards.py
.workbench/layout-env/bin/python mechanical/case-prototype/hinges.py
.workbench/layout-env/bin/python mechanical/case-prototype/check_hinges.py
.workbench/layout-env/bin/python mechanical/case-prototype/draw_hinges.py
```

the existing environment uses CadQuery 2.8.0 and VTK. keep `cad.py` and
`hinges.py` together. changing a parameter and rerunning rebuilds solids,
STEP, STL and the actual-CAD view. meshes are print derivatives, not the
editable source. all exported STEP coordinates are millimeters, installed
X/Y with front +Y and Z positive down from the base bottom. the renderer
uses the same geometry in a conventional Z-up view, related by a rotation.

the original 3.3 kg kit is selected. its drawing label matches, but the
owned hinges still need the coupon fit and marking check. the panel, cell
and trackpad measurements remain outstanding. the planned full enclosure
uses separate load paths for the lid, keyboard, trackpad and batteries.

![stepped hinge adapters](views/hinge-mounts.png)
