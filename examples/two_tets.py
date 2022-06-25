import numpy as np
from vertices_to_h5m import vertices_to_h5m
from pathlib import Path
import trimesh

vertices = np.array(
    [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [1, 1, 0]], dtype="float64"
)


triangles = [
    np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
    np.array([[4, 5, 1], [4, 5, 2], [4, 1, 2], [5,1,2]]),
]

vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=["mat1", "mat2"],
    h5m_filename="double_tet.h5m",
)

import os

os.system("mbconvert double_tet.h5m double_tet.vtk")
