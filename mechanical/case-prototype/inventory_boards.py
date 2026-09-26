#!/usr/bin/env python3
"""Read saved KiCad boards without saving or changing them.

Run using KiCad's Python. Coordinates retain KiCad's +Y toward the front.
Exact Edge.Cuts entities accompany tessellated outlines for the case model.
"""
import hashlib
import json
from pathlib import Path

import wx
app = wx.App(False)
wx.Log.EnableLogging(False)
import pcbnew as p

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def xy(v):
    return [round(v.x / 1e6, 6), round(v.y / 1e6, 6)]


def ring(line):
    return [xy(line.CPoint(i)) for i in range(line.PointCount())]


def main():
    placements = json.loads((ROOT / 'mechanical/board-placement.json').read_text())
    sources = {name: spec['file'] for name, spec in placements['boards'].items()}
    sources.update(keyboard='keyboard/12_keyboard_daughterboard.kicad_pcb',
                   radio='radio_daughterboard/radio_daughterboard.kicad_pcb')
    result = {'units': 'mm', 'coordinates': 'native KiCad XY, front +Y; apply assembly.json transforms',
              'boards': {}}
    for name, file in sources.items():
        path = ROOT / file
        board = p.LoadBoard(str(path))
        poly = p.SHAPE_POLY_SET()
        if not board.GetBoardPolygonOutlines(poly, False):
            raise ValueError(f'{name}: invalid Edge.Cuts')
        outlines = [{'outer': ring(poly.COutline(i)),
                     'holes': [ring(poly.CHole(i, h)) for h in range(poly.HoleCount(i))]}
                    for i in range(poly.OutlineCount())]
        edges, holes, footprints, keepouts = [], [], [], []
        for d in board.GetDrawings():
            if not isinstance(d, p.PCB_SHAPE) or d.GetLayer() != p.Edge_Cuts:
                continue
            kind = d.GetShapeStr()
            row = {'kind': kind, 'start': xy(d.GetStart()), 'end': xy(d.GetEnd())}
            if d.GetShape() == p.SHAPE_T_ARC:
                row.update(mid=xy(d.GetArcMid()), center=xy(d.GetCenter()))
            if d.GetShape() == p.SHAPE_T_CIRCLE:
                row.update(center=xy(d.GetCenter()), radius=d.GetRadius()/1e6)
                holes.append({'reference': None, 'source': 'Edge.Cuts circle',
                              'position': xy(d.GetCenter()), 'drill': [d.GetRadius()/5e5]*2})
            edges.append(row)
        for fp in board.GetFootprints():
            row = {'reference': fp.GetReference(), 'value': fp.GetValue(),
                   'footprint': str(fp.GetFPID()), 'position': xy(fp.GetPosition()),
                   'rotation': fp.GetOrientationDegrees(),
                   'side': 'back' if fp.IsFlipped() else 'front', 'models': [], 'courtyards': {}}
            fp.BuildCourtyardCaches()
            for side, layer in [('front', p.F_CrtYd), ('back', p.B_CrtYd)]:
                court = fp.GetCourtyard(layer)
                row['courtyards'][side] = [ring(court.COutline(i)) for i in range(court.OutlineCount())]
            for model in fp.Models():
                row['models'].append({'path': model.m_Filename,
                    'offset': [model.m_Offset.x, model.m_Offset.y, model.m_Offset.z],
                    'rotation': [model.m_Rotation.x, model.m_Rotation.y, model.m_Rotation.z],
                    'scale': [model.m_Scale.x, model.m_Scale.y, model.m_Scale.z]})
            row['pads'] = []
            for pad in fp.Pads():
                if pad.GetDrillSize().x:
                    q = {'reference': fp.GetReference(), 'pad': pad.GetNumber(),
                         'position': xy(pad.GetPosition()), 'drill': xy(pad.GetDrillSize()),
                         'net': pad.GetNetname(), 'size': xy(pad.GetSize()),
                         'source': 'pad', 'plated': pad.GetAttribute() != p.PAD_ATTRIB_NPTH}
                    holes.append(q)
                if fp.GetReference().startswith(('J', 'FPC')):
                    row['pads'].append({'number': pad.GetNumber(), 'position': xy(pad.GetPosition())})
            footprints.append(row)
        for zone in board.Zones():
            if zone.GetIsRuleArea():
                keepouts.append({'name': zone.GetZoneName(),
                                 'rings': [ring(zone.Outline().COutline(i)) for i in range(zone.Outline().OutlineCount())]})
        result['boards'][name] = {'file': file, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'thickness': board.GetDesignSettings().GetBoardThickness()/1e6,
            'copper_layers': board.GetCopperLayerCount(), 'outlines': outlines, 'edges': edges,
            'holes': holes, 'footprints': sorted(footprints, key=lambda x: x['reference']),
            'keepouts': keepouts}
        pts = [q for o in outlines for q in o['outer']]
        bounds = [[min(q[i] for q in pts), max(q[i] for q in pts)] for i in [0, 1]]
        print(name, 'bounds', bounds, 'thickness', result['boards'][name]['thickness'],
              'mount refs', [h['reference'] for h in holes if h['reference'] is None or h['reference'].startswith('H')])
    (HERE / 'board-inventory.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
