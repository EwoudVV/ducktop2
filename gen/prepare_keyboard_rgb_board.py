#!/usr/bin/env python3
"""Make an unrouted RGB placement copy. Run with KiCad's pcbnew Python."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from keyboard_rgb_contract import LED_OFFSET_MM

ROOT = Path(__file__).resolve().parents[1]

# Support parts stay in the strip beside the keys. Positions are in the saved
# keyboard's coordinate frame, not the main-board or assembled-case frame.
POSITIONS = {
    'U320':(284.5,21,0), 'U321':(284.5,28,0),
    'R320':(289.25,19.6,0), 'R321':(279.8,28,90), 'R322':(289.25,29,0),
    'R323':(289.1,16.7,0),
    'C320':(289.25,26.2,0), 'C321':(289.5,8,90),
    'C322':(289.25,23.2,0), 'C323':(289.25,21.4,0),
    'C324':(280.4,20.8,90), 'C325':(280.4,24,90), 'C326':(289.1,13.5,0),
    'R330':(283.4,4,90), 'R331':(286.3,4,90), 'R332':(286.3,8,90),
    'R333':(283.4,8,90), 'R334':(283.4,12,90), 'R335':(286.3,12,90),
    'TPK1':(284.5,55,0), 'TPK2':(288,55,0), 'TPK3':(284.5,60,0),
    'TPK4':(288,60,0), 'TPK5':(284.5,65,0), 'TPK6':(288,65,0),
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--netlist',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--clear-routing',action='store_true',required=True)
    args=parser.parse_args()
    if args.source.resolve()==args.output.resolve():
        raise ValueError('write a checked candidate before replacing the saved board')
    import wx
    app=wx.App(False)
    wx.Log.EnableLogging(False)
    import pcbnew as p
    board=p.LoadBoard(str(args.source))
    before={f.GetReference():(f.GetPosition().x,f.GetPosition().y,f.GetOrientationDegrees())
            for f in board.GetFootprints()}
    removed_tracks=len(list(board.GetTracks()))
    for item in list(board.GetTracks()):
        board.Delete(item)
    for zone in list(board.Zones()):
        if not zone.GetIsRuleArea():
            board.Delete(zone)
    for drawing in board.GetDrawings():
        if isinstance(drawing, p.PCB_TEXT):
            value = drawing.GetText()
            if value.startswith('Ducktop2 MX ULP keyboard daughterboard rev A:'):
                drawing.SetText(value.replace('daughterboard rev A:', 'daughterboard RGB:'))
            elif value.startswith('J320 is parked in the right margin'):
                drawing.SetText('J320 keeps the existing cable exit. Switches and LEDs are locked for routing.')
    xml=ET.parse(args.netlist).getroot()
    components={c.get('ref'):c for c in xml.findall('./components/comp')}
    assert len(components)==221 and all(f'SW{i}' in components for i in range(320,385))
    pin_nets={}
    nets={n.GetNetname():n for n in board.GetNetInfo().NetsByNetcode().values()}
    for net in xml.findall('./nets/net'):
        name=net.get('name')
        if name.startswith('unconnected-'):
            name=''
        if name not in nets:
            item=p.NETINFO_ITEM(board,name)
            board.Add(item)
            nets[name]=item
        for node in net.findall('node'):
            pin_nets[node.get('ref'),node.get('pin')]=name
    existing={f.GetReference():f for f in board.GetFootprints()}
    library=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
    for ref,c in components.items():
        new=ref not in existing
        if new:
            lib,item=c.findtext('footprint').split(':',1)
            folder=ROOT/(lib+'.pretty')
            if not folder.is_dir():
                folder=library/(lib+'.pretty')
            fp=p.FootprintLoad(str(folder),item)
            assert fp is not None,(ref,c.findtext('footprint'))
            fp.SetFPID(p.LIB_ID(lib,item))
            board.Add(fp)
            fp.SetReference(ref)
        else:
            fp=existing[ref]
        fp.SetValue(c.findtext('value'))
        props={f.get('name'):f.text or '' for f in c.findall('./fields/field')}
        for name,value in props.items():
            fp.SetField(name,value)
            fp.GetField(name).SetVisible(False)
        for field in list(fp.GetFields()):
            if field.GetName()=='ReleasedRevA':
                fp.Remove(field)
        fp.SetDNP(False)
        excluded=ref.startswith('TPK')
        fp.SetExcludedFromBOM(excluded)
        fp.SetExcludedFromPosFiles(excluded)
        path=p.KIID_PATH()
        for ident in c.findtext('tstamps').strip('/').split('/'):
            path.push_back(p.KIID(ident))
        fp.SetPath(path)
        for pad in fp.Pads():
            key=(ref,pad.GetNumber())
            pad.SetNet(nets[pin_nets[key]] if key in pin_nets else nets[''])
        if ref.startswith('LED'):
            switch=existing['SW'+ref[3:]]
            point=switch.GetPosition()
            fp.SetPosition(p.VECTOR2I(point.x+round(LED_OFFSET_MM[0]*1e6),
                                     point.y+round(LED_OFFSET_MM[1]*1e6)))
            fp.SetOrientationDegrees(0)
            fp.SetLocked(True)
        elif ref in POSITIONS:
            x,y,angle=POSITIONS[ref]
            fp.SetPosition(p.VECTOR2I(round(x*1e6),round(y*1e6)))
            fp.SetOrientationDegrees(angle)
        if ref.startswith('SW') or ref=='J320':
            fp.SetLocked(True)
        if new:
            fp.Reference().SetLayer(p.B_SilkS)
            fp.Reference().SetMirrored(True)
            fp.Reference().SetTextSize(p.VECTOR2I(650000,800000))
            fp.Reference().SetTextThickness(150000)
            fp.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
            pos=fp.GetPosition()
            fp.Reference().SetPosition(p.VECTOR2I(pos.x,pos.y-1500000))
            fp.Value().SetVisible(False)
        for field in fp.GetFields():
            if field.IsVisible() and field.GetLayer()in(p.F_SilkS,p.B_SilkS):
                field.SetTextThickness(150000)
    for f in board.GetFootprints():
        ref=f.GetReference()
        if ref.startswith(('SW','D')) or ref=='J320':
            assert before[ref]==(f.GetPosition().x,f.GetPosition().y,f.GetOrientationDegrees()),ref
    board.SetFileName(str(args.output))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    p.SaveBoard(str(args.output),board)
    board.BuildConnectivity()
    print(json.dumps({'footprints':len(list(board.GetFootprints())),
        'removed_tracks_and_vias':removed_tracks, 'tracks_and_vias':len(list(board.GetTracks())),
        'unconnected_native':board.GetConnectivity().GetUnconnectedCount(False),
        'copper_layers':board.GetCopperLayerCount()}))


if __name__=='__main__':
    main()
