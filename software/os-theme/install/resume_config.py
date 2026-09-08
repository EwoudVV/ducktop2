#!/usr/bin/env python3
"""Update a boot cmdline without keeping an old resume target."""
import argparse
import re
from pathlib import Path

def replace_resume(text, uuid):
    if not re.fullmatch(r'[A-Fa-f0-9-]{8,64}', uuid):
        raise ValueError('invalid swap UUID')
    tokens=text.split()
    tokens=[token for token in tokens if not token.startswith(('resume=', 'resume_offset='))]
    return ' '.join(tokens+[f'resume=UUID={uuid}'])

def update(path, uuid, grub=False):
    original=path.read_text()
    if grub:
        matches=list(re.finditer(r'^GRUB_CMDLINE_LINUX="([^"\n]*)"$',original,re.M))
        if len(matches)!=1:
            raise ValueError('expected one quoted GRUB_CMDLINE_LINUX line')
        match=matches[0]
        changed=original[:match.start(1)]+replace_resume(match.group(1),uuid)+original[match.end(1):]
    else:
        changed=replace_resume(original,uuid)+'\n'
    if original!=changed:
        backup=path.with_name(path.name+'.ducktop-backup')
        if not backup.exists(): backup.write_text(original)
        path.write_text(changed)
    return changed

def main():
    p=argparse.ArgumentParser(); p.add_argument('path',type=Path); p.add_argument('uuid'); p.add_argument('--grub',action='store_true')
    a=p.parse_args(); update(a.path,a.uuid,a.grub)
if __name__=='__main__': main()
