from vertices_to_h5m import vertices_to_h5m
import numpy as np
import os

# These are the x,y,z coordinates of each vertex.
# The first 4 are used in the first volume
vertices = np.array(
    [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [1, 1, 0]], dtype="float64"
)

# These are the two sets triangle that connect individual vertices together to form a continious surfaces and also two closed volume.
triangles = [
    np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
    np.array([[4, 5, 1], [4, 5, 2], [4, 1, 2], [5, 1, 2]]),
]

# This will produce a h5m file called two_volume_touching_edge.h5m ready for use with DAGMC enabled codes
vertices_to_h5m(
    vertices=vertices,
    triangles=triangles,
    material_tags=["mat1", "mat2"],
    h5m_filename="two_volume_touching_edge.h5m",
)

os.system("mbconvert two_volume_touching_edge.h5m two_volume_touching_edge.vtk")
