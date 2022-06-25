
[![N|Python](https://www.python.org/static/community_logos/python-powered-w-100x40.png)](https://www.python.org)

[![CI with install](https://github.com/fusion-energy/stl_to_h5m/actions/workflows/ci_with_install.yml/badge.svg)](https://github.com/fusion-energy/stl_to_h5m/actions/workflows/ci_with_install.yml)

[![Upload Python Package](https://github.com/fusion-energy/stl_to_h5m/actions/workflows/python-publish.yml/badge.svg)](https://github.com/fusion-energy/stl_to_h5m/actions/workflows/python-publish.yml)
[![anaconda-publish](https://github.com/fusion-energy/stl_to_h5m/actions/workflows/anaconda-publish.yml/badge.svg)](https://github.com/fusion-energy/stl_to_h5m/actions/workflows/anaconda-publish.yml)

[![conda-publish](https://anaconda.org/fusion-energy/stl_to_h5m/badges/version.svg)](https://anaconda.org/fusion-energy/stl_to_h5m)
[![PyPI](https://img.shields.io/pypi/v/stl-to-h5m?color=brightgreen&label=pypi&logo=grebrightgreenen&logoColor=green)](https://pypi.org/project/stl_to_h5m/)

This is a minimal Python package that provides a Python API interfaces for converting multiple STL files into a DAGMC h5m file ready for use in simulation.

Convert STL files to a DAGMC h5m file complete with material tags and ready for use neutronics simulations.

**warning** this approach does not imprint and merge the geometry and therefore
requires that the STL files do not overlap. Overlaps could lead to particles
being lost during transport. If imprinting and merging is required consider
using [Paramak export_dagmc_h5m()](https://paramak.readthedocs.io/en/main/)
method or [cad-to-h5m](https://github.com/fusion-energy/cad_to_h5m) to make the
DAGMC geometry.

It is strongly advised to used the DAGMC overlap checker to check the
resulting h5m file (see checking for overlaps section below).


# Installation - Conda

This single line command should install the package and dependencies (including moab)

```bash
conda install -c fusion-energy -c fusion-energy stl_to_h5m
```

# Installation - Pip + Conda

These two commands should install the package and dependencies. Moab requires a separate install as it is not available on ```pip```

```bash
conda install -c conda-forge moab
pip install stl_to_h5m
```

# Usage - single file

To convert a single STL file into a h5m file. This also tags the volume with the
material tag m1.

```python
from stl_to_h5m import stl_to_h5m

stl_to_h5m(
    files_with_tags=[('part1.stl', 'mat1')],
    h5m_filename='dagmc.h5m',
)
```

# Usage - multiple files

To convert multiple STL files into a h5m file. This also tags the relevant 
volumes with material tags called m1 and m2.

```python
from stl_to_h5m import stl_to_h5m

stl_to_h5m(
    files_with_tags=[
        ('part1.stl', 'mat1'),
        ('part2.stl', 'mat2')
    ],
    h5m_filename='dagmc.h5m'
)
```

# Usage - checking for overlaps

To check for overlaps in the resulting h5m file one can use the DAGMC
overlap checker. -p is the number of points to check on each line

```bash
conda install -c conda-forge
overlap_check dagmc.h5m -p 1000
```

# Acknowledgments

This package is largely based on [a script](https://gist.github.com/pshriwise/52452c37d4b7dd89bdc9374e13c35157) by @pshriwise
