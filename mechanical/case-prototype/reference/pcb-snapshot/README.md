# pinned mechanical inputs

these are native KiCad STEP exports and the reviewed mechanical inputs
for this case snapshot. `manifest.json` records exact PCB, STEP and input
hashes. `input-audit.json` records source-file commits and the reviewed
geometry equivalence where the electronics work changed value text or
metadata. the live PCB files may continue changing independently.

`inventory.json` retains the original footprint/model references. source
models and their existing credits remain in the main project. this
snapshot does not change their licenses. the separate Framework references
retain their source URLs, revision records and CC-BY-4.0 license.

refresh only through the reviewed inventory/export/freeze sequence in the
case README. do not mix one new board or input into an older snapshot.
