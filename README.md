# Service Registry #

This is a simple service registry that can be used in a distributed
service oriented architecture.

It is designed to be simple, scalable and fault tolerant.

What it is:

* simple
* eventually consistent
* scalable

What it is not:

* a coordination service


## The API

Through this section we refer to the service registering its instance
as "the client".

### Registering

Each service instance that wants to make its presence known should
update its instance entry regulary.  This is done via PUT request to
`/<service>/<id>`.  The service registry do not enforce a specific
content format except that it has to be a JSON object.  What the
object contains is up to the users of the system to decide, but we
recommend something along the following lines:

    {
      "host": "ec2-NN-NN-NN-NN.compute-1.amazonaws.com",
      "port": 1232,
      "updated_at": "<iso 8601 format>",
    }

The `updated_at` field should contain a timestamp of when the last PUT
request was performed.  The client is responsible for setting this
field.  Users of the registry can use this field to detect instances
that has stopped updating its entry.

Other information that can be of interest to communicate via the
instance entry:

* current instance status/load
* data center location
* software version

The update request that the service instance do acts as a heartbeat
signal to the registry.  If an update request has not been received
for `liveness` seconds the entry will be expired from the registry.

Example:

    $ curl -XPUT -d '{"host":"10.1.1.1", "port": 12345, "updated_at": "2012-12-18T13:27:01Z"}' http://localhost:8080/storage/1f11bbbb-df7a-47c5-8ba7-662f70261673

### Query Service Registry

The most common query is look up all instances of a specific service.
This is done by issuing a GET to `/<service>`.  The result looks
something like this:

    {
      "<instance>": {
        "host": "ec2-NN-NN-NN-NN.compute-1.amazonaws.com",
        "port": 1232,
        "updated_at": "<iso 8601 format>",
      },
      ...
    }

The result contains all registered instances for the service, in an
unspecified order.   Example:

    $ curl "http://localhost:8080/storage?pretty"
    {
      "1f11bbbb-df7a-47c5-8ba7-662f70261673": {
        "host": "10.1.1.1", 
        "port": 12345, 
        "updated_at": "2012-12-18T13:27:01Z"
      }
    }

# Usage Patterns

## Writing a Service

Through this section we refer to the service registering its instance
as "the client".

In short, a client should register itself with the service registry
server, and then with regular intervals update the entry to make sure
that it is not expired from the registry.  The interval should be set
with the `liveness` parameter in thought.  For example, if `liveness`
is set to 5 minutes, a good update interval can be every minute.

If there are mutliple machines in the service registry cluster, the
client should first and foremost use the node that is located in the
same data center.  If that fails, any of the other nodes can be used
to update the entry.

## Writing a Client

Through this section we refer to an entity that wants to talk to
services as "the client".

The client can query any node in the service registry cluster, but
should prefer to talk to nodes in the same data center.

The client should do a initial query to get the seed set of service
instances.  After that, it should regulary re-query the instance set.
The re-query intervals should be determined by SLAs.

# Configuration:

Below is an example configuration:

    name: sr-sto-1
    port: 3222
    liveness: 300
    cluster:
      sr-sto-1:
        host: ec2-NN-NN-NN-NN.compute-1.amazonaws.com
        port: 3222
      sr-ash-1:
        host: ec2-NN-NN-NN-NN.compute-1.amazonaws.com
        port: 3222
      sr-lon-1:
        host: ec2-NN-NN-NN-NN.compute-1.amazonaws.com
        port: 3222

Here's a short description of the variables:

* `name` defines the name of the local node in the cluster.  There must be
  a node in `cluster` for this node.
* `port` sets the listen port of the service.
* `liveness` specifies for how long a service instance should live before
  being expired, unless updated.
* `cluster´ defines the replication cluster.

# Internals

The instances of the service registry runs a gossip-like protocol to
exchange data.  How often the peers gossip is controlled by the
`gossip-interval` config variable.

Each node has a complete replica of its siblings state.  A node state
is made up out of `(service instance, timestamp)` pairs.  The
timestamp identifies the last time the instance information was
updated.  It is used to filter out old instances and to resolve
conflicting writes (LWW).

If we look at the configuration:

    name: sr-sto-1
    cluster:
      sr-sto-1:
        host: ec2-NN-NN-NN-NN.compute-1.amazonaws.com
        port: 3222
      sr-ash-1:
        host: ec2-NN-NN-NN-NN.compute-1.amazonaws.com
        port: 3222
      sr-lon-1:
        host: ec2-NN-NN-NN-NN.compute-1.amazonaws.com
        port: 3222

The cluster is made out of three servers, `sr-sto-1`, `sr-ash-1` and
`sr-lon-1`.  The `name` field sets the local name and this should be
different for each instance of the service registry.  The `sr-sto-1`
instance will talk to `sr-ash-1` and `sr-lon-1` at regular intervals.
When `sr-sto-1` talks to `sr-lon-1` it will also receive state updates
for `sr-ash-1`.  This means that if there are network errors that
cause a partial network failure where two nodes cannot talk to
eachother they can still receive updates through the third peer.

When a node has picked a sibling to talk to, it sends a request for
deltas.  This request includes the "last seen timestamp" for all peers
in the cluster.  The node should respond with a set of deltas that can
be applied to the node states.  An example from sr-sto-1 to sr-lon-1
may look like this:

    GET /_deltas?sr-lon-1=T1&sr-ash-1=T2
    ...

Interpret this as `sr-sto-1` tries to get deltas for lon-1 and ash-1,
but only for stuff that was written after the two specified
timestamps.  The response looks something like this:

    {
      "sr-lon-1": [["srv1", "id1", {...}, 1355833258675], ...],
      "sr-ash-1": [["srv1", "id2", {...}, 1355833268199], ...]
    }


## Failure Conditions

Outlined here are a few failure conditions and how they are solved.

* One node in the cluster crashes and its state is wiped => any old
  state will be purged on the other nodes when it becomes old.  After
  a while any new writes from the crashed node will propage to the
  peers.

* One node is isolated from the cluster => service instance data owned
  by the isolated node will be purged.  When connection is restablished
  new writes will be propagated to the peers.








