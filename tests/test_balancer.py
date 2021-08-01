from grpc_proxy.balancer import LoadBalancer

def test_init():
    balancer = LoadBalancer(
        'example.v1.ExampleService',
        'ExampleMethod',
        ['host_one', 'host_two'], )
    assert balancer.adresses[0] == 'host_one'
    assert balancer.adresses[1] == 'host_two'
    assert balancer.service == 'example.v1.ExampleService'
    assert balancer.method == 'ExampleMethod'