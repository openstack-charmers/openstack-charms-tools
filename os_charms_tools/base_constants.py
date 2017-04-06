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


__author__ = 'Ryan Beisner <ryan.beisner@canonical.com>'

BASE_CHARMS = [
    'neutron-gateway',
    'ceilometer-agent',
    'rabbitmq-server',
    'swift-storage-z3',
    'neutron-api',
    'cinder',
    'percona-cluster',
    'mongodb',
    'swift-storage-z2',
    'neutron-openvswitch',
    'nova-compute',
    'tempest',
    'glance',
    'swift-storage-z1',
    'swift-proxy',
    'ceph',
    'nova-cloud-controller',
    'keystone',
    'ceilometer',
    'openstack-dashboard',
]
BASE_RELATIONS = [
   ['keystone', 'mysql'],
   ['nova-cloud-controller', 'mysql'],
   ['nova-cloud-controller', 'rabbitmq-server'],
   ['nova-cloud-controller', 'glance'],
   ['nova-cloud-controller', 'keystone'],
   ['nova-compute', 'nova-cloud-controller'],
   ['nova-compute', 'mysql'],
   ['nova-compute', 'rabbitmq-server:amqp'],
   ['nova-compute', 'glance'],
   ['nova-compute', 'ceph'],
   ['glance', 'mysql'],
   ['glance', 'keystone'],
   ['glance', 'ceph'],
   ['glance', 'cinder:image-service'],
   ['cinder', 'mysql'],
   ['cinder', 'rabbitmq-server'],
   ['cinder', 'nova-cloud-controller'],
   ['cinder', 'keystone'],
   ['cinder', 'ceph'],
   ['neutron-gateway', 'nova-cloud-controller'],
   ['openstack-dashboard', 'keystone'],
   ['swift-proxy', 'keystone'],
   ['swift-proxy', 'swift-storage-z1'],
   ['swift-proxy', 'swift-storage-z2'],
   ['swift-proxy', 'swift-storage-z3'],
   ['ceilometer:identity-service', 'keystone'],
   ['ceilometer', 'rabbitmq-server'],
   ['ceilometer', 'mongodb'],
   ['ceilometer-agent', 'nova-compute'],
   ['ceilometer-agent', 'ceilometer'],
   ['keystone', 'tempest'],
   ['neutron-gateway:amqp', 'rabbitmq-server'],
   ['neutron-api', 'mysql'],
   ['neutron-api', 'rabbitmq-server'],
   ['neutron-api', 'nova-cloud-controller'],
   ['neutron-api', 'neutron-openvswitch'],
   ['neutron-api', 'keystone'],
   ['neutron-api', 'neutron-gateway'],
   ['neutron-openvswitch', 'nova-compute'],
   ['neutron-openvswitch', 'rabbitmq-server'],
]

LOCATION_OVERRIDES = {
    'mongodb': 'cs:~1chb1n/mongodb',
}
