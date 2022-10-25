import numpy as np
import h5py
import trimesh

"""
Creates a DAGMC compatible h5m file based on the H%M file format layout can be
found here https://sigma.mcs.anl.gov/moab/h5m-file-format/
"""

print("started")

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


tstt_group = f.create_group("tstt")

group_elements = tstt_group.create_group("elements")

global_id = 1  # appears to count both triangles and coordinates

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

mesh_name = 2
tri3_group = group_elements.create_group("Tri3")
tri3_group.attrs.create("element_type", mesh_name, dtype=elem_dt)

# compression="gzip"
# compression_opts=4 #meshio defaults
connectivity_group = tri3_group.create_dataset(
    "connectivity",
    data=all_triangles + 1,  # node indices are 1 based in h5m
    # compression=compression,
    # compression_opts=compression_opts,
)

connectivity_group.attrs.create("start_id", global_id)
global_id += len(all_triangles)


tags_tri3_group = tri3_group.create_group("tags")
tags_tri3_group.create_dataset(
    "GLOBAL_ID",
    data=[-1] * len(vertices),
    # compression=compression,
    # compression_opts=compression_opts,
)


nodes_group = tstt_group.create_group("nodes")
tags_nodes_group = nodes_group.create_group("tags")
tags_nodes_group.create_dataset(
    "materials",
    data=[-1] * len(vertices),
    # compression=compression,
    # compression_opts=compression_opts,
)

coordinates_group = nodes_group.create_dataset("coordinates", data=vertices)
coordinates_group.attrs.create("start_id", global_id)
global_id += len(vertices)

sets_group = tstt_group.create_group("sets")
sets_group.create_dataset(
    "children",
    data=[
        [
            23,
            26,
        ]  # TODO not sure where these numbers come from, automate the production of these numbers
    ],
)
sets_group.create_dataset(
    "contents",
    data=[
        [
            1,
            6,
            13,
            4,
            24,
            7,
            6,
            17,
            6,
            27,
            1,
            28,
        ]  # TODO not sure where these numbers come from
    ],
)
sets_group.create_dataset(
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
    ],
)
sets_group.create_dataset(
    "parents", data=[[24, 27]]  # TODO not sure where these numbers come from
)
sets_group.create_dataset(
    "GLOBAL_ID",
    data=[[1, 1, -1, 2, 2, -1, -1]],  # TODO not sure where these numbers come from
)


def hex_encode(string_to_encode: str) -> str:
    """encodes a string in hex format and adds : between characters"""
    hex_string = string_to_encode.encode("utf-8").hex()
    deliminated_string = ':'.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
    # TODO pad the string up to the correct number of characters with 00: entries
    return deliminated_string

tags_tstt_group = tstt_group.create_group("tags")
cat = tags_tstt_group.create_group("CATEGORY")
cat.create_dataset(
    "values",
        # appears to repeat twice as we have two volumes
        # these words appear in hex format with padding in the h5m file
        # for example 53:75:72:66:61:63:65:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00
    data=[
        hex_encode("Surface"),
        "Volume",
        "Group",
        "Surface",
        "Volume",
        "Group",
    ],
)

cat = tags_tstt_group.create_group("id_list")
# TODO populate group
cat = tags_tstt_group.create_group("values")
# TODO populate group

# tried these two methods of making a list in the h5m dataset
# metho 1
# arr = np.array(['mat:mat1','mat:mat2'])
# arr=arr.astype(h5py.opaque_dtype(arr.dtype))
# method 2
# binary_blob = b"mat:mat1"
# dset.attrs["attribute_name"] = np.void(binary_blob)
# out = dset.attrs["attribute_name"]

name_group = tags_tstt_group.create_group("NAME")
name_group.create_dataset(
    "values",
    # TODO needs padding and nesting as pymoab does it
    data=[np.void(b"mat:mat1"), np.void(b"mat:mat2")],
)


tstt_group.attrs.create("max_id", global_id)

print("finished")
