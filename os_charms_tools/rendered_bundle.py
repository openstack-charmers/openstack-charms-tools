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


# TODO: Query charmstore for subordinate
# TODO: Query charmstore for openstack-origin vs source
# TODO: Ready yaml config file for VIPS and other HA config

# TODO: Feature: The RenderedBundle object could be easily generalized
# Creating an OSRenderedBundle(RenderedBundle) with openstack specific options

import logging
import os
import yaml

from os_charms_tools.charm import Charm
from os_charms_tools.tools_common import render_target_inheritance
from os_charms_tools.base_constants import (
    BASE_CHARMS,
    BASE_RELATIONS,
    LOCATION_OVERRIDES,
)

__author__ = 'David Ames <david.ames@canonical.com>'

VALID_SOURCES = [
    'stable',
    'next',
    'github',
]


class InvalidSource(Exception):
    pass


class RenderedBundle(object):
    def __init__(self, series, release, source='stable', target=None):
        self.set_series(series)
        self.set_release(release)
        self.set_target(target)
        self.set_source(source)
        self.set_target(target)
        # Charms is a dictionary with application names as keys and charm
        # objects as values {'application_name': charm_obj}
        self.charms = {}
        # Relations is a list of lists [['neutron-api', 'rabbitmq-server]]
        self.relations = []

    def __str__(self):
        return "Rendered Bundle Object: {}".format(self.get_target())

    def set_series(self, series):
        self.series = series

    def get_series(self):
        return self.get_series

    def set_release(self, release):
        self.release = release

    def get_release(self):
        return self.get_release

    def set_source(self, source):
        if source in VALID_SOURCES:
            self.source = source
        else:
            raise InvalidSource("Source: {}, is not one of stable, next "
                                "or github".format(source))

    def get_source(self):
        return self.source

    def generate_bundle(self):
        # Get charm objects
        for charm in BASE_CHARMS:
            charm_obj = Charm(charm, self.series, self.release, self.source)
            self.charms[charm_obj.application_name] = charm_obj

        # Get relations
        self.relations = BASE_RELATIONS

    def update_urls(self):

        # Check for location overrides
        for charm in self.charms.values():
            if charm.application_name in LOCATION_OVERRIDES.keys():
                charm.set_url(LOCATION_OVERRIDES[charm.application_name],
                              custom_url=True)

    def set_target(self, target=None):
        if target is None:
            target = "{}-{}".format(self.series, self.release)
        self.target = target

    def get_target(self):
        return self.target

    def update_origin(self):
        # Set origin based on self.target
        for charm in self.charms.values():
            charm.set_origin(self.get_target())

    def get_bundle_from_yaml(self, yamlfile):
        # Get a dictionary representation of the bundle
        bundle_dict = self.get_yaml_dict(yamlfile)

        # The render_target_inheritance function has this note:
        #   - Use an override keys map to determine which charms and config
        #     overrides are valid for the charm.
        #
        #   - juju-deployer branches and inspects config.yaml of each charm
        #     to determine valid config override keys, whereas this to
        #     does not do charm code retrieval.
        #
        # It may be a good idea to mimic juju-deployer to allow more flexible
        # overrides. Otherwise, we are stuck managing a static constants that
        # can become out of date.
        if not bundle_dict.get('services') and self.get_target():
            bundle_dict = render_target_inheritance(bundle_dict,
                                                    self.get_target())

        if bundle_dict.get('services'):
            self.set_series(bundle_dict.get('series'))

        # Create charm objects and fill up self.charms
        for charm in bundle_dict['services']:
            charm_obj = Charm(
                    charm, self.series, self.release, self.source,
                    charm_dict={charm: bundle_dict['services'][charm]})
            self.charms[charm_obj.application_name] = charm_obj

        # Create relations list and fill up self.relations
        for relation in bundle_dict['relations']:
            self.relations.append(relation)

    def merge_overrides(self, overrides):
        self.overrides = overrides
        for yamlfile in overrides:
            bundle_dict = self.get_yaml_dict(yamlfile)
            if 'services' in bundle_dict.keys():
                logging.debug("Updating services from {}"
                              "".format(yamlfile))
                for charm in bundle_dict['services']:
                    if charm in self.charms.keys():
                        charm_obj = self.charms[charm]
                        charm_obj.update_charm({
                            charm: bundle_dict['services'][charm]})
                    else:
                        charm_obj = Charm(charm, self.series, self.release,
                                          self.source,
                                          charm_dict={
                                              charm:
                                              bundle_dict['services'][charm]})
                        self.charms[charm_obj.application_name] = charm_obj

            if 'relations' in bundle_dict.keys():
                logging.debug("Updating relations from {}"
                              "".format(yamlfile))
                for relation in bundle_dict['relations']:
                    self.relations.append(relation)

    def get_bundle_dict(self):

        bundle_dict = {'services': {}, 'relations': {}}

        for charm in self.charms.values():
            bundle_dict['services'][charm.application_name] = (
                    charm.get_dict()[charm.application_name])

        bundle_dict['relations'] = self.relations

        return bundle_dict

    def write_bundle(self, destination):

        with open(destination, 'w') as dest:
            dest.write(yaml.dump(self.get_bundle_dict()))

    def add_ha(self):
        # TODO read vips from yaml fragment
        ha_charms = []
        non_ha_charms = []
        for charm in self.charms.values():
            if charm.is_ha_capable():
                ha_charms.append(charm)
            else:
                non_ha_charms.append(charm)

        if not ha_charms:
            logging.warn("No charms were deemed HA capable. If source is set "
                         "to github this is expected. Please use stabe or next"
                         " charmstore sources to check for HA capability")

        for charm in ha_charms:
            # Update number of units
            charm.set_num_units(3)
            # Add hacluster for all the HA charms
            charm_obj = Charm("hacluster-{}".format(charm.charm_name),
                              self.series, self.release, self.source)
            charm_obj.set_series(self.series)
            charm_obj.set_url(self.source)
            charm_obj.set_num_units(0)
            charm_obj.set_subordinate(True)
            self.charms[charm_obj.application_name] = charm_obj
            # Add relations for hacluster
            self.relations.append(
                    [charm.application_name, charm_obj.application_name])

    def get_yaml_dict(self, filename):
        if os.path.isfile(filename):
            with open(filename) as yamlfile:
                try:
                    return yaml.load(yamlfile)
                except yaml.parser.ParserError as e:
                    logging.error("Invalid YAML:{}".format(e))
                except yaml.constructor.ConstructorError as e:
                    logging.error("Invalid YAML: Likely templating "
                                  "{{{{variable}}}} breaking YAML".format(e))
        else:
            logging.error("Not a file:", filename)
