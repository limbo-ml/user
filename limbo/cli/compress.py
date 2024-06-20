# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.

"""Implements the :ref:`limbo-compress` command."""

import argparse
import collections
import copy
import pickle
import re

import limbo.data
import numpy
import tqdm


def argument_parser():
    parser = argparse.ArgumentParser(description="Compress the contents of Limbo datasets for efficient loading.")
    parser.add_argument("--end", type=int, help="Range of samples to extract. Default: all samples.")
    parser.add_argument("--images", action="store_true", help="Generate image output.")
    parser.add_argument("--image-size", type=int, nargs=2, default=(224, 224), help="Target image size. Default: %(default)s")
    parser.add_argument("--mask", nargs="*", default=[], help="Name-pattern pairs of masks to extract. Default: no masks.")
    parser.add_argument("--metadata", action="store_true", help="Generate metadata output.")
    parser.add_argument("--prefix", default="compressed", help="Output file prefix. Default: %(default)s")
    parser.add_argument("--start", type=int, help="Range of samples to extract. Default: all samples.")
    parser.add_argument("--strip-regions", action="store_true", help="Remove bounding-box and contour information from metadata output.")
    parser.add_argument("directory", nargs="+", help="Directory(ies) containing Limbo data.")
    return parser


def main():
    parser = argument_parser()
    arguments = parser.parse_args()

    mask_names = arguments.mask[0::2]
    mask_patterns = arguments.mask[1::2]
    if len(mask_names) != len(mask_patterns):
        raise ValueError("--mask must specify one or more <mask name> <mask pattern> pairs")

    images = []
    masks = collections.defaultdict(list)
    metadatas = []

    dataset = limbo.data.Dataset(arguments.directory)
    for index, sample in enumerate(tqdm.tqdm(dataset)):
        if arguments.start is not None:
            if index < arguments.start:
                continue

        if arguments.end is not None:
            if index >= arguments.end:
                break

        if arguments.images:
            image = sample.resized_image(arguments.image_size)
            if "C" in image.layers:
                image = image.layers["C"].data
            elif "Y" in image.layers:
                image = numpy.tile(image.layers["Y"].data, (1, 1, 3))
            images.append(image)

        for name, pattern in zip(mask_names, mask_patterns):
            if sample.synthetic.cryptomatte:
                instances = sample.synthetic.cryptomatte.instances
                instances = [instance for instance in instances if re.search(pattern, instance)]
                mask = sample.synthetic.cryptomatte.resized_matte(instances, arguments.image_size)
                mask = mask.layers["M"].data
            else:
                mask = numpy.zeros((arguments.image_size[0], arguments.image_size[1], 1))
            masks[name].append(mask)

        if arguments.metadata:
            metadata = copy.deepcopy(sample.metadata)
            if arguments.strip_regions:
                categories = {annotation.get("category") for annotation in metadata.get("annotations", [])}
                metadata["annotations"] = [{"category":category} for category in categories]
            metadatas.append(metadata)


    if arguments.images:
        images = numpy.stack(images, axis=0)
        numpy.save(f"{arguments.prefix}-images.npy", images)

    for name in masks:
        masks[name] = numpy.stack(masks[name], axis=0)
        numpy.save(f"{arguments.prefix}-masks-{name}.npy", masks[name])

    if arguments.metadata:
        with open(f"{arguments.prefix}-metadata.pickle", "wb") as stream:
            pickle.dump(metadatas, stream)

