# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.


from setuptools import setup, find_packages
import re

setup(
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        ],
    description="Synthetic images for training machine learning models.",
    install_requires=[
        "imagecat",
        "numpy",
        "skia-python",
        ],
    maintainer="Timothy M. Shead",
    maintainer_email="tshead@sandia.gov",
    name="limbo-ml",
    packages=find_packages(),
    package_data = {"": ["*.csv"]},
    scripts=[
        "bin/limbo-materialize",
        "bin/limbo-stats",
        ],
    version=re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        open(
            "limbo/__init__.py",
            "r").read(),
        re.M).group(1),
)
