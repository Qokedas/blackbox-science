# Solver image for pxrd-blind-solve. Built offline-capable: every tool is baked in; the container runs with --network none.
# Build context: environment/ (this Dockerfile, TOOLS.md, data/ = solver-visible instances, instruction.md copied in by build script).
FROM mambaorg/micromamba:2.0.5
USER root
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 MPLBACKEND=Agg OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
RUN apt-get update -qq && apt-get install -y --no-install-recommends build-essential gfortran git curl jq ripgrep libgomp1 unzip bzip2 less vim-tiny && rm -rf /var/lib/apt/lists/*
RUN micromamba install -y -n base -c conda-forge python=3.11 numpy scipy matplotlib pandas pymatgen spglib rdkit gemmi pyobjcryst libobjcryst xtb ase networkx scikit-learn pytorch-cpu h5py openbabel diffpy.structure sympy numba lmfit && micromamba clean -a -y
ARG MAMBA_DOCKERFILE_ACTIVATE=1
# GALLOP (GPL-3; CPU only here) without letting pip replace the conda numpy/torch stack
RUN pip install --no-cache-dir --no-deps git+https://github.com/mspillman/gallop.git && pip install --no-cache-dir --no-deps torch-optimizer pytorch-ranger py3dmol mpld3 tqdm
# GSAS-II (self-contained environment under /opt/g2; use /opt/g2/bin/python with PYTHONPATH=/opt/g2/GSAS-II)
RUN curl -sL -o /tmp/g2.sh https://github.com/AdvancedPhotonSource/GSAS-II-buildtools/releases/download/v1.0.1/gsas2main-Latest-Linux-x86_64.sh && bash /tmp/g2.sh -b -p /opt/g2 > /tmp/g2_install.log 2>&1 && rm -f /tmp/g2.sh
RUN /opt/g2/bin/python -c "import sys; sys.path.insert(0,'/opt/g2/GSAS-II'); import GSASII.GSASIIscriptable as G2; print('gsas2 scriptable ok')"
RUN python -c "import numpy, pymatgen, pyobjcryst, rdkit, spglib, gemmi, ase, torch, gallop; print('core ok')" && which xtb
COPY TOOLS.md /app/TOOLS.md
COPY instruction.md /app/instruction.md
COPY data /app/data
RUN mkdir -p /app/results/submission /app/work && chmod -R a+rX /app/data && python -m pip freeze > /app/installed_packages.txt 2>/dev/null; micromamba list > /app/installed_conda.txt 2>/dev/null; true
# the harness starts the container with /bin/sh (no micromamba activation): expose the conda env on PATH
ENV PATH=/opt/conda/bin:/opt/conda/condabin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
WORKDIR /app
CMD ["bash"]
