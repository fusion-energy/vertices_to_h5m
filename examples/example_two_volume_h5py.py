import numpy as np
import h5py
import trimesh

"""
Creates a DAGMC compatible h5m file based on the H%M file format layout can be
found here https://sigma.mcs.anl.gov/moab/h5m-file-format/
"""

print('started')

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

# commented out for now as this just reorders the nodes in a specific order so they point outwards
#
# def fix_normals(vertices, triangles_in_each_volume):
#     fixed_triangles = []
#     for triangles in triangles_in_each_volume:
#         fixed_triangles.append(fix_normal(vertices, triangles))
#     return fixed_triangles
#
# def fix_normal(vertices, triangles):

#     # for triangles in triangles_in_each_volume:
#     mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)

#     mesh.fix_normals()

#     return mesh.faces
#
# triangles = fix_normals(
#     vertices=vertices, triangles_in_each_volume=triangle_groups
# )

f = h5py.File("h5py_two_volumes.h5m", "w")

all_triangles = np.vstack(triangle_groups)


tstt = f.create_group("tstt")

elements = tstt.create_group("elements")

global_id = (
    1  # appears to count both triangles and coordinates
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


tags = elem_group.create_group("tags")
tags.create_dataset(
    "GLOBAL_ID",
    data=[-1]*len(vertices),
    # compression=compression,
    # compression_opts=compression_opts,
)


nodes = tstt.create_group("nodes")
tags = nodes.create_group("tags")
tags.create_dataset(
    "materials",
    data=[-1]*len(vertices),
    # compression=compression,
    # compression_opts=compression_opts,
)

coords = nodes.create_dataset("coordinates", data=vertices)
coords.attrs.create("start_id", global_id)
global_id += len(vertices)

sets = tstt.create_group("sets")
sets.create_dataset(
    "children",
    data=[
        [23,26] # TODO not sure where these numbers come from, automate the production of these numbers
    ]
)
sets.create_dataset(
    "contents",
    data=[
        [ 1, 6, 13, 4, 24, 7, 6, 17, 6, 27, 1, 28]  # TODO not sure where these numbers come from
    ]
)
sets.create_dataset(
    "list",
    data=[
        # TODO make an entry like this, not sure what these numbers are based on
        # {
        # (0,0): 3, -1, 0, 10,
        # (1,0): 3, 0, 0, 2,
        # (2,0): 4, 0, 0, 2,
        # (3,0): 8, 0, 1, 10,
        # (4,0): 8, 1, 1, 2,
        # (5,0): 9, 1, 1, 2,
        # (6,0): 11, 1, 1, 10
        # }
    ]
)
sets.create_dataset(
    "parents",
    data=[
        [ 24, 27]  # TODO not sure where these numbers come from
    ]
)
sets.create_dataset(
    "GLOBAL_ID",
    data=[
        [ 1, 1, -1, 2, 2, -1, -1 ]  # TODO not sure where these numbers come from
    ]
)

tags = tstt.create_group("tags")
cat = tags.create_group("CATEGORY")
cat.create_dataset(
    "values",
    data=[
        # appears to repeat twice as we have two volumes
        # these words appear in hex format with padding in the h5m file
        # for example 53:75:72:66:61:63:65:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
        'Surface', 'Volume', 'Group',
        'Surface', 'Volume', 'Group'
    ]
)

cat = tags.create_group("id_list")
# TODO populate group
cat = tags.create_group("values")
# TODO populate group

# tried these two methods of making a list in the h5m dataset
# metho 1
# arr = np.array(['mat:mat1','mat:mat2'])
# arr=arr.astype(h5py.opaque_dtype(arr.dtype))
# method 2
# binary_blob = b"mat:mat1"
# dset.attrs["attribute_name"] = np.void(binary_blob)
# out = dset.attrs["attribute_name"]

name = tags.create_group("NAME")
name.create_dataset(
    "values",
    # TODO needs padding and nesting as pymoab does it
    data=[np.void(b"mat:mat1"), np.void(b"mat:mat2")]
)


tstt.attrs.create('max_id', global_id)

print("finished")
