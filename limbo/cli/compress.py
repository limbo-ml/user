import argparse
import collections
import pickle
import re

import limbo.data
import numpy
import torch
import torchvision.transforms
import torchvision.transforms.functional as F
import tqdm


def main():
    parser = argparse.ArgumentParser(description="Compress the contents of a Limbo dataset for efficient loading.")
    parser.add_argument("--end", type=int, help="Range of samples to extract. Default: all samples.")
    parser.add_argument("--images", action="store_true", help="Generate image output.")
    parser.add_argument("--mask", nargs="*", default=[], help="Name-pattern pairs of masks to extract. Default: no masks.")
    parser.add_argument("--metadata", action="store_true", help="Generate metadata output.")
    parser.add_argument("--prefix", default="compressed", help="Output file prefix. Default: %(default)s")
    parser.add_argument("--start", type=int, help="Range of samples to extract. Default: all samples.")
    parser.add_argument("directory", nargs="+", help="Directory(ies) containing Limbo data.")
    arguments = parser.parse_args()

    images = []
    masks = collections.defaultdict(list)
    metadata = []

    dataset = limbo.data.Dataset(arguments.directory)
    for index, sample in enumerate(tqdm.tqdm(dataset)):
        if arguments.start is not None:
            if index < arguments.start:
                continue

        if arguments.end is not None:
            if index >= arguments.end:
                break

        if arguments.images:
            image = sample.image
            if "C" in image.layers:
                image = image.layers["C"].data
            elif "Y" in image.layers:
                image = numpy.tile(image.layers["Y"].data, (1, 1, 3))
            image = F.to_tensor(image)
            image = F.resize(image, (224, 224), interpolation=torchvision.transforms.InterpolationMode.BILINEAR, antialias=True)
            images.append(image)

        for name, pattern in zip(arguments.mask[0:2], arguments.mask[1:2]):
            instances = sample.synthetic.cryptomatte.instances
            instances = [instance for instance in instances if re.search(pattern, instance)]

            mask = sample.synthetic.cryptomatte.matte(instances)
            mask = mask.layers["M"].data
            mask = F.to_tensor(mask)
            mask = F.resize(mask, (224, 224), interpolation=torchvision.transforms.InterpolationMode.BILINEAR, antialias=True)
            masks[name].append(mask)

        if arguments.metadata:
            metadata.append(sample.metadata)


    if arguments.images:
        images = torch.stack(images, dim=0)
        torch.save(images, f"{arguments.prefix}-images.pt")

    for name in masks:
        masks[name] = torch.stack(masks[name], dim=0)
        torch.save(masks[name], f"{arguments.prefix}-masks-{name}.pt")

    if arguments.metadata:
        with open(f"{arguments.prefix}-metadata.pickle", "wb") as stream:
            pickle.dump(metadata, stream)

