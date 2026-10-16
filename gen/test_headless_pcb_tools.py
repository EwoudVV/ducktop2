"""Batch PCB jobs must not start a desktop application."""
import ast
from pathlib import Path
import unittest


TOOLS = (
    'export_power_placement.py', 'check_release_candidate.py',
    'check_center_pcie_coupling.py', 'bms_fabrication_geometry.py',
    'check_keyboard_rgb.py', 'prepare_keyboard_rgb_board.py',
    'check_radio_sma_geometry.py', 'generate_keyboard_jlcpcb_package.py',
    'generate_radio_daughterboard_pcb.py', 'export_board_assembly.py',
    'export_bms_assembly.py',
)


def gui_calls(source):
    tree = ast.parse(source)
    failures = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            if name in ('wx.App', 'wx.PyApp', 'wx.AppConsole'):
                failures.append(name)
        # Several workers are Python source strings passed to a subprocess.
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if '\n' in node.value and 'import pcbnew' in node.value:
                failures.extend(gui_calls(node.value))
    return failures


class HeadlessPcbTools(unittest.TestCase):
    def test_batch_tools_do_not_start_gui_apps(self):
        for name in TOOLS:
            with self.subTest(tool=name):
                self.assertEqual(gui_calls((Path(__file__).parent / name).read_text()), [])

    def test_subprocess_gui_startup_is_detected(self):
        source = 'worker = "import wx\\napp=wx.App(False)\\nimport pcbnew"'
        self.assertEqual(gui_calls(source), ['wx.App'])


if __name__ == '__main__':
    unittest.main()
