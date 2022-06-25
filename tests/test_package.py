import numpy as np
from vertices_to_h5m import vertices_to_h5m
from pathlib import Path

def test_h5m_production_with_single_volume():

    # a list of xyz coordinates
    vertices = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ],
        dtype="float64",
    )

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangles = [np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]])]

    vertices_to_h5m(
        vertices=vertices,
        triangles=triangles,
        material_tags=['mat1'],
        h5m_filename='single_tet.h5m'
    )

    assert Path('single_tet.h5m').is_file()

def test_h5m_production_with_two_touching_volumes():
    # pass
    # a list of xyz coordinates
    vertices = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 1, 1],
            [1, 1, 0],
        ],
        dtype="float64",
    )

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangles = [
        np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
        np.array([[4,5,1], [4,5,2], [4,1,2], [5,1,2]]),
        ]
    
    vertices_to_h5m(
        vertices=vertices,
        triangles=triangles,
        material_tags=['mat1', 'mat2'],
        h5m_filename='double_tet.h5m'
    )

    assert Path('double_tet.h5m').is_file()

def test_h5m_production_with_two_touching_vertex():
    vertices = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [-1, 0, 0],
            [0, -1, 0],
            [0, 0, -1],

        ],
        dtype="float64",
    )

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangles = [
        np.array([[0, 4, 5], [6, 4, 5], [0, 5, 6], [0, 4, 6]]),
        np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
        ]

    vertices_to_h5m(
        vertices=vertices,
        triangles=triangles,
        material_tags=['mat1', 'mat2'],
        h5m_filename='touching_vertex_tets.h5m'
    )

    assert Path('touching_vertex_tets.h5m').is_file()
