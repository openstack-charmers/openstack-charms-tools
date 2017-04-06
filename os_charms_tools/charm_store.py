#!/usr/bin/python3
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


import logging
from pprint import pprint
import urllib3
import yaml


__author__ = 'James Page <james.page@canonical.com'

VERSION = 'v5'
API_URL = "https://api.jujucharms.com/charmstore/{}/{}/{}/meta/{}"


def cs_query(charm, series, uri=''):
    """ Query the charm store

    :param: charm: Name of charm in the charms store
    :param: series: Series of the charm in the charms store
    :param: uri: meta returns the following which can be addressed directly:
        ['archive-size',
         'archive-upload-time',
         'bundle-machine-count',
         'bundle-metadata',
         'bundle-unit-count',
         'bundles-containing',
         'can-ingest',
         'charm-actions',
         'charm-config',
         'charm-metadata',
         'charm-metrics',
         'charm-related',
         'common-info',
         'extra-info',
         'hash',
         'hash256',
         'id',
         'id-name',
         'id-revision',
         'id-series',
         'id-user',
         'manifest',
         'owner',
         'perm',
         'promulgated',
         'published',
         'resources',
         'revision-info',
         'stats',
         'supported-series',
         'tags',
         'terms']
    """
    url = API_URL.format(VERSION, series, charm, uri)
    http = urllib3.PoolManager()
    result = http.request('GET', url)
    if result.status == 200:
        return yaml.load(result.data)
    else:
        logging.error("FAILED to query: charm: {}, series {}, uri: {}, "
                      "result:{}".format(charm, series, uri, result.status))
        return {}


if __name__ == "__main__":
    pprint(cs_query('neutron-api', 'xenial', uri='charm-metadata'))
