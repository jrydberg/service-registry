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


import random

from requests.exceptions import RequestException


class Node(object):
    """Known state for a node in our cluster.  We do not maintain this
    state for the local node.
    """

    def __init__(self, name, host, port, state):
        self.name = name
        self.state = state
        self.host = host
        self.port = port
        self._last_timestamp = 0

    @property
    def last_timestamp(self):
        for delta in self.state.iterdeltas(self._last_timestamp):
            self._last_timestamp = max(self._last_timestamp, delta.timestamp)
        return self._last_timestamp

    def apply_deltas(self, deltas):
        for (service, instance, blob, timestamp) in deltas:
            self.state.update(service, instance, blob, timestamp)


class Cluster(object):
    """

    @ivar nodes: A mapping between node name and C{Node} objects.
       Note that this must not contain the local node.
    """

    def __init__(self, name, nodes, requests):
        self.name = name
        self.nodes = nodes
        self.requests = requests

    def _query(self, node, timestamps):
        """Query remote node for deltas."""
        response = self.requests.get('http://%s:%d/_deltas' % (
                node.host, node.port), params=timestamps)
        return response.json

    def consume(self):
        """Talk to one or more peers and consume their deltas."""
        candidate = self._select_candidate()
        if candidate is not None:
            try:
                self._apply_deltas(self._query(candidate, self._collect_timestamps()))
            except RequestException, err:
                print "FEL", err

    def _select_candidate(self):
        candidates = self.nodes.values()
        return random.choice(candidates) if candidates else None

    def _collect_timestamps(self):
        timestamps = {}
        for name, node in self.nodes.iteritems():
            timestamps[name] = node.last_timestamp
        return timestamps

    def _apply_deltas(self, result):
        for name, deltas in result.iteritems():
            if name not in self.nodes:
                continue
            self.nodes[name].apply_deltas(deltas)
    
