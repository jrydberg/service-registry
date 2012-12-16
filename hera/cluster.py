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



class Node(object):
    """Known state for a node in our cluster.  We do not maintain this
    state for the local node.
    """

    def __init__(self, name, host, port, state, requests):
        self.name = name
        self.state = state
        self.host = host
        self.port = port
        self.requests = requests
        self._last_timestamp = 0

    @property
    def last_timestamp(self):
        for k, v, t in self.state.iterdeltas(self._last_timestamp):
            self._last_timestamp = max(self._last_timestamp, t)
        return self._last_timestamp

    def query(self, timestamps):
        """Query remote node for deltas."""
        response = self.requests.get('http://%s:%d/_deltas' % (
                self.host, self.port), params=timestamps)
        return response.json

    def apply_delta(self, delta):
        k, v, t = delta
        self.state.set(k, v, t)

    def produce_deltas(self, timestamp):
        for delta in self.state.iterdeltas(timestamp):
            yield self.name, delta


class Cluster(object):
    """

    @ivar nodes: A mapping between node name and C{Node} objects.
       Note that this must not contain the local node.
    """

    def __init__(self, name, nodes):
        self.name = name
        self.nodes = nodes

    def consume(self):
        """Talk to one or more peers and consume their deltas."""
        candidate = self._select_candidate()
        if candidate is not None:
            self._apply_delta(candidate.query(self._collect_timestamps()))

    def _select_candidate(self):
        candidates = self.nodes.values()
        return random.choice(candidates) if candidates else None

    def _collect_timestamps(self):
        timestamps = {}
        for name, node in self.nodes.iteritems():
            timestamps[name] = node.last_timestamp
        return timestamps

    def _apply_deltas(self, deltas):
        for name, delta in deltas:
            if name not in self.nodes:
                continue
            self.nodes[name].apply_delta(delta)
    
