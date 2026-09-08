"""Failure cases for current-source keyboard packages and assembly coverage."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import generate_keyboard_jlcpcb_package as export


class KeyboardExport(unittest.TestCase):
    def test_cpl_rejects_missing_duplicate_and_nonfinite_positions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=root/'positions.csv';out=root/'cpl.csv'
            def write(rows):
                with raw.open('w',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=['Ref','PosX','PosY','Rot','Side']);writer.writeheader();writer.writerows(rows)
            row={'Ref':'D320','PosX':'1','PosY':'-2','Rot':'90','Side':'top'}
            write([row]);self.assertEqual(export.write_cpl(raw,out,{'D320'}),{'D320'})
            for rows,refs in [([row],{'D320','D321'}),([row,row],{'D320'}),([dict(row,PosX='nan')],{'D320'})]:
                write(rows)
                with self.assertRaises(RuntimeError):export.write_cpl(raw,out,refs)

    def test_source_containing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'keyboard').mkdir();(root/'keyboard/board').write_text('source')
            with patch.object(export,'PROJECT_DIR',root),patch.object(export,'source_snapshot',return_value={'keyboard/board':'hash'}):
                with self.assertRaisesRegex(RuntimeError,'canonical source'):export.guard_output(root/'keyboard',True)
                target=root/'package';target.mkdir()
                with self.assertRaisesRegex(RuntimeError,'already exists'):export.guard_output(target,False)

    def test_promotion_preserves_old_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);old=root/'package';old.mkdir();(old/'data').write_text('old')
            new=root/'candidate';new.mkdir();(new/'data').write_text('new')
            with self.assertRaises(RuntimeError):export.promote(new,old,False)
            backup=export.promote(new,old,True)
            self.assertEqual((old/'data').read_text(),'new')
            self.assertEqual((backup/'data').read_text(),'old')

    def test_stale_source_missing_checksum_and_changed_file_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);package=root/'package';package.mkdir();board=root/'board';board.write_text('source')
            snapshot={'board':export.digest(board)}
            checks={k:0 for k in ('saved_drc_findings','refilled_drc_findings','native_airwires','copper_exclusion_hits','export_mismatches')}
            checks.update(parity_passed=True,copper_layers=2)
            manifest={'schema':1,'status':'CHECKED_FABRICATION_FILES','board':'board','source_sha256':snapshot,'checks':checks}
            (package/'manifest.json').write_text(json.dumps(manifest));(package/'artifact').write_text('first')
            with patch.multiple(export,PROJECT_DIR=root,BOARD=board,OUTPUT=package),patch.object(export,'source_snapshot',return_value=snapshot):
                export.write_checksums(package/'SHA256SUMS.txt');export.verify_package(package)
                (package/'artifact').write_text('changed')
                with self.assertRaisesRegex(RuntimeError,'checksum'):export.verify_package(package)
                export.write_checksums(package/'SHA256SUMS.txt');(package/'unlisted').write_text('extra')
                with self.assertRaisesRegex(RuntimeError,'omits'):export.verify_package(package)
                (package/'unlisted').unlink()
                with patch.object(export,'source_snapshot',return_value={'board':'new'}):
                    with self.assertRaisesRegex(RuntimeError,'stale'):export.verify_package(package)

    def test_old_release_without_binding_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            package=Path(temp);(package/'manifest.json').write_text('{"status":"APPROVED"}')
            with self.assertRaisesRegex(RuntimeError,'current checked manifest'):export.verify_package(package)

    def test_failed_staging_is_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'package'
            with self.assertRaisesRegex(RuntimeError,'fixture failure'):
                with export.retained_staging(output) as staging:
                    (Path(staging)/'report').write_text('failed native check')
                    raise RuntimeError('fixture failure')
            retained=list(Path(temp).glob('package.failed-*'))
            self.assertEqual(len(retained),1)
            self.assertEqual((retained[0]/'report').read_text(),'failed native check')
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
