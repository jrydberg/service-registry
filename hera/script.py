# Copyright 2012 Johan Rydberg
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gevent
from gevent.monkey import patch_all
patch_all(time=True)

from optparse import OptionParser
import time
import yaml
import requests
import logging
import sys

from gevent.pywsgi import WSGIServer
from glock.clock import Clock
from glock.task import LoopingCall

from hera.cluster import Cluster, Node
from hera.state import State, CombinedState
from hera.api import RestApi


def _consume_peer_state(cluster, combined):
    cluster.consume()
    combined.build()


def _purge_expired_deltas(clock, states, combined, liveness):
    for state in states.itervalues():
        state.expire(int(clock.time() - liveness) * 1000)
    combined.build()


class ServiceRegistryApp(object):
    """Namespace for the service registry application."""

    def __init__(self, log, clock, config, name, port, cluster, requests=requests,
                 liveness=5 * 60, gossip_interval=3, purge_interval=7):
        self.log = log
        self.clock = clock
        self.config = config
        self.name = name or config['name']
        self.port = port or config['port']
        self.states = {}
        self.nodes = {}
        self.requests = requests
        self._gossip_interval = gossip_interval
        self._purge_interval = purge_interval
        self._liveness = liveness
        self.build(cluster)

    def build(self, config):
        for name, spec in config.iteritems():
            self.states[name] = State(time)
            if name != self.name:
                self.nodes[name] = Node(name, spec['host'],
                    spec['port'], self.states[name])
        self.cluster = Cluster(self.name, self.nodes, self.requests)
        self.combined_state = CombinedState(self.states)

        self._consume_peer_state_task = LoopingCall(
            self.clock, _consume_peer_state, self.cluster, self.combined_state)
        self._purge_expired_deltas_task = LoopingCall(
            self.clock, _purge_expired_deltas, self.clock, self.states,
            self.combined_state, self._liveness)
        rest_api = RestApi(self.states[self.name], self.combined_state)
        self.server = WSGIServer(('', self.port), rest_api)

    def start(self):
        self.log.info("starting Hera node %s with the following cluster" % (
                self.name,))
        for name, node in self.nodes.iteritems():
            self.log.info("  %s: %r" % (name, node))

        for interval, call in (
            (self._gossip_interval, self._consume_peer_state_task),
            (self._purge_interval, self._purge_expired_deltas_task)):
            call.start(interval)

        self.server.serve_forever()


def main():
    parser = OptionParser()
    parser.add_option("-c", dest="config", default='hera.yml',
                      help="config file", metavar="FILE")
    parser.add_option("-n", "--name", dest="name",
                      help="node name", metavar="NODE")
    parser.add_option("-p", "--port", dest="port", type=int,
                      help="node port", metavar="PORT")
    (options, args) = parser.parse_args()

    format = '%(asctime)s %(name)s %(levelname)s: %(message)s'
    logging.basicConfig(format=format, level=logging.DEBUG)

    try:
        with open(options.config) as fp:
            config = yaml.load(fp)
    except (OSError, IOError), err:
        logging.exception("failed reading config")
        sys.exit(1)

    app = ServiceRegistryApp(logging.getLogger('app'), Clock(), config,
              options.name or config['name'],
              options.port or config['port'],
              config['cluster'])
    app.start()
