import numpy as np
import h5py

vertices = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]
)


triangles = np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]])

f = h5py.File("one_volume.h5m", "w")

tstt = f.create_group("tstt")

elements = tstt.create_group("elements")

global_id = 1  # not sure if this is need, appears to count both triangles and coordinates
mesh_type = "Tri3"
mesh_name = 2

elem_dt = h5py.special_dtype(
    enum=(
        "i",
        {
            "Edge": 1,
            "Tri": 2,
            "Quad": 3,
            "Polygon": 4,
            "Tet": 5,
            "Pyramid": 6,
            "Prism": 7,
            "Knife": 8,
            "Hex": 9,
            "Polyhedron": 10,
        },
    )
)

my_group = elements.create_group(mesh_type)
my_group.attrs.create("element_type", mesh_name, dtype=elem_dt)

# compression="gzip"
# compression_opts=4 #meshio defaults
conn = my_group.create_dataset(
    "connectivity",
    data=triangles+1, # node indices are 1 based in h5m
    # compression=compression,
    # compression_opts=compression_opts,
)

conn.attrs.create("start_id", global_id)
global_id += len(triangles)

nodes = tstt.create_group("nodes")

coords = nodes.create_dataset("coordinates", data=vertices)
coords.attrs.create("start_id", global_id)
global_id += len(vertices)

sets = tstt.create_group("sets")

tags = tstt.create_group("tags")