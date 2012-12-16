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

TOMB = '!TOMBSTONE!'


class State(object):
    """Encapsulation of the service state that a node in the cluster
    holds.

    Items in the state are timestamped.
    """

    def __init__(self, clock):
        self.clock = clock
        self.store = {}

    def set(self, k, v, t=None):
        if t is None:
            t = self.clock.time()
        self.store.set(k, (v, t))

    def get(self, k, default=None):
        v, t = self.store.get(k, (default, 0))
        return v if v != TOMB else default

    def column(self, k):
        return self.store.get(k)

    def remove(self, k):
        self.set(k, TOMB)

    def iterdeltas(self, timestamp):
        for k, (v, t) in self.store.iteritems():
            if t > timestamp:
                yield k, v, t

    def iteritems(self):
        for k, (v, t) in self.store.iteritems():
            yield k, v

    def keys(self):
        return self.store.keys():
