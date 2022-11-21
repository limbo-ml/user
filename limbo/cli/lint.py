# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.


import argparse
import logging
import os
import sys

import tqdm

import limbo.data

def main():
    parser = argparse.ArgumentParser(description="Correct problems with Limbo dataset(s).")
    parser.add_argument("--delete-empty-bboxes", action="store_true", help="Remove empty bounding box annotations.")
    parser.add_argument("--delete-missing-cryptomatte", action="store_true", help="Remove samples that don't have Cryptomatte data.")
    parser.add_argument("--delete-missing-image", action="store_true", help="Remove samples that don't have a reference image.")
    parser.add_argument("--delete-missing-synthetic", action="store_true", help="Remove samples that don't have synthetic image data.")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes.")
    parser.add_argument("datadir", nargs="+", default=[], help="Limbo dataset director(ies).")
    arguments = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("imagecat").setLevel(logging.WARN)

    logging.info("Linting data in:")
    for path in arguments.datadir:
        logging.info(f"  {path}")

    dataset = limbo.data.Dataset(arguments.datadir)

    for sample in tqdm.tqdm(dataset, desc="Samples", unit="sample"):
        delete_sample = False

        if arguments.delete_empty_bboxes:
            if "annotations" in sample.metadata:
                annotations = []
                for annotation in sample.metadata["annotations"]:
                    if "bbox" in annotation:
                        x, y, width, height = annotation["bbox"]
                        if width == 0 and height == 0:
                            logging.error(f"Found empty bounding box in {sample.path}")
                            continue
                    annotations.append(annotation)
                if annotations != sample.metadata["annotations"]:
                    logging.info(f"Updating {sample.path} metadata.")
                    if not arguments.dry_run:
                        sample.update_metadata({"annotations": annotations})

        if arguments.delete_missing_cryptomatte:
            if not os.path.exists(sample.default_cryptomatte_path):
                logging.error(f"Missing Cryptomatte image {sample.default_synthetic_path}")
                delete_sample = True

        if arguments.delete_missing_image:
            if not os.path.exists(sample.default_image_path):
                logging.error(f"Missing reference image {sample.default_image_path}")
                delete_sample = True

        if arguments.delete_missing_synthetic:
            if not os.path.exists(sample.default_synthetic_path):
                logging.error(f"Missing synthetic image {sample.default_synthetic_path}")
                delete_sample = True

        if delete_sample:
            logging.info(f"Deleting {sample.path}")
            if not arguments.dry_run:
                sample.delete()
