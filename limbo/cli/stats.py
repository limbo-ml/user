# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.

import argparse
import itertools
import logging
import os
import sys

import numpy
import scipy.sparse
import tqdm

import limbo.data

def main():
    parser = argparse.ArgumentParser(description="Print information about Limbo dataset(s).")
    parser.add_argument("--annotations", action="store_true", help="Display annotation statistics.")
    parser.add_argument("--copyright", action="store_true", help="Display copyright statistics.")
    parser.add_argument("--empty-bbox", action="store_true", help="Display samples that have empty bounding boxes.")
    parser.add_argument("--license", action="store_true", help="Display license statistics.")
    parser.add_argument("--license-csv", action="store_true", help="Display license statistics as CSV data.")
    parser.add_argument("datadir", nargs="+", default=[], help="Limbo dataset director(ies).")
    arguments = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("imagecat").setLevel(logging.WARN)

    logging.info("Extracting statistics from:")
    for path in arguments.datadir:
        logging.info(f"  {path}")

    dataset = limbo.data.Dataset(arguments.datadir)

    # Setup column indices for a sparse matrix.
    column = itertools.count()

    bbox_column = next(column)
    empty_bbox_column = next(column)
    category_columns = {}
    contour_column = next(column)
    copyright_columns = {}
    cryptomatte_column = next(column)
    image_column = next(column)
    index_column = next(column)
    license_columns = {}
    provenance_column = next(column)
    synthetic_column = next(column)
    tag_column = next(column)

    # Iterate over samples, incrementally populating a sparse matrix in coordinate format.
    i = []
    j = []
    data = []

    def mark(row, col, value=1):
        i.append(row)
        j.append(col)
        data.append(value)

    for row, sample in enumerate(tqdm.tqdm(dataset, desc="Samples", unit="sample")):
        mark(row, index_column) # This guarantees that there will be a row for every sample in the sparse data.

        for category in sample.categories:
            if category not in category_columns:
                category_columns[category] = next(column)
            mark(row, category_columns[category])

        if "annotations" in sample.metadata:
            for annotation in sample.metadata["annotations"]:
                if "bbox" in annotation:
                    mark(row, bbox_column)
                    x, y, width, height = annotation["bbox"]
                    if width == 0 and height == 0:
                        mark(row, empty_bbox_column)
                if "contours" in annotation:
                    mark(row, contour_column)
                else:
                    mark(row, tag_column)

        if "image" in sample.metadata:
            mark(row, image_column)

        if "provenance" in sample.metadata:
            mark(row, provenance_column)

            copyright = sample.metadata["provenance"].get("copyright", "")
            if copyright not in copyright_columns:
                copyright_columns[copyright] = next(column)
            mark(row, copyright_columns[copyright])

            license = sample.metadata["provenance"].get("license", "")
            if license not in license_columns:
                license_columns[license] = next(column)
            mark(row, license_columns[license])

        if sample.synthetic:
            mark(row, synthetic_column)
            if sample.synthetic.cryptomatte:
                mark(row, cryptomatte_column)

    categories = sorted(category_columns.keys())
    copyrights = sorted(copyright_columns.keys())
    licenses = sorted(license_columns.keys())

    samples = scipy.sparse.coo_matrix((data, (i, j))).toarray()

    print(f"Total samples: {len(dataset)}.")
    print("")
    print(f"- Samples with provenance: {numpy.count_nonzero(samples[:,provenance_column])}")
    print(f"- Samples with images: {numpy.count_nonzero(samples[:,image_column])}")
    print(f"- Samples with synthetic data: {numpy.count_nonzero(samples[:,synthetic_column])}")
    print(f"- Samples with cryptomatte data: {numpy.count_nonzero(samples[:,cryptomatte_column])}")
    print(f"- Samples with bounding-boxes: {numpy.count_nonzero(samples[:,bbox_column])}")
    print(f"- Samples with empty bounding-boxes: {numpy.count_nonzero(samples[:,empty_bbox_column])}")
    print(f"- Samples with contours: {numpy.count_nonzero(samples[:,contour_column])}")
    print(f"- Samples with tags: {numpy.count_nonzero(samples[:,tag_column])}")
    print("")

    print("Categories:")
    print("")
    for category in categories:
        print(f"- Category *{category}* samples: {numpy.count_nonzero(samples[:,category_columns[category]])}")
    print("")

    old_columns = [category_columns[category] for category in categories]
    new_columns = [index for index, column in enumerate(old_columns)]
    new_samples = samples[:, old_columns]

    if arguments.annotations:
        print("Annotations:")
        print("")
        for configuration in numpy.unique(new_samples, axis=0):
            label = " + ".join([f"*{category}*" for category, new_column in zip(categories, new_columns) if configuration[new_column]])
            matches = numpy.all(numpy.equal(new_samples, configuration), axis=1)
            print(f"- Samples annotated {label}: {numpy.sum(matches)}")
        print("")

    if arguments.copyright:
        print("Copyrights:")
        print("")
        for copyright in copyrights:
            print(f"- Copyright *{copyright}* samples: {numpy.count_nonzero(samples[:,copyright_columns[copyright]])}")
        print("")

    if arguments.empty_bbox:
        print("Empty Bounding Boxes:")
        print("")
        indices = numpy.flatnonzero(samples[:, empty_bbox_column])
        indices = " ".join([str(index) for index in indices])
        print(indices)

    if arguments.license:
        print("Licenses:")
        print("")
        for license in licenses:
            print(f"- License *{license}* samples: {numpy.count_nonzero(samples[:,license_columns[license]])}")
        print("")

    if arguments.license_csv:
        print("count,original,indices\n")
        for license in licenses:
            indices = numpy.flatnonzero(samples[:, license_columns[license]])
            indices = " ".join([str(index) for index in indices])
            print(f"{numpy.count_nonzero(samples[:,license_columns[license]])},\"{license}\",{indices}\n")


