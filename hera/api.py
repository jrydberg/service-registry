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

from webob.exc import HTTPNotFound
from webob.dec import wsgify
from webob import Request, Response
from routes import Mapper
import json


class RestApi(object):
    """Implement and expose our REST API."""

    def __init__(self, state, combined_state):
        self.state = state
        self.combined_state = combined_state
        self.mapper = Mapper()
        self.mapper.connect("deltas", "/_deltas", controller=self.deltas)
        self.mapper.connect("collection", "/{service}", controller=self.index)
        self.mapper.connect("instance", "/{service}/{instance}",
                            controller=self.update)

    def index(self, request, service):
        """Iterate through all service instances."""
        result = {}
        for delta in self.combined_state.iterservice(service):
            result[delta.instance] = delta.blob
        indent = 2 if 'pretty' in request.params else None
        return Response(body=json.dumps(result, indent=indent))

    def update(self, request, service, instance):
        blob = json.load(request.body_file)
        self.state.update(service, instance, blob)
        return Response(status='204 No Content')

    def deltas(self, request):
        """Produce a set of deltas."""
        deltas = self.combined_state.deltas(request.params)
        return Response(body=json.dumps(deltas))

    @wsgify
    def __call__(self, request):
        """Handle incoming response."""
        route = self.mapper.match(request.path_info)
        if route is None:
            return HTTPNotFound()

        controller = route.pop('controller')
        return controller(request, **route)
