.. _installation:

Installation
============

Limbo
-----

The Limbo dataset and library are built around `OpenEXR <https://github.com/AcademySoftwareFoundation/openexr>`_
images; to use the software, you'll need the OpenEXR library, which can't be installed via
pip.  If you use `Conda <https://docs.conda.io/en/latest/>`_ (which we strongly
recommend), you can install it as follows::

    $ conda install -c conda-forge openexr-python

Once you have OpenEXR, you can install the latest stable version of the Limbo
software and its dependencies with `pip`::

    $ pip install limbo-ml

... once that completes, you'll be ready to use all of Limbo's features.

Documentation
-------------

We assume that you'll normally access this documentation online, but if you
want a local copy on your own computer, do the following:

First, you'll need the `pandoc <https://pandoc.org>`_ universal document
converter, which can't be installed with pip ... if you use `Conda <https://docs.conda.io/en/latest/>`_
(again - strongly recommended), you can install it with the following::

    $ conda install pandoc

Once you have pandoc, install Limbo along with all of the dependencies needed to build the docs::

    $ pip install limbo-ml[doc]

Next, do the following to download a tarball to the current directory
containing all of the Imagecat source code, which includes the documentation::

    $ pip download limbo-ml --no-binary=:all: --no-deps

Now, you can extract the tarball contents and build the documentation (adjust the
following for the version you downloaded)::

    $ tar xzvf limbo-ml-0.2.0.tar.gz
    $ cd limbo-ml-0.2.0/docs
    $ make html

