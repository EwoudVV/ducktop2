import json
import tempfile
import unittest
import fnmatch
from pathlib import Path

import setup_net_classes as classes


class NetClasses(unittest.TestCase):
    def test_escaped_sheet_slash_is_not_bus_syntax(self):
        net = "/Wi-Fi{slash}Bluetooth & OLEDs/WIFI_REFCLK_E_N"
        pattern = classes.project_pattern(net)
        self.assertNotIn("{", pattern)
        self.assertTrue(fnmatch.fnmatchcase(net, pattern))

    def test_usb_segments_keep_the_same_pair_geometry(self):
        nets = {"/PD1 Dual-Role/PD1_CONN_DP", "/PD1 Dual-Role/PD1_CONN_DN",
                "/USB Hub + Ports/HUB_DIS5_DP", "/USB Hub + Ports/HUB_DIS5_DN",
                "/Maker MCU/MAKER_USB_MCU_DP", "/Maker MCU/MAKER_USB_MCU_DN",
                "/RADIO_CODEC_USB_HOST_DP", "/RADIO_CODEC_USB_HOST_DN"}
        assigned, _ = classes.classify(nets)
        self.assertEqual(set(assigned["DIFF_90"]), nets)

    def test_clock_controls_are_separate_from_clock_pairs(self):
        nets = {"/Wi-Fi{slash}Bluetooth & OLEDs/WIFI_REFCLK_E_P",
                "/Wi-Fi{slash}Bluetooth & OLEDs/WIFI_REFCLK_E_N",
                "/Mu Carrier/PCIE_M_CLKREQ_N", "/TCP0_TXRX0_P", "/TCP0_TXRX0_N"}
        assigned, _ = classes.classify(nets)
        self.assertEqual(len(assigned["DIFF_85"]), 2)
        self.assertEqual(set(assigned["DIFF_100"]), {"/TCP0_TXRX0_P", "/TCP0_TXRX0_N"})
        self.assertFalse(any("/Mu Carrier/PCIE_M_CLKREQ_N" in values for values in assigned.values()))

    def test_custom_rules_and_clearance_survive_an_update(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "board.kicad_pro"
            path.with_suffix(".kicad_pcb").write_text('(kicad_pcb (net "SENSE") (net "/USBC1_DN"))')
            path.write_text(json.dumps({
                "net_settings": {"classes": [{"name": "Default", "clearance": .25},
                                               {"name": "quiet", "clearance": .4}],
                                 "netclass_patterns": [{"netclass": "quiet", "pattern": "SENSE"}]},
                "board": {"design_settings": {}}
            }))
            assigned, _ = classes.classify({"SENSE", "/USBC1_DN"})
            result = classes.expected_project(assigned, path)["net_settings"]
            self.assertEqual(next(x for x in result["classes"] if x["name"] == "Default")["clearance"], .25)
            self.assertIn({"netclass": "quiet", "pattern": "SENSE"}, result["netclass_patterns"])
            self.assertIn({"netclass": "DIFF_90", "pattern": "/USBC1_DN"}, result["netclass_patterns"])


if __name__ == "__main__":
    unittest.main()
