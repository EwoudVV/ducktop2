import importlib.util
from pathlib import Path
import tempfile
import unittest
s=importlib.util.spec_from_file_location('resume',Path(__file__).parents[1]/'install/resume_config.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ResumeTests(unittest.TestCase):
    def test_existing_cmdline(self):
        self.assertEqual(m.replace_resume('quiet resume=UUID=old resume_offset=24 splash','12345678-abcd'),
                         'quiet splash resume=UUID=12345678-abcd')
    def test_grub_and_idempotence(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'grub'; original='GRUB_TIMEOUT=5\nGRUB_CMDLINE_LINUX="quiet resume=UUID=old"\n';p.write_text(original)
            m.update(p,'12345678-abcd',True);m.update(p,'12345678-abcd',True)
            self.assertEqual(p.read_text().count('resume='),1)
            self.assertEqual(p.with_name('grub.ducktop-backup').read_text(),original)
    def test_reject_unsupported_grub(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'grub';p.write_text('GRUB_TIMEOUT=5\n')
            with self.assertRaises(ValueError):m.update(p,'12345678-abcd',True)
if __name__=='__main__':unittest.main()
