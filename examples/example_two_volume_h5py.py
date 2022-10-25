import numpy as np
import h5py

print('started')
vertices = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
)

vertices = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 1.0],
    ]
)

triangle_groups = [
    np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
    np.array([[1, 2, 3], [1, 3, 4], [3, 5, 2], [1, 2, 4], [2, 4, 5], [3, 5, 4]]),
]
f = h5py.File("h5py_two_volumes.h5m", "w")

all_triangles = np.vstack(triangle_groups)


tstt = f.create_group("tstt")

elements = tstt.create_group("elements")

global_id = (
    1  # not sure if this is need, appears to count both triangles and coordinates
)
mesh_type = "Tri3"
mesh_name = 2

elem_dt = h5py.special_dtype(
    enum=(
        "i",
        {
            # "Edge": 1,
            "Tri": 2,
            # "Quad": 3,
            # "Polygon": 4,
            # "Tet": 5,
            # "Pyramid": 6,
            # "Prism": 7,
            # "Knife": 8,
            # "Hex": 9,
            # "Polyhedron": 10,
        },
    )
)

# for triangles in triangle_groups:

elem_group = elements.create_group(mesh_type)
elem_group.attrs.create("element_type", mesh_name, dtype=elem_dt)

# compression="gzip"
# compression_opts=4 #meshio defaults
conn = elem_group.create_dataset(
    "connectivity",
    data=all_triangles + 1,  # node indices are 1 based in h5m
    # compression=compression,
    # compression_opts=compression_opts,
)

conn.attrs.create("start_id", global_id)
global_id += len(all_triangles)

key = "materials"
tags = elem_group.create_group("tags")
tags.create_dataset(
    key,
    data=[0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
    # compression=compression,
    # compression_opts=compression_opts,
)


nodes = tstt.create_group("nodes")

coords = nodes.create_dataset("coordinates", data=vertices)
coords.attrs.create("start_id", global_id)
global_id += len(vertices)

sets = tstt.create_group("sets")

tags = tstt.create_group("tags")

print('finished')