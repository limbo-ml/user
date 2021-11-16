.. _specification:

Limbo Data Format
=================

We created the Limbo Data Format to organize and annotate the hybrid synthetic
training data that we create for our machine learning research.

You may be wondering why we created yet another format for storing computer
vision training data ... why not COCO or VOC?  We seriously considered these
and other formats for our work, but found that they all lacked features that
we needed, features like the following:

* Storing multiple layers (images) per sample - our synthetic data includes both visible spectrum and depth information, and existing formats didn't provide a way to logically group together related images for this purpose.
* Storing antialiased masks - our synthetic data includes subpixel coverage information for those that need it, while existing formats assume that masks are boolean.
* Storing high-dynamic-range images - our synthetic images record floating-point absolute intensity value pixels, instead of the highly-quantized integer pixels of current formats.

Many of these features are stored in a highly compressed form, in file formats
that aren't widely used in the machine learning community.  The Limbo software
provides an API to simplify extracting just the information you need to use
Limbo data in your research.  In the sections that follow, we will describe how
the data is organized.

Terminology
-----------

Here are some terms that we use throughout the documentation, and what we mean
when we use them.

Annotation
    Generic term for any ground-truth applied to a *sample*; *bounding boxes*,
    *contours*, and *tags* are specific types of annotation.

Bounding Box
    Specific type of *annotation* that applies a *category* to a rectangular
    region of an image; the ground truth for *object detection*.

Category
	An arbitrary (but not empty) string label.

Contour
    Specific type of *annotation* that applies a *category* to an arbitrary
    region of an image, bounded by a set of one-or-more 2D polygons; the ground
    truth for *object segmentation*.

Dataset
    A dataset is a collection of *samples*.

Metadata
    The metadata for a *sample* is an arbitrary JSON data structure which
    contains provenance, *annotations*, and references to the sample
    images.

Sample
    We refer to each of our observations as a *sample*.  Every sample includes
    arbitrary *metadata*, which may include *annotations*, and a collection of
    one-to-many images.

Tag
    Specific type of *annotation* that applies a *category* to an entire image;
    the ground truth for *classification*.

Specification
-------------

A Limbo dataset is a collection of metadata files in JSON format, each
containing the metadata for a single sample.  The metadata filenames *must* end
with ".json", but the remainder of the filename is arbitrary.  Metadata files
can be organized in arbitrary hierarchies on disk, but those hierachies carry
no meaning and the Limbo software will treat the dataset as a flat collection
of samples.

For each sample, image data is stored in separate files.  The image filenames
are arbitrary, but each image file *must* be located in the same directory as
the corresponding metadata file.
