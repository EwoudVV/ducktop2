#!/usr/bin/env python3
"""Read the BMS's native geometry for fabrication export checks. Never saves it."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys


def main():
    import wx
    app = wx.App(False)
    import pcbnew as p
    source, output = map(Path, sys.argv[1:3])
    root = Path(__file__).resolve().parents[1]
    library = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
    b = p.LoadBoard(str(source))
    b.BuildConnectivity()
    copper = list(b.GetEnabledLayers().CuStack())
    xy = lambda v: [v.x / 1e6, v.y / 1e6]

    def polys(s):
        def ring(r):
            return [xy(r.CPoint(j)) for j in range(r.PointCount())]
        return [{'outer': ring(s.COutline(i)),
                 'holes': [ring(s.CHole(i, j)) for j in range(s.HoleCount(i))]}
                for i in range(s.OutlineCount())]

    def shape(item, layer, margin=0):
        s = p.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(s, layer, margin, 500, p.ERROR_OUTSIDE)
        return polys(s)

    def signature(fp):
        q = p.FOOTPRINT(fp)
        if q.IsFlipped():
            q.Flip(q.GetPosition(), False)
        q.SetOrientationDegrees(0)
        q.SetPosition(p.VECTOR2I(0, 0))
        return Counter((pad.GetNumber(), int(pad.GetAttribute()), int(pad.GetShape()),
                        tuple(round(x, 3) for x in xy(pad.GetPosition())),
                        tuple(round(x, 3) for x in xy(pad.GetSize())),
                        tuple(xy(pad.GetDrillSize())),
                        round(pad.GetOrientationDegrees() % 180, 3),
                        tuple(pad.GetLayerSet().Seq())) for pad in q.Pads())

    result = {'board_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'native_airwires': b.GetConnectivity().GetUnconnectedCount(False),
              'copper_layers': [b.GetLayerName(x) for x in copper],
              'thickness_mm': b.GetDesignSettings().GetBoardThickness() / 1e6,
              'footprints': [], 'copper': [], 'drills': [], 'tracks': [],
              'library_pad_differences': [], 'library_sha256': {}, 'vias': []}
    for f in b.GetFootprints():
        pads = []
        for pad in f.Pads():
            row = {'number': pad.GetNumber(), 'net': pad.GetNetname(),
                   'position': xy(pad.GetPosition()), 'size': xy(pad.GetSize()),
                   'rotation': pad.GetOrientationDegrees(),
                   'attribute': int(pad.GetAttribute()), 'drill': xy(pad.GetDrillSize()),
                   'layers': [b.GetLayerName(x) for x in pad.GetLayerSet().Seq()],
                   'polygons': {}}
            for layer in copper:
                if pad.IsOnLayer(layer) and pad.GetAttribute() != p.PAD_ATTRIB_NPTH:
                    geometry = shape(pad, layer)
                    row['polygons'][b.GetLayerName(layer)] = geometry
                    result['copper'].append({'kind': 'pad', 'id': pad.m_Uuid.AsString(),
                        'ref': f.GetReference(), 'net': pad.GetNetname(),
                        'layer': b.GetLayerName(layer), 'polygons': geometry})
            pads.append(row)
            if pad.GetDrillSize().x:
                result['drills'].append({'position': xy(pad.GetPosition()),
                    'size': xy(pad.GetDrillSize()), 'rotation': pad.GetOrientationDegrees(),
                    'plated': pad.GetAttribute() != p.PAD_ATTRIB_NPTH,
                    'ref': f.GetReference(), 'pad': pad.GetNumber()})
        result['footprints'].append({'ref': f.GetReference(), 'value': f.GetValue(),
            'footprint': str(f.GetFPID().GetLibNickname()) + ':' + str(f.GetFPID().GetLibItemName()),
            'position': xy(f.GetPosition()),
            'rotation': f.GetOrientationDegrees(), 'layer': b.GetLayerName(f.GetLayer()),
            'attributes': f.GetAttributes(), 'pads': pads})
        lib, name = str(f.GetFPID().GetLibNickname()), str(f.GetFPID().GetLibItemName())
        folder = root / (lib + '.pretty')
        if not folder.is_dir():
            folder = library / (lib + '.pretty')
        loaded = p.FootprintLoad(str(folder), name)
        if loaded is None:
            raise RuntimeError('missing footprint library: ' + lib + ':' + name)
        result['library_sha256'][lib + ':' + name] = hashlib.sha256(
            (folder / (name + '.kicad_mod')).read_bytes()).hexdigest()
        if signature(f) != signature(loaded):
            result['library_pad_differences'].append(f.GetReference())
        for item in f.GraphicalItems():
            for layer in copper:
                if item.IsOnLayer(layer):
                    result['copper'].append({'kind': 'graphic', 'id': item.m_Uuid.AsString(),
                        'net': '', 'layer': b.GetLayerName(layer), 'polygons': shape(item, layer)})
    for item in list(b.GetTracks()) + list(b.GetDrawings()):
        via = isinstance(item, p.PCB_VIA)
        if via:
            result['drills'].append({'position': xy(item.GetPosition()),
                'size': [item.GetDrillValue() / 1e6] * 2, 'rotation': 0, 'plated': True,
                'ref': 'VIA', 'pad': ''})
            result['vias'].append({'id': item.m_Uuid.AsString(), 'net': item.GetNetname(),
                'position': xy(item.GetPosition()), 'diameter': item.GetWidth(p.F_Cu) / 1e6,
                'drill': item.GetDrillValue() / 1e6,
                'layers': [b.GetLayerName(x) for x in item.GetLayerSet().Seq()]})
        elif isinstance(item, p.PCB_TRACK):
            result['tracks'].append({'id': item.m_Uuid.AsString(), 'net': item.GetNetname(),
                'width': item.GetWidth() / 1e6, 'layer': b.GetLayerName(item.GetLayer()),
                'start': xy(item.GetStart()), 'end': xy(item.GetEnd())})
        for layer in copper:
            if item.IsOnLayer(layer):
                result['copper'].append({'kind': 'via' if via else 'track or graphic',
                    'id': item.m_Uuid.AsString(), 'net': item.GetNetname() if hasattr(item, 'GetNetname') else '',
                    'layer': b.GetLayerName(layer), 'polygons': shape(item, layer)})
    for z in b.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in copper:
            if z.IsOnLayer(layer):
                result['copper'].append({'kind': 'zone', 'id': z.m_Uuid.AsString(),
                    'net': z.GetNetname(), 'layer': b.GetLayerName(layer),
                    'polygons': polys(z.GetFilledPolysList(layer))})
    outline = p.SHAPE_POLY_SET()
    if not b.GetBoardPolygonOutlines(outline, False):
        raise RuntimeError('invalid board outline')
    result['outline'] = polys(outline)
    output.write_text(json.dumps(result, separators=(',', ':')) + '\n')
    print(json.dumps({k: result[k] for k in ('native_airwires', 'copper_layers',
          'board_sha256', 'library_pad_differences')}))


if __name__ == '__main__':
    main()
