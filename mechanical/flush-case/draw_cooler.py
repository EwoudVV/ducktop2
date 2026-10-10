#!/usr/bin/env python3
"""Render the checked cooler and export its separate inspection assembly."""
import hashlib
import json
from pathlib import Path

import cadquery as cq
import check_cooler
from cad import box, export_step, compound, _MESHES, mesh

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def render(parts,path,title,direction,size,focus=None):
    """Frame close-ups without leaving the clipping planes at the old camera."""
    import vtk
    scene=vtk.vtkRenderer();scene.SetBackground(.94,.95,.96)
    for p in parts:
        vertices,triangles=mesh(p['shape']);points=vtk.vtkPoints();cells=vtk.vtkCellArray()
        for v in vertices:points.InsertNextPoint(*v.toTuple())
        for tri in triangles:
            cells.InsertNextCell(3)
            for i in tri:cells.InsertCellPoint(i)
        poly=vtk.vtkPolyData();poly.SetPoints(points);poly.SetPolys(cells)
        normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly);normals.SetFeatureAngle(35)
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
        actor=vtk.vtkActor();actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*p['color'][:3]);actor.GetProperty().SetSpecular(.2)
        scene.AddActor(actor)
    camera=scene.GetActiveCamera();camera.ParallelProjectionOn();camera.SetViewUp(0,0,1)
    camera.SetPosition(*direction);camera.SetFocalPoint(0,0,0)
    scene.ResetCamera()
    if focus:
        target,scale=focus;camera.SetFocalPoint(*target)
        camera.SetPosition(*[target[i]+direction[i]*500 for i in range(3)])
        camera.SetParallelScale(scale)
    scene.ResetCameraClippingRange()
    label=vtk.vtkTextActor();label.SetInput(title);label.SetPosition(20,size[1]-42)
    prop=label.GetTextProperty();prop.SetFontSize(24);prop.SetColor(.1,.15,.18)
    prop.SetBackgroundColor(.94,.95,.96);prop.SetBackgroundOpacity(.92)
    scene.AddActor2D(label)
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetSize(*size);window.AddRenderer(scene)
    window.Render()
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.SetInputBufferTypeToRGB();capture.ReadFrontBufferOff();capture.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(path));writer.SetInputConnection(capture.GetOutputPort());writer.Write();window.Finalize()


def main():
    parts,case,sources=check_cooler.load_case()
    result=json.loads((HERE/'cooler-checks.json').read_text())
    assert result['nominal_geometry_pass'],'cooler checks are not clear'
    for path,value in result['source_hashes'].items():assert sha(ROOT/path)==value,path
    # Reuse only a viewer built from these exact geometry sources.
    html=(HERE/'inspection.html').read_text();start=html.index('const DATA=')+len('const DATA=')
    viewer,_=json.JSONDecoder().raw_decode(html[start:])
    assert viewer.get('source_hashes')==sources,'viewer does not match the checked CAD'
    by_name={p['name']:p for p in viewer['parts']}
    assert set(by_name)=={p['name'] for p in parts}
    for p in parts:
        mesh=by_name[p['name']]
        _MESHES[id(p['shape'])]=(p['shape'],([cq.Vector(*v) for v in mesh['v']],mesh['f']))
    physical=[p for p in parts if p.get('remote_cooler') and p['group']=='cooling']
    nearby=[p for p in parts if not p.get('moving') and p['group'] in ['boards','wiring'] and not p['name'].startswith('keyboard')]
    render(nearby+physical,HERE/'views/remote-cooler.png','right-side cooler / existing board outlines retained',direction=(.15,-.3,1.6),size=(1700,1100),focus=((272,-102,11),111))
    render(physical,HERE/'views/remote-cooler-parts.png','stepped copper plate / two uncut 250 mm pipes / separate blower',direction=(1,-1,1.5),size=(1700,1100))
    render(nearby+physical,HERE/'views/pipe-wire-clearance.png','heatpipes above the lowered USB power guides',direction=(.1,-1,.65),size=(1550,1050),focus=((277,-96,15),32))
    crop=box(181,8,10,60,75,13);contact=[]
    for p in physical:
        s=p['shape'].intersect(crop)
        if s.Volume()>.001:contact.append({**p,'shape':s})
    render(contact,HERE/'views/cooler-contact.png','contact plate underside / prototype gaps / clamp hardware unfinished',direction=(-1,.5,-1.5),size=(1450,1050))
    local=box(294,115,-.1,70,70,24);hardware=[]
    base=next(p for p in parts if p['name']=='base-floor')
    hardware.append({**base,'shape':base['shape'].intersect(local)})
    for p in physical:
        s=p['shape'].intersect(local)
        if s.Volume()>.001:hardware.append({**p,'shape':s})
    exploded=[]
    for p in hardware:
        s=p['shape']
        if p['name']=='delta-blower' or p['name'].startswith(('fan-screw-','fan-washer-')):
            s=s.translate((0,0,12))
        exploded.append({**p,'shape':s})
    render(exploded,HERE/'views/cooler-mounts.png','fan lifted 12 mm for inspection / separate spacers / retained fin duct',direction=(.75,-1,1.15),size=(1650,1200))
    half=box(294,115,-.1,70,35.2,24);section=[]
    for p in hardware:
        s=p['shape'].intersect(half)
        if s.Volume()>.001:section.append({**p,'shape':s})
    render(section,HERE/'views/cooler-air-path.png','section through the bottom inlet and side exhaust / prototype seals',direction=(.08,-1,.24),size=(1700,1050))
    render(hardware,HERE/'views/cooler-intake.png','base intake grille / two fin screws accessible from underneath',direction=(.35,-.45,-1.4),size=(1500,1100))
    export_step(compound(p['shape'] for p in physical),HERE/'exports/remote-cooler.step')
    reopened=cq.importers.importStep(str(HERE/'exports/remote-cooler.step')).val()
    assert reopened.isValid()
    outputs=['views/remote-cooler.png','views/remote-cooler-parts.png','views/pipe-wire-clearance.png','views/cooler-contact.png','views/cooler-mounts.png','views/cooler-air-path.png','views/cooler-intake.png','exports/remote-cooler.step']
    report={'date':case['date'],'source_hashes':{**result['source_hashes'],str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},
            'outputs':{p:sha(HERE/p) for p in outputs},'STEP_reopens':True,'STEP_solids':len(reopened.Solids()),
            'scope':'actual CAD renders and inspection assembly; not machining or assembly instructions'}
    (HERE/'cooler-exports.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Saved seven cooler views and a reopened STEP assembly.',flush=True)


if __name__=='__main__':main()
