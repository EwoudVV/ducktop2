"""Shared CAD helpers. Inputs are installed X/Y and height above the base bottom.

Construction uses X, -Y, height. Export rotates 180 degrees about X, giving
the right-handed assembly frame X, Y, Z with +Z down and height = -Z.
No imported part is mirrored. STEP and schedules use the assembly frame.
"""
from pathlib import Path
import json
import cadquery as cq

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def box(x, y, h, w, d, t):
    return cq.Solid.makeBox(w, d, t, cq.Vector(x, -y-d, h))


def cylinder(x, y, h, r, t):
    return cq.Solid.makeCylinder(r, t, cq.Vector(x, -y, h))


def compound(shapes):
    return cq.Compound.makeCompound(list(shapes))


def drilling(shape, points, diameter, h, depth):
    for x, y in points:
        shape = shape.cut(cylinder(x, y, h, diameter/2, depth))
    return shape


def export_step(shape, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shape.rotate((0,0,0),(1,0,0),180), str(path))


def export_stl(shape, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Print files sit on Z=0 in a conventional build-plate frame.
    bb = shape.BoundingBox()
    cq.exporters.export(shape.translate((-bb.xmin,-bb.ymin,-bb.zmin)), str(path),
                        tolerance=.035, angularTolerance=.12)


def bounds(shape):
    bb=shape.BoundingBox()
    return [round(getattr(bb,k),6) for k in ['xmin','ymin','zmin','xmax','ymax','zmax']]


def render(parts, path, title, direction=(1,-1,1), size=(1600,1100), focus=None):
    """Render tessellated BReps using VTK, with parallel projection."""
    import vtk
    renderer=vtk.vtkRenderer()
    renderer.SetBackground(.94,.95,.96)
    for item in parts:
        shape, color = item['shape'], item.get('color',(.6,.65,.7))
        vertices, triangles=shape.tessellate(.10,.15)
        points=vtk.vtkPoints()
        for p in vertices: points.InsertNextPoint(*p.toTuple())
        cells=vtk.vtkCellArray()
        for tri in triangles:
            cells.InsertNextCell(3)
            for i in tri: cells.InsertCellPoint(i)
        poly=vtk.vtkPolyData(); poly.SetPoints(points); poly.SetPolys(cells)
        normals=vtk.vtkPolyDataNormals(); normals.SetInputData(poly); normals.SetFeatureAngle(35)
        mapper=vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
        actor=vtk.vtkActor(); actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color[:3])
        actor.GetProperty().SetOpacity(color[3] if len(color)>3 else 1)
        actor.GetProperty().SetSpecular(.2); actor.GetProperty().SetSpecularPower(25)
        renderer.AddActor(actor)
    camera=renderer.GetActiveCamera(); camera.ParallelProjectionOn()
    camera.SetPosition(*direction); camera.SetFocalPoint(0,0,0)
    camera.SetViewUp(0,0,1) if abs(direction[2])<.99 or abs(direction[0])+abs(direction[1])>.1 else camera.SetViewUp(0,1,0)
    renderer.ResetCamera()
    if focus:
        target, scale=focus
        camera.SetFocalPoint(*target)
        camera.SetPosition(*[target[i]+direction[i]*500 for i in range(3)])
        camera.SetParallelScale(scale)
    label=vtk.vtkTextActor(); label.SetInput(title)
    label.GetTextProperty().SetFontSize(24); label.GetTextProperty().SetColor(.1,.15,.18)
    label.SetDisplayPosition(24,size[1]-42); renderer.AddActor2D(label)
    window=vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(*size)
    window.AddRenderer(renderer); window.SetMultiSamples(4); window.Render()
    shot=vtk.vtkWindowToImageFilter(); shot.SetInput(window); shot.Update()
    out=vtk.vtkPNGWriter(); out.SetFileName(str(path)); out.SetInputConnection(shot.GetOutputPort()); out.Write()
    window.Finalize()
