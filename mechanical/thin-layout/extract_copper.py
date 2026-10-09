#!/usr/bin/env python3
"""Read the saved center-board copper without saving or changing the PCB."""
import hashlib
import json
from pathlib import Path

import pcbnew
import wx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.workbench/thin-layout-20261008/center-track-geometry.json'


def main():
    app = wx.App(False)
    source = ROOT / 'ducktop2-center.kicad_pcb'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    board = pcbnew.LoadBoard(str(source))

    def xy(point):
        return [round(pcbnew.ToMM(point.x) - 30.550001, 6),
                round(pcbnew.ToMM(point.y) - 36.55, 6)]

    rows = []
    for item in board.GetTracks():
        via = isinstance(item, pcbnew.PCB_VIA)
        width = item.GetWidth(item.GetLayer()) if via else item.GetWidth()
        row = {'uuid': str(item.m_Uuid.AsString()), 'kind': item.GetClass(),
               'net': item.GetNetname(), 'layer': board.GetLayerName(item.GetLayer()),
               'start': xy(item.GetStart()), 'end': xy(item.GetEnd()),
               'width_mm': pcbnew.ToMM(width)}
        if isinstance(item, pcbnew.PCB_ARC):
            row['mid'] = xy(item.GetMid())
        rows.append(row)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'pcb_sha256': before, 'coordinates': 'installed X,Y in mm',
                              'items': rows}, indent=2) + '\n')
    print(f'{len(rows)} track/via items read; PCB unchanged')


if __name__ == '__main__':
    main()
