import cadquery as cq
import os
from vertices_to_h5m import vertices_to_h5m

result = cq.Workplane("front").box(2.0, 2.0, 0.5)

vertices, triangles = result.val().tessellate(tolerance=0.1)

vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=["mat1"],
    h5m_filename="one_cadquery_volume.h5m",
)

os.system("mbconvert one_cadquery_volume.h5m one_cadquery_volume.vtk")
