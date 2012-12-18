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

from collections import namedtuple, deque


Delta = namedtuple('Delta', ['service', 'instance', 'blob', 'timestamp'])


class CombinedState(object):
    """View that combines multiple states into one."""

    def __init__(self, states):
        self.states = states
        self.instances = {}
    
    def build(self):
        self.instances.clear()
        for state in self.states.itervalues():
            for delta in state.iterdeltas():
                existing = self.instances.setdefault(delta.service, {}).get(
                    delta.instance)
                if existing and existing.timestamp > delta.timestamp:
                    delta = existing
                self.instances[delta.service][delta.instance] = delta

    def iterservice(self, service):
        d = self.instances.get(service, {})
        return d.values()

    def deltas(self, timestamps):
        deltas = {}
        for name, timestamp in timestamps.items():
            if name in self.states:
                print "ITERDELTAS", name
                deltas[name] = list(self.states[name].iterdeltas(int(timestamp)))
        return deltas


class State(object):
    """State."""

    def __init__(self, clock):
        self.clock = clock
        self.deltas = deque()

    def update(self, service, instance, blob, timestamp=None):
        """Update a service instance record."""
        if timestamp is None:
            timestamp = int(self.clock.time() * 1000)
        delta = Delta(service=service, instance=instance, blob=blob,
                      timestamp=timestamp)
        self.deltas.appendleft(delta)

    def iterdeltas(self, timestamp=0):
        for delta in self.deltas:
            if delta.timestamp > timestamp:
                yield delta

    def expire(self, timestamp):
        self.deltas = deque(delta for delta in self.deltas
                            if delta.timestamp >= timestamp)
