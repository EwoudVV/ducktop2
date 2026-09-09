"""Check references across an active schematic hierarchy, including power symbols."""
from pathlib import Path
import argparse
import re
from collections import defaultdict
from check_release_candidate import top_level_blocks
from board_release_contract import BOARD_PROJECTS

ROOT=Path(__file__).resolve().parents[1]


def check_annotation(root):
    references=defaultdict(list)
    issues=[]
    visited=set()

    def visit(path):
        path=path.resolve()
        if path in visited:
            issues.append(f'{path.name}: repeated sheet instance needs a native annotation check')
            return
        visited.add(path)
        text=path.read_text()
        for block in top_level_blocks(text,'(symbol'):
            if not re.match(r'\(symbol\s',block):continue
            ref=re.search(r'\(property\s+"Reference"\s+"([^"]+)"',block)
            unit=re.search(r'\(unit\s+(\d+)\)',block)
            if not ref or not unit:
                issues.append(f'{path.name}: symbol has no reference or unit')
                continue
            name=ref.group(1)
            match=re.fullmatch(r'([#A-Za-z][^?\s]*?)(\d+)',name)
            if not match:
                issues.append(f'{path.name}: invalid reference {name}')
                continue
            key=(match.group(1),int(match.group(2)),int(unit.group(1)))
            references[key].append((path.name,name))
        for block in top_level_blocks(text,'(sheet'):
            if not re.match(r'\(sheet\s',block):continue
            filename=re.search(r'\(property\s+"Sheetfile"\s+"([^"]+)"',block)
            if not filename:
                issues.append(f'{path.name}: sheet has no filename')
                continue
            visit(path.parent/filename.group(1))

    visit(Path(root))
    for (prefix,number,unit),items in references.items():
        if len(items)>1:
            issues.append(f'duplicate {prefix}{number}, unit {unit}: '+', '.join(f'{name} in {path}' for path,name in items))
    return issues


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schematic',type=Path)
    args=parser.parse_args()
    paths=[args.schematic] if args.schematic else [ROOT/v['schematic'] for v in BOARD_PROJECTS.values()]
    count=0
    for path in paths:
        issues=check_annotation(path)
        print(str(path)+': '+('PASS' if not issues else 'FAIL'))
        for issue in issues:print('  '+issue)
        count+=len(issues)
    return 1 if count else 0


if __name__=='__main__':raise SystemExit(main())
