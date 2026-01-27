from pathlib import Path

import numpy as np
import openmc
import openmc_data_downloader
import pytest
from vertices_to_h5m import vertices_to_h5m

try:
    import dagmc_h5m_file_inspector as di
except Exception:  # pragma: no cover - optional dependency
    di = None

try:
    import h5py  # noqa: F401

    _HAS_H5PY = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_H5PY = False

try:
    import pymoab  # noqa: F401

    _HAS_PYMOAB = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_PYMOAB = False

"""
Tests that check that:
    - h5m files are created
    - h5m files contain the correct number of volumes
    - h5m files contain the correct material tags
    - h5m files can be used a transport geometry in DAGMC with OpenMC 
"""


@pytest.fixture(scope="module", autouse=True)
def _generate_two_volume_h5m_files():
    vertices = np.array(
        [
            [0.42, 0.42, 0.42],
            [1.42, 0.42, 0.42],
            [0.42, 1.42, 0.42],
            [0.42, 0.42, 1.42],
            [1.42, 0.42, 1.42],
            [0.42, 1.42, 1.42],
        ],
        dtype="float64",
    )

    triangle_groups = [
        np.array([[0, 1, 2], [3, 1, 2], [0, 2, 3], [0, 1, 3]]),
        np.array(
            [
                [1, 2, 3],
                [1, 3, 4],
                [3, 5, 2],
                [1, 2, 4],
                [2, 4, 5],
                [3, 5, 4],
            ]
        ),
    ]

    created = []
    h5py_file = Path("h5py_two_volumes.h5m")
    if not h5py_file.is_file():
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1", "mat2"],
            h5m_filename=str(h5py_file),
            method="h5py",
        )
        created.append(h5py_file)

    pymoab_file = Path("pymoab_two_volumes.h5m")
    if not pymoab_file.is_file():
        method = "pymoab" if _HAS_PYMOAB else "h5py"
        vertices_to_h5m(
            vertices=vertices,
            triangle_groups=triangle_groups,
            material_tags=["mat1", "mat2"],
            h5m_filename=str(pymoab_file),
            method=method,
        )
        created.append(pymoab_file)

    yield

    for path in created:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


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
        volume_handles = [
            h for h, v in zip(cat_handles, cat_values) if v == "Volume"
        ]

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
        mat_dag_material_tag.add_nuclide("H1", 1, "ao")
        mat_dag_material_tag.set_density("g/cm3", 2)

        materials.append(mat_dag_material_tag)

    if cross_sections_xml:
        materials.cross_sections = cross_sections_xml

    # downloads the nuclear data and sets the openmc_cross_sections environmental variable
    if hasattr(openmc_data_downloader, "just_in_time_library_generator"):
        openmc_data_downloader.just_in_time_library_generator(
            libraries="ENDFB-7.1-NNDC", materials=materials
        )
    elif hasattr(openmc_data_downloader, "download_cross_section_data"):
        openmc_data_downloader.download_cross_section_data(
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
    settings.batches = 100
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


@pytest.mark.parametrize("filename", ["h5py_two_volumes.h5m", "pymoab_two_volumes.h5m"])
def test_h5m_files_produced_contain_exspected_tags(filename):
    assert Path(filename).is_file()
    assert get_volumes_from_h5m(filename) == [1, 2]
    assert get_materials_from_h5m(filename) == ["mat1", "mat2"]
    assert get_volumes_and_materials_from_h5m(filename) == {
        1: "mat1",
        2: "mat2",
    }


@pytest.mark.parametrize("filename", ["h5py_two_volumes.h5m", "pymoab_two_volumes.h5m"])
def test_h5m_files_produced_work_in_transport(filename):
    flux_value = transport_particles_on_h5m_geometry(
        h5m_filename=filename,
        material_tags=["mat1", "mat2"],
    )

    assert flux_value == pytest.approx(9998.51084800535)
