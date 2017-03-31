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

'''
bundle-reducer helpers
'''

import logging
import os
import random
import string
import yaml

import os_charms_tools.control_data_common as control_data

from copy import deepcopy
from jinja2 import Environment, FileSystemLoader

__author__ = 'Ryan Beisner <ryan.beisner@canonical.com>'


class CharmHasNoSource(Exception):
    pass


def read_yaml(the_file):
    '''Returns yaml data from provided file name

    :param the_file: yaml file name to read
    :returns: dictionary of yaml data from file
    '''
    if not os.path.exists(the_file):
        raise ValueError('File not found: {}'.format(the_file))
    with open(the_file) as yaml_file:
        data = yaml.safe_load(yaml_file.read())
    return data


def write_yaml(data, the_file):
    '''Save yaml data dictionary to a yaml file

    :param the_file: yaml file name to write
    :returns: dictionary of yaml data to write to file
    '''
    with open(the_file, 'w') as yaml_file:
        yaml_file.write(yaml.dump(data, default_flow_style=False))


def recursive_dict_key_search(data, key):
    '''Recursively look for key match in dictionaries, return value.

    :param data: dictionary data
    :param key: key to find
    :returns: value of found key
    '''
    if key in data:
        return data[key]
    for _, val in data.items():
        if isinstance(val, dict):
            ret = recursive_dict_key_search(val, key)
            if ret is not None:
                return ret


def render(source, target, context, templates_dir=None):
    '''Render a template.

       The `source` path, if not absolute, is relative to the `templates_dir`.

       The `target` path should be absolute.

       The context should be a dict containing the values to be replaced in
       the template.

       If omitted, `templates_dir` defaults to the current working dir.
    '''

    if templates_dir is None:
        templates_dir = os.getcwd()
    loader = Environment(loader=FileSystemLoader(templates_dir))
    try:
        source = source
        template = loader.get_template(source)
    except Exception:
        logging.error('Could not load template {} from {}.'.format(
            source, templates_dir))
        raise

#    safe_mkdir(templates_dir)
    with open(target, 'w') as _file:
        _file.write(template.render(context))


# above, ripped from uosci common
# below, unique here, or improved from uosci common


def yaml_dump(data):
    '''Return dict data as pretty-ish yaml output.'''
    return yaml.dump(data, default_flow_style=False)


def rnd_str(length=32):
    '''Return lower-case alpha-numeric random string, a la pwgen.

    :param length: number of characters to generate
    :returns: lower-case alpha-numeric random string
    '''
    _str = ''
    for _ in range(length):
        _str += random.choice(string.ascii_lowercase + string.digits)
    return _str


def get_all_services(org_bundle_dict):
    '''Return a frozen set of all services values from dict.'''
    svcs_all = set()

    for (k, v) in org_bundle_dict.items():
        _svcs = recursive_dict_key_search(v, 'services')
        if _svcs:
            svcs_all |= set(list(_svcs.keys()))

    return frozenset(svcs_all)


def rm_attr_from_services(org_bundle_dict, attr):
    '''Remove specified key from all services, where attr is
    commonly one of: to, constraints, or options.'''

    new_bundle_dict = deepcopy(org_bundle_dict)

    for (k, v) in new_bundle_dict.items():
        if 'services' in v.keys():
            _svcs = v['services']
            for (_svc, _svc_attrs) in _svcs.items():
                if (isinstance(_svc_attrs, dict) and
                        attr in _svc_attrs.keys()):
                    logging.debug('Removing {} from '
                                  '{}'.format(attr, _svc))
                    del new_bundle_dict[k]['services'][_svc][attr]

    return new_bundle_dict


def rm_inheritance_targets(org_bundle_dict):
    '''Remove all targets which attempt to inherit from another target.'''

    new_bundle_dict = deepcopy(org_bundle_dict)

    for (k, v) in org_bundle_dict.items():
        if 'inherits' in v.keys():
            logging.debug('Removing {} because it inherits'.format(k))
            del new_bundle_dict[k]

    return new_bundle_dict


def get_lineage(dict_data, target, lineage=None):
    '''Determine recursive deployer style bundle inheritance
    trail and return a list.'''

    if not lineage:
        lineage = [target]

    if 'inherits' in dict_data[target].keys():
        inherits = dict_data[target]['inherits']
        logging.debug('{} inherits {}'.format(target, inherits))
        lineage.append(inherits)
        get_lineage(dict_data, inherits, lineage)
    else:
        logging.debug('Inheritance stops at {}'.format(target))

    return lineage


def get_fresh_bundle():
    '''Construct a fresh bundle with no services, relations or series.'''
    return {
        'services': {},
        'series': None,
        'relations': []
    }


def validate_target_exists(bundle_dict, target):
    '''Validate that a target exists in a bundle'''
    return target in bundle_dict.keys()


def validate_target_inherits(bundle_dict, target):
    '''Validate that a target exists in a bundle, and that it
    claims inheritance of any sort.'''
    return (validate_target_exists(bundle_dict, target) and
            'inherits' in bundle_dict[target])


def render_target_inheritance(bundle_dict, render_target):
    '''Render inheritance for a specific target.'''

    # Validate
    if not validate_target_inherits(bundle_dict, render_target):
        raise ValueError('Target does not specify inheritance: '
                         '{}'.format(render_target))

    # Determine recursive inheritance of target(s)
    lineage = get_lineage(bundle_dict, render_target)
    logging.debug('Lineage {}'.format(lineage))

    # Construct a fresh bundle and seed with the senior inheritance target
    new_bundle = get_fresh_bundle()
    new_bundle.update(bundle_dict[lineage[-1]])

    for target in lineage[:-1][::-1]:
        # Handle relation inheritance
        if 'relations' in bundle_dict[target].keys():
            logging.debug('Inheriting relations from {}'.format(target))
            new_bundle['relations'] = \
                (new_bundle['relations'] +
                 bundle_dict[target]['relations'])

        # Handle series inheritance
        if 'series' in bundle_dict[target].keys():
            logging.debug('Inheriting series from {}'.format(target))
            new_bundle['series'] = bundle_dict[target]['series']

        # Handle service inheritance
        if 'services' in bundle_dict[target].keys():
            for svc in bundle_dict[target]['services']:
                logging.debug('Inheriting service {} from '
                              '{}'.format(svc, target))

                if svc not in new_bundle['services'].keys():
                    # Inheritance might introduce a new service
                    new_bundle['services'][svc] = {}

                new_bundle['services'][svc].update(
                    bundle_dict[target]['services'][svc]
                )

        # Handle overrides
        #   - Use an override keys map to determine which charms and config
        #     overrides are valid for the charm.
        #
        #   - juju-deployer branches and inspects config.yaml of each charm
        #     to determine valid config override keys, whereas this to
        #     does not do charm code retrieval.
        if 'overrides' in bundle_dict[target].keys():
            logging.debug('Inheriting overrides from {}'.format(target))
            for ovr_key, ovr_val in bundle_dict[target]['overrides'].items():
                # Make sure all charms are represented
                validate_charms_have_source(new_bundle['services'].keys())
                for svc in new_bundle['services'].keys():
                    if (ovr_key in control_data.OVERRIDE_KEYS_MAP.keys() and
                            (svc in control_data.OVERRIDE_KEYS_MAP[ovr_key] or
                             control_data.SERVICE_TO_CHARM.get(svc) in
                             control_data.OVERRIDE_KEYS_MAP[ovr_key])):
                        logging.debug('Applying {} to {}'.format(ovr_key, svc))
                        if 'options' not in new_bundle['services'][svc].keys():
                            new_bundle['services'][svc]['options'] = {}

                        new_bundle['services'][svc]['options'][ovr_key] = \
                            bundle_dict[target]['overrides'][ovr_key]
                    else:
                        logging.debug('Ignoring {} for {}'.format(ovr_key,
                                                                  svc))
    return new_bundle


def validate_charms_have_source(services):
    ''' Validate the charm is in one of the following:
        CHARMS_USE_ORIGIN,
        CHARMS_USE_SOURCE,
        CHARMS_USE_OTHER_SOURCE,
        SUBORDINATE_CHARMS.
    '''
    if isinstance(services, str):
        services = [services]
    for service in services:
        if ((service not in control_data.CHARMS_USE_ORIGIN and
                service not in control_data.CHARMS_USE_SOURCE and
                service not in control_data.SUBORDINATE_CHARMS and
                service not in control_data.CHARMS_USE_OTHER_SOURCE and
                service not in control_data.SERVICE_TO_CHARM.keys()) or
                (service in control_data.SERVICE_TO_CHARM.keys() and
                 control_data.SERVICE_TO_CHARM[service] not in
                 control_data.CHARMS_USE_ORIGIN and
                 control_data.SERVICE_TO_CHARM[service] not in
                 control_data.CHARMS_USE_SOURCE and
                 control_data.SERVICE_TO_CHARM[service] not in
                 control_data.CHARMS_USE_OTHER_SOURCE)):

            raise CharmHasNoSource("{} is not in CHARMS_USE_ORIGIN, "
                                   "CHARMS_USE_SOURCE, SUBORDINATE_CHARMS or "
                                   "CHARMS_USE_OTHER_SOURCE "
                                   "It may need to be added".format(service))


def extract_services(org_bundle_dict, svcs_include="ALL", svcs_exclude=None,
                     exclude_related=False, render_target=None,
                     rm_constraints=False, rm_placements=False,
                     rm_inheritance=False):
    '''The mangling beast'''

    new_bundle_dict = deepcopy(org_bundle_dict)
    svcs_whitelist = set()

    # Multiple top-level targets can exist, each with potentially
    # having services and/or relations defined.

    # Make list of service names from all targets
    svcs_all = get_all_services(org_bundle_dict)
    logging.debug(yaml_dump({'svcs_all': sorted(list(svcs_all))}))

    if svcs_include == frozenset():
        logging.debug('Including all services.')
        svcs_include = svcs_all

    # Determine other services
    svcs_other = svcs_exclude | svcs_all - svcs_include
    logging.debug(yaml_dump({'svcs_other': sorted(list(svcs_other))}))

    # Remove relations, optionally determine svcs whitelist
    for (k, v) in org_bundle_dict.items():
        if 'relations' in v.keys():
            _rels = v['relations']
            rels_whitelist = []
            for _rel_pair in _rels:
                _a = _rel_pair[0].split(':')[0]
                _b = _rel_pair[1].split(':')[0]
                if exclude_related:
                    if _a not in svcs_other and _b not in svcs_other and \
                            _a not in svcs_exclude and _b not in svcs_exclude:
                        rels_whitelist.append(_rel_pair)
                else:
                    if (_a not in svcs_other or _b not in svcs_other) and \
                            _a not in svcs_exclude and _b not in svcs_exclude:
                        svcs_whitelist |= {_a}
                        svcs_whitelist |= {_b}
                        rels_whitelist.append(_rel_pair)

            svcs_whitelist -= svcs_exclude

            if not rels_whitelist:
                logging.debug('Removing empty relations key from '
                              '{}.'.format(k))
                del new_bundle_dict[k]['relations']
            else:
                new_bundle_dict[k]['relations'] = rels_whitelist
                logging.debug('rels_whitelist for {}:'
                              '\n{}'.format(k, rels_whitelist))
    logging.debug('svcs_whitelist:\n{}'.format(svcs_whitelist))

    # Remove services
    for (k, v) in org_bundle_dict.items():
        if 'services' in v.keys():
            _svcs = set(v['services'])
            if _svcs & svcs_other - svcs_whitelist:
                for _s in _svcs & svcs_other - svcs_whitelist:
                    del new_bundle_dict[k]['services'][_s]
                    if not len(new_bundle_dict[k]['services']):
                        logging.debug('Removing empty services key from '
                                      '{}.'.format(k))
                        del new_bundle_dict[k]['services']

    # Remove placements
    if rm_placements:
        new_bundle_dict = rm_attr_from_services(new_bundle_dict,
                                                'to')

    # Remove constraints
    if rm_constraints:
        new_bundle_dict = rm_attr_from_services(new_bundle_dict,
                                                'constraints')

    # Remove targets which inherit
    if rm_inheritance:
        new_bundle_dict = rm_inheritance_targets(new_bundle_dict)

    # Render target inheritance
    if render_target:
        new_bundle_dict = render_target_inheritance(new_bundle_dict,
                                                    render_target)

    return new_bundle_dict


def prompt_yes_no(question=None):
    '''Prompt for yes or no, return True or False.'''
    if not question:
        question = "Proceed?"

    _response = input('{}: [y/n]'.format(question))

    if not _response or _response[0].lower() != 'y':
        return False
    else:
        return True
