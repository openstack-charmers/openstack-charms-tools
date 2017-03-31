#!/usr/bin/env python3
#
# Copyright 2017 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# TODO: Manipulate constraints and tags for hardware vs virtual
# TODO: Default VIPS for serverstack
# TODO: VIPS file. YAML or python
# TODO: Local cache of charms


import argparse
import logging

from os_charms_tools.rendered_bundle import RenderedBundle

__author__ = 'David Ames <david.ames@canonical.com>'


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
            '-b', '--source_bundle',
            help="Source bundle YAML file to manipulate")
    group.add_argument(
            '-g', '--generate', action='store_true',
            help="Alpha: Generate base bundle from scratch")
    parser.add_argument(
            '-o', '--overrides', nargs='*',
            help="One or more override YAML files in ascending order of "
                 "signficance. The last file in the list is most significant ")
    parser.add_argument(
            '-d', '--destination', default="rendered.yaml",
            help="Destination YAML file for the rendered bundle. "
                 "Default: rendered.yaml")
    parser.add_argument(
            '-s', '--series', default="xenial",
            help="Series for the model")
    parser.add_argument(
            '-r', '--release', default="mitaka",
            help="OpenStack release for the model")
    parser.add_argument(
            '-src', '--source', default="stable",
            choices=['stable', 'next', 'github'],
            help="Source to pull charms from. Stable and next are the "
                 "charmstore. Github will pull dirrectly from the repo. "
                 "Default: stable")
    parser.add_argument(
            '-t', '--target',
            help="Target in the YAML bundle. i.e. xenial-mitaka or "
            "trusty-liberty-proposed.")
    parser.add_argument(
            '-ha', '--high-availability', action='store_true',
            help="Add High Availability to all HA capable charms.")
    parser.add_argument(
            '-l', '--log_level', default="WARN",
            choices=['DEBUG', 'INFO', 'WARN',  'ERROR'],
            help="Set logging level")
    return parser.parse_args()


def set_log_level(log_level):
    logging.basicConfig(level=log_level.upper())


def main():
    args = get_args()
    set_log_level(args.log_level)

    # Initialize the bundle
    bundle = RenderedBundle(args.series, args.release,
                            args.source, args.target)

    if args.generate:
        # Generate base bundle from scratch
        bundle.generate_bundle()
    else:
        # Render bundle from existing bundle yaml
        bundle.get_bundle_from_yaml(args.source_bundle)

    # Based on target urls and origin may be different
    # than self initilized urls and origin.
    bundle.update_urls()
    bundle.update_origin()

    # Setup High Availability
    if args.high_availability:
        # TODO: Will need to pass yaml with VIP info
        bundle.add_ha()

    # Merge override yaml files
    # Note: This merge happens last so these are truly overrides
    # New charms and relations can be added
    # Options, urls, origin etc can all be overriden
    if args.overrides:
        bundle.merge_overrides(args.overrides)

    # Write out the bundle
    bundle.write_bundle(args.destination)


if __name__ == '__main__':
    main()
