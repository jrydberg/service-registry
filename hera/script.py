

def produce_deltas(states, request):
    """Given a set of states, produce deltas."""
    deltas = []
    for name, timestamp in request.params.items():
        if name in states:
            for delta in states[name].iterdeltas(timestamp):
                deltas.append((name, delta))
    return Response(body=json.dumps(deltas))


def main():
    config = None
    states = {}
    nodes = {}
    for name, spec in cluster.iteritems():
        states[name] = State(time)
        if name != config['name']:
            nodes[name] = Node(name, spec['host'],
                spec['port'], states[name], requests)
    cluster = Cluster(config['name'], nodes)

    # the local state, our state:
    state = states[config['name']]

