#!/usr/bin/python3
#
# Copyright 2017 Canonical Limited.
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


import logging
import yaml

import os_charms_tools.control_data_common as control_data
from os_charms_tools.charm_store import cs_query

__author__ = 'David Ames <david.ames@canonical.com>'

# TODO: Feature: The Charm object could be easily generalized
# Creating an OSCharm(Charm) with openstack specific options


class InvalidSource(Exception):
    pass


class Charm(object):

    def __init__(self, application_name, series, release,
                 source='stable', charm_dict={}):
        # Constants
        self.SUPPORTED_SOURCES = ['stable', 'next', 'github']
        self.OPENSTACK_PROJECT = 'openstack'
        self.OPENSTACK_CHARM_PREFIX = 'charm-'
        self.OPENSTACK_CHARMERS_USER = 'openstack-charmers'
        self.OPENSTACK_CHARMERS_NEXT_USER = 'openstack-charmers-next'
        # From common imports
        self.NATIVE_RELEASES = control_data.NATIVE_RELEASES
        self.SERVICE_TO_CHARM = control_data.SERVICE_TO_CHARM
        self.HA_EXCEPTIONS = control_data.HA_EXCEPTIONS
        # Defaults
        self.application_name = application_name
        self.set_charm_name()
        self.set_options()
        self.set_constraints([])
        self.set_num_units(1)
        self.charmstore_data = None
        self.metadata = None
        self.configs = None
        self.subordinate = None
        self.ha_capable = None

        # Run load from dict early as the init settings may override
        # settings from the dict
        if charm_dict:
            self._load_from_dict(charm_dict)

        # Finish initializing based on init parameters
        self.set_series(series)
        self.set_release(release)
        self.set_source(source, update_urls=False)
        self.set_url(source=self.source)
        self.set_origin()
        self.is_charmstore_charm()
        self.get_charmstore_data()
        self.get_metadata()
        self.get_configs()
        self.is_subordinate(update_num_units=True)
        self.is_ha_capable()

    def __str__(self):
        return 'Charm Object: {}'.format(self.application_name)

    def _load_from_dict(self, charm_dict, update=False):
        if charm_dict[self.application_name].get('charm'):
            self.set_url(charm_dict[self.application_name].get('charm'),
                         custom_url=True)
        if charm_dict[self.application_name].get('num_units'):
            self.set_num_units(
                    charm_dict[self.application_name].get('num_units'))
        if charm_dict[self.application_name].get('options'):
            if update:
                self.update_options(
                        **charm_dict[self.application_name].get('options'))
            else:
                self.set_options(
                        **charm_dict[self.application_name].get('options'))
        if charm_dict[self.application_name].get('series'):
            self.set_series(charm_dict[self.application_name].get('series'))
        if charm_dict[self.application_name].get('to'):
            self.set_placement([charm_dict[self.application_name].get('to')])
        if charm_dict[self.application_name].get('constraints'):
            self.set_constraints(
                    [charm_dict[self.application_name].get('constraints')])

    def _load_from_yaml(self):
        # TODO
        pass

    def update_charm(self, charm_dict):
        self._load_from_dict(charm_dict, update=True)

    def get_dict(self):
        charm_attr_dict = {'charm': self.get_url(),
                           'num_units': self.get_num_units()}
        if self.get_series():
            charm_attr_dict['series'] = self.get_series()
        if self.get_constraints():
            charm_attr_dict['constraints'] = self.get_constraints()
        if self.get_options():
            charm_attr_dict['options'] = self.get_options()
        if self.get_placement():
            charm_attr_dict['to'] = self.get_options()

        return {self.application_name: charm_attr_dict}

    def get_yaml(self):
        return yaml.dump(self.get_dict())

    def set_charm_name(self):
        self.charm_name = self.application_name
        if self.application_name in self.SERVICE_TO_CHARM.keys():
            self.charm_name = (
                    self.SERVICE_TO_CHARM[self.application_name])
        return self.charm_name

    def get_charm_name(self):
        if self.charm_name is None:
            self.set_charm_name()
        return self.charm_name

    def set_url(self, source='stable', series=None,
                user=None, custom_url=False):
        if custom_url:
            self.url = source
            return

        # Otherwise validate the source.
        if source not in self.SUPPORTED_SOURCES:
            raise InvalidSource("{} is not a valid source. Valid sources are: "
                                "stable, next or github".format(source))

        if source == 'github':
            if user:
                self.url = "git://github.com/{}/{}{}".format(
                        user,
                        self.OPENSTACK_CHARM_PREFIX,
                        self.get_charm_name())
            else:
                self.url = "git://github.com/{}/{}{}".format(
                        self.OPENSTACK_PROJECT,
                        self.OPENSTACK_CHARM_PREFIX,
                        self.get_charm_name())
            return

        charmstore_url = []

        if 'next' in source:
            user = self.OPENSTACK_CHARMERS_NEXT_USER
        if user:
            user = '~{}'.format(user)
            charmstore_url.append(user)

        # Series specific
        if series:
            self.set_series(series)

        charmstore_url.append(self.get_series())
        charmstore_url.append(self.charm_name)

        self.url = "cs:{}".format("/".join(charmstore_url))

    def set_origin(self, target=None, config_option=None,
                   custom_origin=False):
        origin = None
        series = None
        release = None
        pocket = None
        # If custom set it directly
        if custom_origin:
            self.origin = custom_origin
            return

        if not target:
            target = '{}-{}'.format(self.series, self.release)

        splits = target.split('-')
        if len(splits) == 2:
            series, release = splits
        elif len(splits) == 3:
            series, release, pocket = splits
        # Do not set origin if the release is native to the series
        if (not pocket and
                series in self.NATIVE_RELEASES.keys() and
                release == self.NATIVE_RELEASES[series]):
            logging.debug("{} is native to {}. Not setting origin."
                          "".format(release, series))
            self.origin = None
            return

        origin = 'cloud:{}-{}'.format(series, release)
        if pocket:
            origin = '{}/{}'.format(origin, pocket)

        self.origin = origin

        if self.has_config_option('openstack-origin'):
            logging.debug("Use openstack-origin: {} for {}"
                          "".format(self.origin, self.application_name))
            self.update_options(**{'openstack-origin': self.origin})
        elif self.has_config_option('source'):
            logging.debug("Use source: {} for {}"
                          "".format(self.origin, self.application_name))
            self.update_options(**{'source': self.origin})
        else:
            logging.warn("{} does not use either openstack-origin or source "
                         "skipping".format(self.application_name))

    def get_origin(self):
        return self.origin

    def get_url(self):
        return self.url

    def set_source(self, source, update_urls=True):
        self.source = source
        # Source changed url should also change
        if update_urls:
            self.set_url(source=self.source)

    def get_source(self):
        return self.source

    def set_num_units(self, num_units):
        self.num_units = num_units

    def get_num_units(self):
        return self.num_units

    def get_options(self):
        return self.options

    def set_options(self, **kwargs):
        options = {}
        for key, val in kwargs.items():
            options[key] = val
        self.options = options

    def update_options(self, **kwargs):
        for key, val in kwargs.items():
            self.options[key] = val

    def get_series(self):
        return self.series

    def set_series(self, series):
        self.series = series

    def get_release(self):
        return self.release

    def set_release(self, release):
        self.release = release

    def get_placement(self):
        # TODO
        pass

    def set_placement(self, to):
        # TODO
        pass

    def set_constraints(self, constraints):
        self.constraints = constraints

    def get_constraints(self):
        if self.constraints:
            return " ".join(self.constraints)

    # TODO Check and fix is not Nones that can be reversed
    def is_charmstore_charm(self):
        self.charmstore_charm = self.get_url().startswith('cs:')
        return self.charmstore_charm

    def is_subordinate(self, update_num_units=True):
        if self.subordinate is not None:
            return self.subordinate

        if (self.get_metadata() and
                self.has_metadata_option('Subordinate')) is not None:
            self.set_subordinate(self.metadata.get('Subordinate'))

        if self.subordinate and update_num_units:
            self.set_num_units(0)

        return self.subordinate

    def set_subordinate(self, subordinate):
        """
        :param: subordinate: boolean
        """
        self.subordinate = subordinate

    def is_ha_capable(self):
        if self.ha_capable is not None:
            return self.ha_capable
        elif self.is_subordinate():
            logging.debug("{} is a subordinate not a primary charm, setting "
                          "ha_capable=False".format(self.charm_name))
            self.ha_capable = False
            return self.ha_capable
        elif self.charm_name in self.HA_EXCEPTIONS:
            logging.debug("{} is in the HA_EXCEPTIONS, setting "
                          "ha_capable=False".format(self.charm_name))
            self.ha_capable = False
            return self.ha_capable

        if (self.get_metadata() and
                self.has_metadata_option('Requires', 'ha')):
            logging.debug("{} is HA capable".format(self.charm_name))
            self.ha_capable = True
        else:
            logging.debug("{} is NOT HA capable".format(self.charm_name))
            self.ha_capable = False
        return self.ha_capable

    def get_charmstore_data(self):
        if self.charmstore_data is not None:
            return self.charmstore_data
        elif not self.is_charmstore_charm():
            # TODO: Feature: Query a local cache of charms
            # TODO: Feature: Would it be possible to scrape info from github?
            logging.warn("{} is not a charm store url cannot query charmstore "
                         "for {}. Use self.set_source(source) source = stable "
                         "or next for charmstore urls."
                         "".format(self.get_url(), self.application_name))
            return False

        self.charmstore_data = {}
        # Query the charmstore for charm data
        self.charmstore_data['charm-metadata'] = (
                cs_query(self.charm_name, self.get_series(), 'charm-metadata'))
        self.charmstore_data['charm-config'] = (
                cs_query(self.charm_name, self.get_series(), 'charm-config'))
        return self.charmstore_data

    def get_metadata(self):
        if self.metadata is not None:
            return self.metadata
        if (self.get_charmstore_data() and
                self.charmstore_data.get('charm-metadata')):
            self.metadata = self.charmstore_data.get('charm-metadata')
            return self.metadata

    def get_configs(self):
        if self.configs is not None:
            return self.configs

        if (self.get_charmstore_data() and
                self.charmstore_data.get('charm-config')):

            self.configs = self.charmstore_data.get('charm-config')
            return self.configs

    def has_metadata_option(self, option, suboption=None):
        if (self.get_metadata() and
                self.metadata.get(option)):
            if (suboption and
                    not self.metadata.get(option).get(suboption)):
                return False
            return True
        else:
            return False

    def has_config_option(self, option):
        if (self.get_configs() and
                self.configs.get('Options') and
                self.configs.get('Options').get(option)):
                return True
        else:
            return False
