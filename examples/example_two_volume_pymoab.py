import numpy as np
import os
from vertices_to_h5m import vertices_to_h5m


vertices = np.array(
    [
        [0.42, 0.42, 0.42],
        [1.42, 0.42, 0.42],
        [0.42, 1.42, 0.42],
        [0.42, 0.42, 1.42],
        [1.42, 0.42, 1.42],
        [0.42, 1.42, 1.42],
    ]
)

triangle_groups = [
    np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
    np.array([[1, 2, 3], [1, 3, 4], [3, 5, 2], [1, 2, 4], [2, 4, 5], [3, 5, 4]]),
]

vertices_to_h5m(
    vertices=vertices,
    triangle_groups=triangle_groups,
    material_tags=["mat1", "mat2"],
    h5m_filename="pymoab_two_volumes.h5m",
)

os.system("mbconvert pymoab_two_volumes.h5m pymoab_two_volumes.vtk")
