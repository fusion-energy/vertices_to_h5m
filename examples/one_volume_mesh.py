from vertices_to_h5m import vertices_to_h5m
import numpy as np

vertices = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
)


triangles = [
    np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
]

vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=["mat1"],
    h5m_filename="one_volume.h5m",
)

import os

os.system("mbconvert one_volume.h5m one_volume.vtk")
