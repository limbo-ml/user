# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.


from behave import *

import os
import pkgutil
import subprocess
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
docs_dir = os.path.join(root_dir, "docs")

copyright_notice = """# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS).
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains
# certain rights in this software.
"""


@given(u'all sources.')
def step_impl(context):
    context.sources = []
    for directory, subdirectories, filenames in os.walk(root_dir):
        for filename in filenames:
            if os.path.splitext(filename)[1] not in [".py"]:
                continue

            context.sources.append(os.path.join(directory, filename))
    context.sources = sorted(context.sources)


@then(u'every source must contain a copyright notice.')
def step_impl(context):
    for source in context.sources:
        with open(source, "r") as fobj:
            if not fobj.read().startswith(copyright_notice):
                raise AssertionError("%s missing copyright notice." % source)


