"""Externally compensated SYS_5V supply for the complete switched bank."""
from build_ducktop2 import FOOTPRINTS


def add_sys5_power(s):
    def part(ref, symbol, value, x, y, footprint, pins, mpn,
             maker="Texas Instruments", **extra):
        s.place(ref, symbol, value, x, y, footprint=footprint,
                pin_nets={str(k): (v if isinstance(v, tuple) else
                                   (v, "local") if v else ("", "nc"))
                          for k, v in pins.items()},
                extra_props={"Manufacturer": maker, "MPN": mpn, **extra})

    def r(ref, value, x, y, a, b, mpn):
        part(ref, "R", value, x, y, FOOTPRINTS["R"], {1: a, 2: b}, mpn, "Vishay" if mpn.startswith("TNP") else "Yageo")

    def c(ref, value, x, y, a, b="GND", mpn="GRM188R71H104KA93D",
          fp="C_100n", maker="Murata"):
        part(ref, "C", value, x, y, FOOTPRINTS[fp], {1: a, 2: b}, mpn, maker)

    out = ("SYS_5V", "hier")
    vin = ("VSYS", "hier")
    pins = {
        **{str(n): vin for n in (1, 2, 3, 27, 28, 29)},
        **{str(n): "GND" for n in (6, 8, 17, 23, 24, 25, 26, 30)},
        **{str(n): "BUCK5_SW" for n in (20, 21, 22)},
        "4": "BUCK5_BOOT", "5": "BUCK5_SW_BOOT", "7": "SYS_5V_PG",
        "9": "BUCK5_EN", "10": "", "11": "SYS5_PRE_SENSE", "12": out,
        "13": "BUCK5_CONFIG", "14": "BUCK5_RT", "15": "BUCK5_COMP",
        "16": "BUCK5_FB", "18": "BUCK5_VDDA", "19": "BUCK5_VCC",
    }
    s.text(1180, 20, "== SYS_5V: 4.5A continuous, complete switched-bank model ==")
    part("U6", "LM706A0", "LM706A0RRXR SYS_5V 5.106V; 4.5A envelope", 1240, 75,
         FOOTPRINTS["LM706A0"], pins, "LM706A0RRXR",
         Datasheet="https://www.ti.com/lit/gpn/LM706A0",
         Compensation="2.2k+220n;2.2nHF;0.95MHz;local20..80uFcer+90..500uFpoly;switchedC_le300uF",
         Layout="local_power_return;Kelvin_shunt_pair;6mm_max_inductor_height;qualify_load_steps")
    part("L4", "L", "6.8uH 18.4A Isat30; SYS_5V", 1370, 55,
         FOOTPRINTS["L_XGL1060_CENTER"], {1: "BUCK5_SW", 2: "SYS5_PRE_SENSE"},
         "XGL1060-682MEC", "Coilcraft", Layout="pad1_marked_short_lead_to_SW;6mm_max_height")
    for ref, y in (("RS2360", 55), ("RS2361", 75)):
        part(ref, "R", "10mOhm 1% 1W; parallel pair gives 5mOhm", 1460, y,
             FOOTPRINTS["R_ERJ8CW_CENTER"], {1: "SYS5_PRE_SENSE", 2: out},
             "ERJ8CWFR010V", "Panasonic",
             Layout="Kelvin_at_RS2360_inner_pad_edges;power_branch_mismatch_le20uOhm")
    r("R40", "54.9k 0.02% 5ppm SYS5 FB high", 1370, 115, out, "BUCK5_FB", "TNPU060354K9HZEN00")
    r("R41", "10.2k 0.02% 5ppm SYS5 FB low", 1405, 115, "BUCK5_FB", "GND", "TNPU060310K2HZEN00")
    r("R42", "100k 1% SYS5 EN high", 1180, 145, ("MU_HOST_ACTIVE", "hier"), "BUCK5_EN", "RC0603FR-07100KL")
    r("R45", "100k 1% SYS5 EN low", 1215, 145, "BUCK5_EN", "GND", "RC0603FR-07100KL")
    r("R46", "100k SYS_5V PG pull-up", 1250, 145, ("MCU_3V3", "hier"), "SYS_5V_PG", "RC0603FR-07100KL")
    r("R2360", "22.1k 0.02% 5ppm SYS5 RT", 1285, 145, "BUCK5_RT", "GND", "TNPU060322K1HZEN00")
    r("R2361", "29.4k SYS5 standalone config", 1320, 145, "BUCK5_CONFIG", "GND", "RC0603FR-0729K4L")
    r("R2362", "2.2k SYS5 COMP", 1180, 185, "BUCK5_COMP", "BUCK5_COMP_RC", "TNPU06032K20HZEN00")
    c("C2362", "220n 50V X7R SYS5 COMP", 1215, 185, "BUCK5_COMP_RC",
      mpn="C0603C224K5RACTU", maker="KEMET")
    c("C2363", "2.2n 50V C0G SYS5 COMP HF", 1250, 185, "BUCK5_COMP",
      mpn="C0603C222J5GACTU", maker="KEMET")
    r("R2363", "1R SYS5 BOOT damping", 1295, 185, "BUCK5_BOOT", "BUCK5_BOOT_C", "RC0603FR-071RL")
    c("C43", "47n 25V SYS5 bootstrap", 1330, 185, "BUCK5_BOOT_C", "BUCK5_SW_BOOT",
      "GRM155R71E473KA88D", "C_0402")
    for ref, x in (("C40", 1180), ("C41", 1215)):
        c(ref, "10u 50V SYS5 input", x, 225, vin, mpn="CGA5L1X7R1H106K160AC",
          fp="C_10u", maker="TDK")
    for ref, x in (("C42", 1250), ("C2365", 1285)):
        c(ref, "100n 50V SYS5 input HF", x, 225, vin)
    c("C2360", "22u 25V SYS5 VCC; effective minimum 4.7u", 1320, 225, "BUCK5_VCC",
      mpn="GRM32ER71E226KE15L", fp="C_1210")
    c("C2361", "100n 50V SYS5 VDDA", 1355, 225, "BUCK5_VDDA")
    for ref, x in (("C44", 1390), ("C45", 1425)):
        c(ref, "22u 25V SYS5 output; TI characterized part", x, 225, out,
          mpn="GRM32ER71E226KE15L", fp="C_1210")
    part("C2364", "C_Polarized", "220u 10V SYS5 local reservoir; 6mOhm", 1460, 185,
         FOOTPRINTS["C_100u_25V_poly"], {1: out, 2: "GND"},
         "T530D227M010ATE006", "KEMET", HeightMax="3.1mm")
    s.text(1180, 265, "SYS5: local ceramic <=80uF, polymer <=500uF, all switched branches <=300uF; 4.5A load plus startup. source admission remains separate.")
