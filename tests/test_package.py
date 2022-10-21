import numpy as np
from vertices_to_h5m import vertices_to_h5m
from pathlib import Path
import dagmc_h5m_file_inspector as di
import openmc
import openmc_data_downloader as odd
import pytest


"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
    - h5m files can be used a transport geometry in DAGMC with OpenMC 
"""


def transport_particles_on_h5m_geometry(
    h5m_filename, material_tags, cross_sections_xml=None
):
    """A function for testing the geometry file with particle transport in DAGMC OpenMC"""

    materials = openmc.Materials()
    for material_tag in material_tags:

        # simplified material definitions have been used to keen this example minimal
        mat_dag_material_tag = openmc.Material(name=material_tag)
        mat_dag_material_tag.add_element("H", 1, "ao")
        mat_dag_material_tag.set_density("g/cm3", 2)

        materials.append(mat_dag_material_tag)

    if cross_sections_xml:
        materials.cross_sections = cross_sections_xml
    # downloads the nuclear data and sets the openmc_cross_sections environmental variable
    odd.just_in_time_library_generator(libraries="ENDFB-7.1-NNDC", materials=materials)

    # makes use of the dagmc geometry
    dag_univ = openmc.DAGMCUniverse(h5m_filename)

    # creates an edge of universe boundary surface
    vac_surf = openmc.Sphere(r=10000, surface_id=9999, boundary_type="vacuum")

    # specifies the region as below the universe boundary
    region = -vac_surf

    # creates a cell from the region and fills the cell with the dagmc geometry
    containing_cell = openmc.Cell(cell_id=9999, region=region, fill=dag_univ)

    geometry = openmc.Geometry(root=[containing_cell])

    # initialises a new source object
    my_source = openmc.Source()
    # sets the location of the source to x=0.1 y=0.1 z=0.1 which is not on a vertex
    my_source.space = openmc.stats.Point((0.1, 0.1, 0.1))
    # sets the direction to isotropic
    my_source.angle = openmc.stats.Isotropic()
    # sets the energy distribution to 100% 14MeV neutrons
    my_source.energy = openmc.stats.Discrete([14e6], [1])

    # specifies the simulation computational intensity
    settings = openmc.Settings()
    settings.batches = 10
    settings.particles = 10000
    settings.inactive = 0
    settings.run_mode = "fixed source"
    settings.source = my_source

    # adds a tally to record the heat deposited in entire geometry
    cell_tally = openmc.Tally(name="flux")
    cell_tally.scores = ["flux"]

    # creates a mesh that covers the geometry
    mesh = openmc.RegularMesh()
    mesh.dimension = [100, 100, 100]
    mesh.lower_left = [
        -10,
        -10,
        -10,
    ]  # x,y,z coordinates start at 0 as this is a sector model
    mesh.upper_right = [10, 10, 10]

    # makes a mesh tally using the previously created mesh and records flux on the mesh
    mesh_tally = openmc.Tally(name="flux_on_mesh")
    mesh_filter = openmc.MeshFilter(mesh)
    mesh_tally.filters = [mesh_filter]
    mesh_tally.scores = ["flux"]

    # groups the two tallies
    tallies = openmc.Tallies([cell_tally, mesh_tally])

    # builds the openmc model
    my_model = openmc.Model(
        materials=materials, geometry=geometry, settings=settings, tallies=tallies
    )

    # starts the simulation
    sp_filename = my_model.run()

    sp = openmc.StatePoint(sp_filename)

    # access the tally
    tally = sp.get_tally(name="flux")

    df = tally.get_pandas_dataframe()

    flux_tally_result = df["mean"].sum()

    return flux_tally_result


def test_h5m_production_with_single_volume_list():
    """The simplest geometry, a single 4 sided shape with lists instead of np arrays"""

    test_h5m_filename = "single_tet.h5m"

    # a list of xyz coordinates
    vertices = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangle_groups = [[[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]]

    for method in ["pymoab", "h5py"]:
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1"],
            h5m_filename=test_h5m_filename,
            method=method,
        )

        flux_value = transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1"],
        )
        assert flux_value == pytest.approx(9994.523679063743)
        assert Path(test_h5m_filename).is_file()
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1]
        assert di.get_materials_from_h5m(test_h5m_filename) == ["mat1"]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {1: "mat1"}


def test_h5m_production_with_single_volume_numpy():
    """The simplest geometry, a single 4 sided shape"""

    test_h5m_filename = "single_tet.h5m"

    # a list of xyz coordinates
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype="float64",
    )

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangle_groups = [np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]])]

    for method in ["pymoab", "h5py"]:
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1"],
            h5m_filename=test_h5m_filename,
            method=method,
        )

        flux_value = transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1"],
        )

        assert flux_value == pytest.approx(9994.523679063743)
        assert Path(test_h5m_filename).is_file()
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1]
        assert di.get_materials_from_h5m(test_h5m_filename) == ["mat1"]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {1: "mat1"}


def test_h5m_production_with_two_touching_edges_numpy():
    """Two 4 sided shapes that share and edge"""

    test_h5m_filename = "double_tet.h5m"

    # a list of xyz coordinates
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [1.0, 1.0, 0.0],
        ],
        dtype="float64",
    )

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangle_groups = [
        np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
        np.array([[4, 5, 1], [4, 5, 2], [4, 1, 2], [5, 1, 2]]),
    ]

    for method in ["pymoab", "h5py"]:
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1", "mat2"],
            h5m_filename=test_h5m_filename,
            method=method,
        )

        flux_value = transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1", "mat2"],
        )

        assert flux_value == pytest.approx(9992.03209797692)
        assert Path(test_h5m_filename).is_file()
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1, 2]
        assert di.get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat1",
            2: "mat2",
        }


def test_h5m_production_with_two_touching_edges_lists():
    """Two 4 sided shapes that share and edge"""

    test_h5m_filename = "double_tet.h5m"

    # a list of xyz coordinates
    vertices = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.0, 0.0],
    ]

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangle_groups = [
        [[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]],
        [[4, 5, 1], [4, 5, 2], [4, 1, 2], [5, 1, 2]],
    ]

    for method in ["pymoab", "h5py"]:
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1", "mat2"],
            h5m_filename=test_h5m_filename,
            method=method,
        )

        flux_value = transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1", "mat2"],
        )

        assert flux_value == pytest.approx(9992.03209797692)
        assert Path(test_h5m_filename).is_file()
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1, 2]
        assert di.get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat1",
            2: "mat2",
        }


def test_h5m_production_with_two_touching_vertex_numpy():
    """Two 4 sided shapes that share an single vertex"""

    test_h5m_filename = "touching_vertex_tets.h5m"

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
    triangle_groups = [
        np.array([[0, 4, 5], [6, 4, 5], [0, 5, 6], [0, 4, 6]]),
        np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
    ]

    for method in ["pymoab", "h5py"]:
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1", "mat2"],
            h5m_filename=test_h5m_filename,
            method=method,
        )

        flux_value = transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1", "mat2"],
        )

        assert flux_value == pytest.approx(9992.93026368412)
        assert Path(test_h5m_filename).is_file()
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1, 2]
        assert di.get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat1",
            2: "mat2",
        }


def test_h5m_production_with_two_touching_vertex_list():
    """Two 4 sided shapes that share an single vertex"""

    test_h5m_filename = "touching_vertex_tets.h5m"

    vertices = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [-1.0, 0.0, 0.0],
        [0.0, -1.0, 0.0],
        [0.0, 0.0, -1.0],
    ]

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangle_groups = [
        [[0, 4, 5], [6, 4, 5], [0, 5, 6], [0, 4, 6]],
        [[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]],
    ]
    for method in ["pymoab", "h5py"]:
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1", "mat2"],
            h5m_filename=test_h5m_filename,
            method=method,
        )

        flux_value = transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1", "mat2"],
        )

        assert flux_value == pytest.approx(9992.93026368412)
        assert Path(test_h5m_filename).is_file()
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1, 2]
        assert di.get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat1",
            2: "mat2",
        }


def test_h5m_production_with_two_touching_face_numpy():
    """Two 4 sided shapes that share a face"""

    test_h5m_filename = "double_tet_touching_face.h5m"

    # a list of xyz coordinates
    vertices = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype="float64",
    )

    # the index of the coordinate that make up the corner of a tet, normals need fixing
    triangle_groups = [
        np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
        np.array([[1, 2, 3], [1, 3, 4], [3, 5, 2], [1, 2, 4], [2, 4, 5], [3, 5, 4]]),
    ]
    for method in ["pymoab", "h5py"]:
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1", "mat2"],
            h5m_filename=test_h5m_filename,
            method=method,
        )

        flux_value = transport_particles_on_h5m_geometry(
            h5m_filename=test_h5m_filename,
            material_tags=["mat1", "mat2"],
        )

        assert flux_value == pytest.approx(9972.750052518444)
        assert Path(test_h5m_filename).is_file()
        assert di.get_volumes_from_h5m(test_h5m_filename) == [1, 2]
        assert di.get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
        assert di.get_volumes_and_materials_from_h5m(test_h5m_filename) == {
            1: "mat1",
            2: "mat2",
        }
