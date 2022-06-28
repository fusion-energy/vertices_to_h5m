
# A vscode remote container docker image with conda from
# https://hub.docker.com/_/microsoft-vscode-devcontainers
FROM mcr.microsoft.com/vscode/devcontainers/miniconda:0-3

RUN conda install -c conda-forge mamba

# specifying dagmc version so all the examples work and no mpi to reduce complexity
RUN mamba install -c conda-forge -y "openmc=0.13.0=dagmc*nompi*"
