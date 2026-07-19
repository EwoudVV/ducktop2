# LattePanda Mu module and BIOS release contract

Status: **CONTROLLED INPUT, FIRST-ARTICLE READBACK REQUIRED**
Project: Ducktop2
Date: 2026-07-18

## Released assembly selection

| Item | Released identity |
|---|---|
| PCB-fitted host socket | TE Connectivity `2309411-1`, 260 contacts, 8.0 mm standard orientation |
| Removable compute module | DFRobot `DFR1149`, LattePanda Mu Intel N305, 16 GB RAM, 64 GB eMMC |
| BIOS branch | LattePanda Mu `DFLT` |
| BIOS archive | `S70NC1R200-16G-B.zip` |
| BIOS archive SHA-256 | `4e3e197b100c77c8ad0cbc03c744cc7118b7f98203bd48c6c813aa30d78436e9` |
| BIOS binary | `S70NC1R200-16G-B.bin` |
| BIOS binary SHA-256 | `6edcfe021d84baf2b6ea3e4f4df4e81442a6be3580905f255221644d0eeb0bed` |
| BIOS build date | 2026-06-03 |
| Official repository blob | `d41dd0df4e25cd1575c1b3fd2cbb044b83b2b2d3` |
| Mu retention standoffs | 2 x Wurth Elektronik `9774055243R`, M2, 5.5 mm above PCB |
| Retention screws | 2 x RS PRO `914-1462`, M2 x 4 mm; sample-fit before release |

The DFLT branch is required because Ducktop2's native USB, M.2 E-key,
Ethernet, NVMe, and TCP0 lane allocation is designed around that profile. A
different Mu SKU or BIOS branch is a design change, not an approved substitute.

## Source authority

- Official BIOS manifest:
  <https://github.com/LattePandaTeam/LattePanda-Mu/blob/main/Softwares/BIOS/DFLT/README.md>
- Official Mu specifications:
  <https://docs.lattepanda.com/content/mu_edition/specification/>
- Official edge-connector guide:
  <https://docs.lattepanda.com/content/mu_edition/design_guide_edge_connector/>

The BIOS binary is not vendored into this repository. Before use, download it
from the official LattePanda repository and verify both the archive and binary
SHA-256 values above.

## First-article release procedure

1. Verify the purchased socket and module labels against the released MPNs.
2. Inspect socket orientation, solder joints, standoff height, screw engagement,
   and thermal-stack contact before applying power.
3. Read back and record the installed BIOS identity/hash. Do not assume the
   module arrived with the released DFLT image.
4. Cold-boot and enumerate NVMe, E-key, RTL8111H Ethernet, both native USB 3.x
   ports, external HDMI, and the onboard eDP path.
5. Repeat warm reboot and suspend/resume enumeration after routing, stackup,
   firmware, and display-harness release.

No first article is approved for normal use until this procedure has retained
evidence and the firmware/HIL release gates pass.
