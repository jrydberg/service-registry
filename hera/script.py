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

from gevent.pywsgi import WSGIServer

from hera.cluster import Cluster, Node
from hera.state import State, CombinedState
from hera.api import RestApi



class ServiceRegistryApp(object):
    """Namespace for the service registry application."""

    def __init__(self, config, name, port, requests=requests):
        self.config = config
        self.name = name or config['name']
        self.port = port or config['port']
        self.states = {}
        self.nodes = {}
        self.requests = requests

    def start(self):
        """."""
        for name, spec in self.config['cluster'].iteritems():
            self.states[name] = State(time)
            if name != self.name:
                self.nodes[name] = Node(name, spec['host'],
                    spec['port'], self.states[name])
        self.cluster = Cluster(self.name, self.nodes, self.requests)
        self.combined_state = CombinedState(self.states)

        # the local state, our state:
        gevent.spawn(self._rebuild_combined_state, self.combined_state,
                     time, 3)
        gevent.spawn(self._purge_expired_deltas, self.states.values(),
                     time, 7, self.config.get('liveness', 5 * 60))
        gevent.spawn(self._consume_peer_state, self.cluster, time, self.config.get(
                'replication-interval', 5))

        rest_api = RestApi(self.states[self.name], self.combined_state)
        server = WSGIServer(('', self.port), rest_api)
        server.serve_forever()

    def _consume_peer_state(self, cluster, time, interval):
        while True:
            cluster.consume()
            time.sleep(interval)

    def _rebuild_combined_state(self, combined_state, time, interval):
        while True:
            combined_state.build()
            time.sleep(interval)

    def _purge_expired_deltas(self, states, time, interval, liveness):
        """."""
        while True:
            for state in states:
                state.expire(int(time.time() - liveness) * 1000)
            time.sleep(interval)


def main():
    parser = OptionParser()
    parser.add_option("-c", dest="config", default='hera.yml',
                      help="config file", metavar="FILE")
    parser.add_option("-n", "--name", dest="name",
                      help="node name", metavar="NODE")
    parser.add_option("-p", "--port", dest="port", type=int,
                      help="node port", metavar="PORT")
    (options, args) = parser.parse_args()

    with open(options.config) as fp:
        config = yaml.load(fp)

    app = ServiceRegistryApp(config, options.name, options.port)
    app.start()


if __name__ == '__main__':
    main()
