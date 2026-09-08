#!/usr/bin/env python3
"""Check the radio SMA slot datum and complete on-board copper lands."""
from __future__ import annotations
import json,sys
import wx
app=wx.App(False)
import pcbnew as p

def check(path):
 b=p.LoadBoard(str(path));assert b is not None
 if abs(b.GetDesignSettings().GetBoardThickness()/1e6-1.6)>.001:raise ValueError('Molex 73251-1153 placement is checked for a nominal 1.6 mm board')
 outline=p.SHAPE_POLY_SET()
 if not b.GetBoardPolygonOutlines(outline,False):raise ValueError('invalid board outline')
 rows=[]
 for f in b.GetFootprints():
  if f.GetReference() not in ['J241','J251']:continue
  if str(f.GetFPID().GetLibItemName())!='SMA_Molex_73251-1153_EdgeMount_Horizontal':raise ValueError('SMA footprint needs a new geometry review')
  if abs(f.GetPosition().y/1e6-24.26)>.001 or abs(f.GetOrientationDegrees()%360-270)>.001:raise ValueError(f.GetReference()+': incorrect SMA slot datum or direction')
  long=[]
  for q in f.Pads():
   box=q.GetBoundingBox();corners=[box.GetOrigin(),p.VECTOR2I(box.GetRight(),box.GetTop()),p.VECTOR2I(box.GetRight(),box.GetBottom()),p.VECTOR2I(box.GetLeft(),box.GetBottom())]
   if any(not outline.Contains(v,-1,p.FromMM(.000002)) for v in corners):raise ValueError(f.GetReference()+': pad copper extends outside the board')
   if q.GetAttribute()==p.PAD_ATTRIB_SMD and abs(q.GetSize().x/1e6-5.08)<.000001:
    if abs(box.GetTop()/1e6-20)>.000002:raise ValueError(f.GetReference()+': edge land is not aligned to the board edge')
    long.append(dict(pad=q.GetNumber(),size_mm=[q.GetSize().x/1e6,q.GetSize().y/1e6],bounds_mm=[box.GetLeft()/1e6,box.GetTop()/1e6,box.GetRight()/1e6,box.GetBottom()/1e6]))
  if len(long)!=5:raise ValueError(f.GetReference()+': expected complete RF and four ground SMD lands')
  rows.append(dict(reference=f.GetReference(),origin_mm=[f.GetPosition().x/1e6,f.GetPosition().y/1e6],rotation_degrees=270,long_lands=long))
 if len(rows)!=2:raise ValueError('expected two SMA connectors')
 return dict(board_thickness_mm=1.6,slot_stop_local_x_mm=-4.26,board_edge_y_mm=20,land_length_mm=5.08,connectors=rows)
if __name__=='__main__':print(json.dumps(check(sys.argv[1]),indent=2))
