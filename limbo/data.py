# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.


"""Functionality for working with :ref:`specification` datasets.
"""

import collections
import glob
import itertools
import json
import logging
import os
import re

import graphcat
import imagecat
import imagecat.color.brewer
import numpy
import skia
import skimage.measure


log = logging.getLogger()


def signed_area(contour):
    """Return the signed area of a contour.

    Parameters
    ----------
    contour: sequence of x,y coordinates, required

    Returns
    -------
    area: :class:`float`
        Signed area of the given closed contour.  Positive
        if the contour coordinates are in counter-clockwise
        order, negative otherwise.
    """
    result = 0
    for index, (x1, y1) in enumerate(contour):
        x2, y2 = contour[(index + 1) % len(contour)]
        result += (x2 - x1) * (y2 + y1)
    return result


def ccw(contour):
    """Return :any:`True` if the given contour is counter-clockwise.

    Parameters
    ----------
    contour: sequence of x,y coordinates, required

    Returns
    -------
    ccw: :class:`bool`
        :any:`True` if the contour coordinates are in counter-clockwise
        order, otherwise :any:`False`.
    """
    return signed_area(contour) > 0


class Cryptomatte(object):
    """Provides access to extra information provided by synthetic samples.

    The :class:`Cryptomatte` has access to high quality masking information
    created for synthetic samples at render time, and can convert that information
    into many different representations, including contours and rectangular
    bounding boxes.

    There is no reason to create an instance of this class yourself, callers
    should obtain instances from the :meth:`Synthetic.cryptomatte` property.
    """
    def __init__(self, sample, synthetic):
        self._sample = sample
        self._synthetic = synthetic


    def bbox(self, instances=None):
        """Compute a bounding box.

        Note that bounding boxes are computed from contour information.

        Parameters
        ----------
        instances: :class:`str`, :class:`list` of :class:`str`, or :any:`None`, optional
            If :any:`None`, computes a bounding box that contains every object
            in the sample.  Otherwise, computes a bounding box that contains
            just the given object instances.

        Returns
        -------
        bbox: (left, top, width, height) tuple
            Returns the bounding box using absolute pixel values.
        """
        if instances is None:
            instances = self.instances
        elif isinstance(instances, str):
            instances = [instances]
        self._sample.graph.set_task("/cryptomatte/mattes", graphcat.constant(instances))
        return self._sample.graph.output("/bbox")


    def contours(self, instances=None):
        """Compute polygon contours.

        Note that contours are computed from matte information.

        Parameters
        ----------
        instances: :class:`str`, :class:`list` of :class:`str`, or :any:`None`, optional
            If :any:`None`, returns contours for every object in the sample.
            Otherwise, returns contours that contain just the given object
            instances.

        Returns
        -------
        contours: :class:`list` of :class:`numpy.ndarray`
            Returns a :math:`N \\times 2` :class:`numpy.ndarray` for each contour,
            containing absolute pixel values.
        """
        if instances is None:
            instances = self.instances
        elif isinstance(instances, str):
            instances = [instances]
        self._sample.graph.set_task("/cryptomatte/mattes", graphcat.constant(instances))
        return self._sample.graph.output("/contours")


    @property
    def image(self):
        """Return the Cryptomatte data for this sample.

        The Cryptomatte for a sample contains masking information
        for every instance.  All mattes, contours, and bounding boxes
        are derived from this information.

        Returns
        -------
        cryptomatte: :class:`imagecat.data.Image`
            Imagecat image containing the Cryptomatte data for this sample.
        """
        return self._sample.graph.output("/load-cryptomatte")


    @property
    def instances(self):
        """Return the set of visible object instances for this sample.

        Note that an instance label can be any string - any semantics
        encoded in instance labels are dataset-specific.

        Returns
        -------
        instances: :class:`list` of :class:`str`
            Unique instance labels for this sample.
        """
        return self._sample.metadata["synthetic"]["cryptomatte"]["manifest"]


    def materialize_bounds(self):
        annotations = [annotation for annotation in self._sample.metadata.get("annotations", [])]
        annotations = [annotation for annotation in annotations if "bbox" not in annotation]
        annotations = [annotation for annotation in annotations if "contours" not in annotation]

        for instance in self.instances:
            category, index = instance.rsplit("/", 1)

            contours = self.contours(instance)
            if contours:
                annotations.append({
                    "category": category,
                    "contours": [contour.tolist() for contour in self.contours(instance)],
                    "contour_mode": "XY_ABS",
                })

                annotations.append({
                    "category": category,
                    "bbox": self.bbox(instance),
                    "bbox_mode": "XYWH_ABS",
                })
        self._sample.update_metadata({"annotations": annotations})


#    def materialize_segmentation(self):
#        segmentation_image = self.segmentation(self.instances)
#
#        segmentation_image_filename = self._sample.name + ".segmentation.png"
#        segmentation_image_path = os.path.join(self._sample.path, segmentation_image_filename)
#        self._sample.graph.set_task("/save-segmentation/path", graphcat.constant(segmentation_image_path))
#        self._sample.graph.update("/save-segmentation")
#
#        updates = {
#            "segmentation-image": {
#                "content-type": "image/png",
#                "res": segmentation_image.layers["M"].res,
#                "filename": segmentation_image_filename,
#                }
#            }
#        self._sample.update_metadata(updates)


    def matte(self, instances=None):
        """Compute matte images.

        Note that mattes are computed from Cryptomatte data, and are subpixel accurate:
        where an object covers a fraction of a pixel's area, the matte will contain a
        value between 0 and 1.

        Parameters
        ----------
        instances: :class:`str`, :class:`list` of :class:`str`, or :any:`None`, optional
            If :any:`None`, returns a matte containing every object in the sample.
            Otherwise, returns a matte that contains just the given object
            instances.

        Returns
        -------
        matte: :class:`imagecat.data.Image`
            Imagecat image containing the given matte.
        """
        if instances is None:
            instances = self.instances
        elif isinstance(instances, str):
            instances = [instances]
        self._sample.graph.set_task("/cryptomatte/mattes", graphcat.constant(instances))
        return self._sample.graph.output("/cryptomatte")


    def preview(self, show_bboxes=False, show_contours=False, instances=None):
        if instances is None:
            instances = self.instances
        elif isinstance(instances, str):
            instances = [instances]

        # Assign a color to each class.
        color = itertools.cycle(imagecat.color.brewer.palette("Set1").colors)
        colors = {}
        categories = {}
        for instance in self.instances:
            category, index = instance.rsplit("/", 1)
            if category not in categories:
                categories[category] = next(color)
            colors[instance] = categories[category]

        # Start drawing.
        res = self._sample.metadata["synthetic"]["image"]["res"]
        surface = skia.Surface(res[0], res[1])
        canvas = surface.getCanvas()
        canvas.clear(skia.Color4f.kWhite)
        font = skia.Font()

        data = self._synthetic.image.layers["C"].data
        data = imagecat.color.linear_to_srgb(data)
        data = numpy.dstack((data, numpy.ones(data.shape[:2], dtype=numpy.float16)))
        image = skia.Image.fromarray(data, colorType=skia.ColorType.kRGBA_F16_ColorType)
        canvas.drawImage(image, left=0, top=0)

        # Draw contours.
        if show_contours:
            for instance in self.instances:
                if instance not in instances:
                    continue

                contours = self.contours(instance)
                if contours:
                    path = skia.Path()
                    for contour in contours:
                        points = [skia.Point(point[0], point[1]) for point in contour]
                        path.addPoly(points, close=True)

                    color = colors[instance]

                    paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 0.2), Style=skia.Paint.kFill_Style)
                    canvas.drawPath(path, paint)
                    paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 1), Style=skia.Paint.kStroke_Style)
                    canvas.drawPath(path, paint)

                    center = numpy.mean(contours[0], axis=0)
                    paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), Style=skia.Paint.kFill_Style)
                    canvas.drawSimpleText(instance, center[0], center[1], font, paint)

        # Draw bounding boxes.
        if show_bboxes:
            for instance in self.instances:
                if instance not in instances:
                    continue

                xywh = self.bbox(instance)
                if not xywh:
                    continue
                rect = skia.Rect.MakeXYWH(*xywh)

                color = colors[instance]

                paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 0.2), Style=skia.Paint.kFill_Style)
                canvas.drawRect(rect, paint)
                paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 1), Style=skia.Paint.kStroke_Style)
                canvas.drawRect(rect, paint)

                paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), Style=skia.Paint.kFill_Style)
                canvas.drawSimpleText(instance, xywh[0] + 5, xywh[1]+xywh[3] - 5, font, paint)

        return surface


    def segmentation(self, instances=None):
        """Compute segmentation images.

        A segmentation image contains a distinct color for each visible instance
        in the image.

        Note that segmentation images are only accurate to a single pixel: each
        pixel can only be one color, and each color represents a single object
        instance.

        Parameters
        ----------
        instances: :class:`str`, :class:`list` of :class:`str`, or :any:`None`, optional
            If :any:`None`, returns a segmentation containing every object in the sample.
            Otherwise, returns a segmentation that contains just the given object
            instances.

        Returns
        -------
        matte: :class:`imagecat.data.Image`
            Imagecat image containing the given segmentation.
        """
        if instances is None:
            instances = self.instances
        elif isinstance(instances, str):
            instances = [instances]
        self._sample.graph.set_task("/cryptomatte-clown/mattes", graphcat.constant(instances))
        return self._sample.graph.output("/cryptomatte-clown")


class Synthetic(object):
    """Provides access to extra information provided by synthetic samples.

    There is no reason to create an instance of this class yourself, callers
    should obtain instances from the :meth:`Sample.synthetic` property.
    """
    def __init__(self, sample):
        self._sample = sample

        if "cryptomatte" in sample.metadata["synthetic"]:
            self._cryptomatte = Cryptomatte(sample, self)
        else:
            self._cryptomatte = None


    @property
    def cryptomatte(self):
        """Optional cryptomatte data for this sample.

        Samples that are generated synthetically typically include masking
        information that is stored using a cryptomatte, and the
        object returned by this property (if any) provides access to the
        cryptomatte data.

        Returns
        -------
        cryptomatte: :any:`Cryptomatte` or :any:`None`
        """
        return self._cryptomatte


    @property
    def depth(self):
        """Rendered depth (LIDAR) image for this sample.

        Returns
        -------
        image: :class:`imagecat.data.Image`
        """
        return self._sample.graph.output("/remap-render-depth")


    @property
    def image(self):
        """Rendered image for this sample.

        Note that the rendered image for the sample is a high-dynamic-range
        image with floating-point pixel values.  Thus, it is higher-quality than
        the reference image for the sample, which is clipped and stored in PNG
        format using unsigned bytes.

        Returns
        -------
        image: :class:`imagecat.data.Image`
        """
        return self._sample.graph.output("/remap-render-image")


    def materialize_image(self):
        """Extract a reference image for this sample.

        The reference image is converted from the high quality rendered image,
        and stored as a PNG with unsigned byte pixel values.
        """
        image = self.image

        image_filename = self._sample.name + ".png"
        image_path = os.path.join(os.path.dirname(self._sample.path), image_filename)
        self._sample.graph.set_task("/save-image/path", graphcat.constant(image_path))
        self._sample.graph.update("/save-image")

        updates = {
            "image": {
                "content-type": "image/png",
                "res": image.layers["C"].res,
                "filename": image_filename,
                }
            }
        self._sample.update_metadata(updates)


def _bbox_task(graph, name, inputs):
    contours = inputs.getone("contours")
    if not contours:
        return None

    points = numpy.row_stack(contours)
    xmin = points[:, 0].min(axis=0)
    ymin = points[:, 1].min(axis=0)
    xmax = points[:, 0].max(axis=0)
    ymax = points[:, 1].max(axis=0)

    log.info(f"Task {name} completed.")

    return (xmin, ymin, xmax-xmin, ymax-ymin)


def _contours_task(graph, name, inputs):
    # Compute the contours from a [0, 1] matte image.
    matte = inputs.getone("image")
    layer = matte.layers["M"]
    if numpy.all(layer.data == 0):
        return None

    # Find the contours using a padded version of the matte, so the image
    # borders are handled correctly.
    padded = numpy.pad(layer.data[:,:,0], 1)
    contours = skimage.measure.find_contours(padded, positive_orientation="high", level=0.5)
    # Correct for padding
    contours = [contour - 1 for contour in contours]

    # Swap coordinates from (row, col) to (x, y)
    contours = [contour[:,[1, 0]] for contour in contours]

    log.info(f"Task {name} completed.")
    return contours


class Sample(object):
    """Provides access to one sample within a :ref:`specification` dataset.

    Although callers are free to create :any:`Sample` objects directly, they
    are typically returned from an instance of :any:`Dataset`.

    Parameters
    ----------
    path: :class:`str`, required
        Absolute path to the JSON metadata file for a sample.
    """
    def __init__(self, path):
        self._path = os.path.abspath(path)
        with open(path, "rb") as stream:
            self._metadata = json.load(stream)

        self._graph = None

        if "synthetic" in self._metadata:
            self._synthetic = Synthetic(self)
        else:
            self._synthetic = None

    def __repr__(self):
        return f"limbo.data.Sample(path={self._path!r})"


    @property
    def categories(self):
        """All categories that have been applied to this sample, regardless of annotation type.

        Returns
        -------
        categories: :class:`set` of :class:`str`
        """
        return {annotation["category"] for annotation in self._metadata.get("annotations", [])}


    @property
    def default_cryptomatte_path(self):
        image_filename = self.name.replace("image", "cryptomatte") + ".cryptomatte.exr"
        image_path = os.path.join(os.path.dirname(self.path), image_filename)
        return image_path


    @property
    def default_image_path(self):
        image_filename = self.name + ".png"
        image_path = os.path.join(os.path.dirname(self.path), image_filename)
        return image_path


    @property
    def default_synthetic_path(self):
        image_filename = self.name + ".exr"
        image_path = os.path.join(os.path.dirname(self.path), image_filename)
        return image_path


    def delete(self):
        """Unconditionally remove this sample and related files."""
        paths = [self.default_cryptomatte_path, self.default_image_path, self.default_synthetic_path, self.path]
        for path in paths:
            if os.path.exists(path):
                os.remove(path)


    @property
    def graph(self):
        """Graphcat network used for image processing.

        This is used by the rest of the API and should be of little interest to callers.

        Returns
        -------
        graph: :class:`graphcat.graph.Graph`
        """
        if self._graph is None:
            graph = graphcat.StaticGraph()

            # Prepare to load the training image, if it exists.
            if "image" in self._metadata:
                filename = self._metadata["image"]["filename"]
                path = os.path.join(os.path.dirname(self._path), filename)
                imagecat.add_task(graph, "/load-image", imagecat.operator.load, path=path)

    #        imagecat.add_task(graph, "/load-segmentation", imagecat.operator.load, path=None)

            # Prepare to load the synthetic image, if it exists.
            if "synthetic" in self._metadata:
                filename = self._metadata["synthetic"]["image"]["filename"]
                path = os.path.join(os.path.dirname(self._path), filename)

                imagecat.add_task(graph, "/load-render-image", imagecat.operator.load, path=path)
                imagecat.add_task(graph, "/remap-render-image", imagecat.operator.remap, mapping={"C":{"role": imagecat.data.Role.RGB, "selection":["R", "G", "B"]}})
                imagecat.add_task(graph, "/remap-render-depth", imagecat.operator.remap, mapping={"Z":{"role": imagecat.data.Role.DEPTH, "selection":["Z"]}})
                imagecat.add_task(graph, "/save-image", imagecat.operator.save, path=None)
                imagecat.add_links(graph, "/load-render-image", ("/remap-render-image", "image"))
                imagecat.add_links(graph, "/load-render-image", ("/remap-render-depth", "image"))
                imagecat.add_links(graph, "/remap-render-image", ("/save-image", "image"))

                # Prepare to load the cryptomatte image, if it exists.
                if "cryptomatte" in self._metadata["synthetic"]:
                    filename = self._metadata["synthetic"]["cryptomatte"]["filename"]
                    path = os.path.join(os.path.dirname(self._path), filename)

                    imagecat.add_task(graph, "/load-cryptomatte", imagecat.operator.load, path=path)
                    imagecat.add_task(graph, "/cryptomatte", imagecat.operator.cryptomatte.decoder, mattes=None)
                    imagecat.add_task(graph, "/cryptomatte-clown", imagecat.operator.cryptomatte.decoder, clown=True, mattes=None)
    #        imagecat.add_task(graph, "/save-segmentation", imagecat.operator.save, path=None)

                    imagecat.add_task(graph, "/contours", _contours_task)
                    imagecat.add_task(graph, "/bbox", _bbox_task)

                    imagecat.add_links(graph, "/load-cryptomatte", ("/cryptomatte", "image"))
                    imagecat.add_links(graph, "/cryptomatte", ("/contours", "image"))
                    imagecat.add_links(graph, "/contours", ("/bbox", "contours"))
                    imagecat.add_links(graph, "/load-cryptomatte", ("/cryptomatte-clown", "image"))
    #        imagecat.add_links(graph, "/cryptomatte-clown", ("/save-segmentation", "image"))

            self._graph = graph
        return self._graph


    @property
    def image(self):
        """Reference image for this sample, if it exists.

        Returns
        -------
        image: :class:`imagecat.data.Image` or :any:`None`
        """
        if "image" not in self._metadata:
            return None
        return self.graph.output("/load-image")


    @property
    def image_path(self):
        """Filesystem path of the reference image for this sample, if it exists.

        Returns
        -------
        image: :class:`str` or :any:`None`
        """
        if "image" in self._metadata:
            filename = self._metadata["image"]["filename"]
            return os.path.join(os.path.dirname(self._path), filename)
        return None


    @property
    def metadata(self):
        """Metadata for this sample.

        Returns
        -------
        metadata: :class:`dict`
        """
        return self._metadata


    @property
    def name(self):
        """Name for this sample.

        Returns
        -------
        name: :class:`str`
        """
        return os.path.splitext(os.path.basename(self._path))[0]


    @property
    def path(self):
        """Metadata path for this sample.

        Returns
        -------
        path: :class:`str`
            Absolute path to the metadata file for this sample.
        """
        return self._path


    def preview(self, show_bboxes=False, show_contours=False, include=None):
        """Generate an annotated preview image from the sample.

        Note
        ----

        This method only displays annotations that are stored in the sample metadata;
        annotations provided by a :class:`Cryptomatte` object will not be visible,
        unless they have been materialized using :meth:`Cryptomatte.materialize_bounds`.

        Parameters
        ----------
        show_bboxes: :class:`bool`, optional
            If :any:`True`, the preview will include bounding box annotations.
        show_contours: :class:`bool`, optional
            If :any:`True`, the preview will include contour annotations.
        include: callable object, optional
            If specified, the given callable object will be called once per
            sample annotation.  If it returns :any:`True`, the annotation
            will be included in the preview.

        Returns
        -------
        surface: :class:`skia.Surface`
            Skia drawing library surface containing the preview that can be
            converted into a bitmap or other image format.
        """
        if include is None:
            include = lambda x: True

        # Assign a color to each category.
        color = itertools.cycle(imagecat.color.brewer.palette("Set1").colors)
        colors = {}
        categories = {}
        annotations = self._metadata.get("annotations", [])
        for annotation in annotations:
            category = annotation["category"]
            if category not in categories:
                categories[category] = next(color)
            colors[category] = categories[category]

        # Start drawing.
        res = self._metadata["image"]["res"]
        surface = skia.Surface(res[0], res[1])
        canvas = surface.getCanvas()
        canvas.clear(skia.Color4f.kWhite)
        font = skia.Font()

        data = self.image.layers["C"].data
        data = imagecat.color.linear_to_srgb(data)
        data = numpy.dstack((data, numpy.ones(data.shape[:2], dtype=numpy.float16)))
        image = skia.Image.fromarray(data, colorType=skia.ColorType.kRGBA_F16_ColorType)
        canvas.drawImage(image, left=0, top=0)

        # Draw contours.
        if show_contours:
            for annotation in self._metadata.get("annotations", []):
                if "contours" not in annotation:
                    continue
                if not include(annotation):
                    continue

                contours = annotation["contours"]
                for contour in contours:
                    points = [skia.Point(point[0], point[1]) for point in contour]
                    path = skia.Path.Polygon(points, isClosed=True)

                    category = annotation["category"]
                    color = colors[category]

                    paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 0.2), Style=skia.Paint.kFill_Style)
                    canvas.drawPath(path, paint)
                    paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 1), Style=skia.Paint.kStroke_Style)
                    canvas.drawPath(path, paint)

                    center = numpy.mean(contour, axis=0)
                    paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), Style=skia.Paint.kFill_Style)
                    canvas.drawSimpleText(category, center[0], center[1], font, paint)

        # Draw bounding boxes.
        if show_bboxes:
            for annotation in annotations:
                if "bbox" not in annotation:
                    continue
                if not include(annotation):
                    continue

                xywh = annotation["bbox"]
                rect = skia.Rect.MakeXYWH(*xywh)

                category = annotation["category"]
                color = colors[category]

                paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 0.2), Style=skia.Paint.kFill_Style)
                canvas.drawRect(rect, paint)
                paint = skia.Paint(Color=skia.Color4f(color[0], color[1], color[2], 1), Style=skia.Paint.kStroke_Style)
                canvas.drawRect(rect, paint)

                paint = skia.Paint(Color=skia.Color4f(1, 1, 1, 1), Style=skia.Paint.kFill_Style)
                canvas.drawSimpleText(category, xywh[0] + 5, xywh[1]+xywh[3] - 5, font, paint)

        return surface


    @property
    def synthetic(self):
        """Optional synthetic data for this sample.

        Samples that are generated synthetically contain information that isn't
        present in samples gathered from more traditional sources (like
        photographs), and the object returned by this property (if any)
        provides access to that information.

        Returns
        -------
        synthetic: :any:`Synthetic` or :any:`None`
        """
        return self._synthetic


    def update_metadata(self, updates):
        """Modify the metadata for this sample.

        Parameters
        ----------
        updates: :class:`dict`, required
            Metadata information that will be merged
            with the existing metadata, and saved to disk.
        """
        self._metadata.update(updates)
        with open(self._path, "w") as stream:
            json.dump(self._metadata, stream, indent=2, sort_keys=True)


class Dataset(object):
    """Provides access to one-or-more :ref:`specification` datasets.

    Use ``len(dataset)`` to retrieve the number of samples in the dataset.

    Use ``dataset[index]`` to retrieve the :any:`Sample` at the given integer index.

    Use ``for sample in dataset:`` to iterate over :any:`samples<Sample>`.

    Parameters
    ----------
    paths: :class:`str` or :class:`list` of :class:`str`, required
        Paths to one-or-more directories containing data in
        :ref:`specification`.  The resulting dataset object can be used to
        access the union of the data from the given paths.

    """
    def __init__(self, paths):
        if isinstance(paths, str):
            paths = [paths]
        paths = [os.path.abspath(path) for path in paths]

        samples = []
        for path in paths:
            samples += glob.glob(os.path.join(path, "**/*.json"), recursive=True)

        self._paths = paths
        self._samples = sorted(samples)


    def __len__(self):
        return len(self._samples)


    def __getitem__(self, index):
        return Sample(self._samples[index])


    def __iter__(self):
        for index in range(len(self)):
            yield Sample(self._samples[index])


    def __repr__(self):
        return f"limbo.data.Dataset(paths={self._paths!r})"


    @property
    def paths(self):
        """Paths used to initialize the dataset.

        Returns
        -------
        paths: :class:`list` of :class:`str`
            Absolute paths used to initialize this object.
        """
        return self._paths
