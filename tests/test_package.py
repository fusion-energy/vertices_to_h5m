from pathlib import Path

import numpy as np
import openmc
import openmc_data_downloader as odd
import pytest

try:
    import dagmc_h5m_file_inspector as di
except Exception:  # pragma: no cover - optional dependency
    di = None

try:
    import pymoab  # noqa: F401

    _HAS_PYMOAB = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_PYMOAB = False

try:
    import h5py  # noqa: F401

    _HAS_H5PY = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_H5PY = False

from vertices_to_h5m import vertices_to_h5m

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
    - h5m files can be used a transport geometry in DAGMC with OpenMC 
"""


def _decode_opaque(value):
    raw = value.tobytes() if hasattr(value, "tobytes") else bytes(value)
    return raw.split(b"\x00", 1)[0].decode("ascii")


def _h5py_read_volumes_and_materials(filename):
    if not _HAS_H5PY:
        raise ImportError("h5py is required to read h5m files without pymoab.")

    import h5py

    with h5py.File(filename, "r") as f:
        tstt = f["tstt"]
        sets = tstt["sets"]

        start_id = int(sets["list"].attrs["start_id"])
        global_ids = sets["tags"]["GLOBAL_ID"][:]
        handle_to_gid = {
            start_id + i: int(global_ids[i]) for i in range(len(global_ids))
        }

        cat = tstt["tags"]["CATEGORY"]
        cat_handles = [int(x) for x in cat["id_list"][:]]
        cat_values = [_decode_opaque(v) for v in cat["values"][:]]
        volume_handles = [h for h, v in zip(cat_handles, cat_values) if v == "Volume"]

        name = tstt["tags"]["NAME"]
        group_pairs = sorted(
            [
                (int(h), _decode_opaque(v))
                for h, v in zip(name["id_list"][:], name["values"][:])
            ],
            key=lambda pair: pair[0],
        )
        materials = [
            val.split("mat:", 1)[1] if val.startswith("mat:") else val
            for _, val in group_pairs
        ]

        volume_ids = [handle_to_gid[h] for h in sorted(volume_handles)]
        mapping = {
            volume_ids[i]: materials[i]
            for i in range(min(len(volume_ids), len(materials)))
        }

        return volume_ids, materials, mapping


def get_volumes_from_h5m(filename):
    if di is not None:
        return di.get_volumes_from_h5m(filename)
    volumes, _, _ = _h5py_read_volumes_and_materials(filename)
    return volumes


def get_materials_from_h5m(filename):
    if di is not None:
        return di.get_materials_from_h5m(filename)
    _, materials, _ = _h5py_read_volumes_and_materials(filename)
    return materials


def get_volumes_and_materials_from_h5m(filename):
    if di is not None:
        return di.get_volumes_and_materials_from_h5m(filename)
    _, _, mapping = _h5py_read_volumes_and_materials(filename)
    return mapping


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

    # Download nuclear data and set OPENMC_CROSS_SECTIONS (API differs across versions)
    if hasattr(odd, "just_in_time_library_generator"):
        odd.just_in_time_library_generator(
            libraries="ENDFB-7.1-NNDC", materials=materials
        )
    elif hasattr(odd, "download_cross_section_data"):
        odd.download_cross_section_data(
            materials=materials,
            libraries=["ENDFB-7.1-NNDC"],
            particles=["neutron"],
            set_OPENMC_CROSS_SECTIONS=True,
        )
    elif hasattr(materials, "download_cross_section_data"):
        materials.download_cross_section_data(
            libraries=["ENDFB-7.1-NNDC"],
            set_OPENMC_CROSS_SECTIONS=True,
            particles=["neutron"],
        )
    else:
        raise RuntimeError("No compatible cross-section downloader found.")

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

    try:
        flux_tally_result = float(tally.mean.sum())
    except Exception:
        df = tally.get_pandas_dataframe()
        flux_tally_result = df["mean"].sum()

    return flux_tally_result


_METHODS = ["pymoab", "h5py"] if _HAS_PYMOAB else ["h5py"]


@pytest.mark.parametrize("method", _METHODS)
def test_h5m_production_with_single_volume_list(method):
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

    vertices_to_h5m(
        vertices=vertices,
        triangle_groups=triangle_groups,
        material_tags=["mat1"],
        h5m_filename=test_h5m_filename,
        method=method,
    )

    assert Path(test_h5m_filename).is_file()
    assert get_materials_from_h5m(test_h5m_filename) == ["mat1"]
    assert get_volumes_from_h5m(test_h5m_filename) == [1]
    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {1: "mat1"}

    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["mat1"],
    )
    assert flux_value == pytest.approx(9994.523679063743)


@pytest.mark.parametrize("method", _METHODS)
def test_h5m_production_with_single_volume_numpy(method):
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

    vertices_to_h5m(
        vertices=vertices,
        triangle_groups=triangle_groups,
        material_tags=["mat1"],
        h5m_filename=test_h5m_filename,
        method=method,
    )
    assert Path(test_h5m_filename).is_file()
    assert get_volumes_from_h5m(test_h5m_filename) == [1]
    assert get_materials_from_h5m(test_h5m_filename) == ["mat1"]
    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {1: "mat1"}

    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["mat1"],
    )

    assert flux_value == pytest.approx(9994.523679063743)


@pytest.mark.parametrize("method", _METHODS)
def test_h5m_production_with_two_touching_edges_numpy(method):
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

    vertices_to_h5m(
        vertices=vertices,
        triangle_groups=triangle_groups,
        material_tags=["mat1", "mat2"],
        h5m_filename=test_h5m_filename,
        method=method,
    )

    assert Path(test_h5m_filename).is_file()
    assert get_volumes_from_h5m(test_h5m_filename) == [1, 2]
    assert get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat1",
        2: "mat2",
    }
    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["mat1", "mat2"],
    )

    assert flux_value == pytest.approx(9992.03209797692)


@pytest.mark.parametrize("method", _METHODS)
def test_h5m_production_with_two_touching_edges_lists(method):
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

    vertices_to_h5m(
        vertices=vertices,
        triangle_groups=triangle_groups,
        material_tags=["mat1", "mat2"],
        h5m_filename=test_h5m_filename,
        method=method,
    )

    assert Path(test_h5m_filename).is_file()
    assert get_volumes_from_h5m(test_h5m_filename) == [1, 2]
    assert get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat1",
        2: "mat2",
    }
    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["mat1", "mat2"],
    )

    assert flux_value == pytest.approx(9992.03209797692)


@pytest.mark.parametrize("method", _METHODS)
def test_h5m_production_with_two_touching_vertex_numpy(method):
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

    vertices_to_h5m(
        vertices=vertices,
        triangle_groups=triangle_groups,
        material_tags=["mat1", "mat2"],
        h5m_filename=test_h5m_filename,
        method=method,
    )

    assert Path(test_h5m_filename).is_file()
    assert get_volumes_from_h5m(test_h5m_filename) == [1, 2]
    assert get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat1",
        2: "mat2",
    }
    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["mat1", "mat2"],
    )

    assert flux_value == pytest.approx(9992.93026368412)


@pytest.mark.parametrize("method", _METHODS)
def test_h5m_production_with_two_touching_vertex_list(method):
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

    vertices_to_h5m(
        vertices=vertices,
        triangle_groups=triangle_groups,
        material_tags=["mat1", "mat2"],
        h5m_filename=test_h5m_filename,
        method=method,
    )

    assert Path(test_h5m_filename).is_file()
    assert get_volumes_from_h5m(test_h5m_filename) == [1, 2]
    assert get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat1",
        2: "mat2",
    }
    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["mat1", "mat2"],
    )

    assert flux_value == pytest.approx(9992.93026368412)


@pytest.mark.parametrize("method", _METHODS)
def test_h5m_production_with_two_touching_face_numpy(method):
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

    vertices_to_h5m(
        vertices=vertices,
        triangle_groups=triangle_groups,
        material_tags=["mat1", "mat2"],
        h5m_filename=test_h5m_filename,
        method=method,
    )
    assert Path(test_h5m_filename).is_file()
    assert get_volumes_from_h5m(test_h5m_filename) == [1, 2]
    assert get_materials_from_h5m(test_h5m_filename) == ["mat1", "mat2"]
    assert get_volumes_and_materials_from_h5m(test_h5m_filename) == {
        1: "mat1",
        2: "mat2",
    }

    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=test_h5m_filename,
        material_tags=["mat1", "mat2"],
    )

    assert flux_value == pytest.approx(9981.443525722958)
