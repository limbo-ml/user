# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.

import argparse
import logging
import os

import tqdm

import limbo.data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Materialize everything.")
    parser.add_argument("--bounds", action="store_true", help="Materialize bounding box / bounding polygon metadata.")
    parser.add_argument("--images", action="store_true", help="Materialize PNG images from the EXR originals.")
    parser.add_argument("datadir", nargs="+", default=[], help="Limbo dataset director(ies).")
    arguments = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("imagecat").setLevel(logging.WARN)

    dataset = limbo.data.Dataset(arguments.datadir)
    for sample in tqdm.tqdm(dataset, desc="Samples", unit="sample"):
        #logging.info(f"Processing {sample.name}")
        try:
            if sample.synthetic and sample.synthetic.cryptomatte and (arguments.all or arguments.bounds):
                sample.synthetic.cryptomatte.materialize_bounds()
                #logging.info(f"Materialized bounding box / polygon metadata.")

            if sample.synthetic and (arguments.all or arguments.images):
                sample.synthetic.materialize_image()
                #logging.info(f"Materialized {sample.metadata['image']['filename']}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.info(f"Skipping {sample.name}: {e}")
