# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.


from setuptools import setup, find_packages
import re

setup(
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        ],
    description="Library for accessing computer vision training data in Limbo Data Format.",
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
    project_urls={
        "Chat": "https://github.com/limbo-ml/user/discussions",
        "Coverage": "https://coveralls.io/r/limbo-ml/user",
        "Documentation": "http://limbo-ml.readthedocs.io/",
        "Issue Tracker": "http://github.com/limbo-ml/user/issues",
        "Regression Tests": "http://github.com/limbo-ml/user/actions",
        "Source": "http://github.com/limbo-ml/user",
    },
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
