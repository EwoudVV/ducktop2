# working on ducktop2

start with the [project README](../README.md), then [current status and work
order](design-status.md). each topic has one working guide linked from the
README. older tracked versions are available through git.

the canonical folder on this Mac is
`/Users/ellievanvooren/Documents/kicad/ducktop2`.

- PCB routing and edits should happen in the visible KiCad editor so i can
  follow them in real time. build the live connection first, work within the
  task i asked for, and preserve unrelated existing routing.
- commit only when i explicitly ask for a commit.
- check the working tree first and preserve uncommitted work.
- change schematic generators, then regenerate deliberately. do not hand-edit `.kicad_sch` files.
- verify saved files against the intended result. logs and previous notes are not proof of the current files.
- show the work order and give clear progress updates.
- write plainly, in my voice, with no em dashes. devlogs are lowercase,
  chat-only unless requested otherwise, with time since the previous commit.
- keep important files in the actual project. temporary copies are only for
  preparing and checking a change.
- update the relevant current page when the design changes. remove obsolete
  or duplicated text instead of creating another handoff, archive, or status page.

the center PCB needs the split pipeline's net normalization; do not use a
normal F8 update. full split/recovery/hygiene scripts can replace routing
or placement. tool paths, candidate handling, and the deliberate rebuild
order are in [build and verify](build-and-verify.md).
