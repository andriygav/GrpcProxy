#########
GrpcProxy
#########

|build| |codecov| |docker| |docs|

.. |build| image:: https://github.com/andriygav/GrpcProxy/actions/workflows/docker.yml/badge.svg?branch=master
    :target: https://github.com/andriygav/GrpcProxy/actions/workflows/docker.yml
    :alt: Build info

.. |codecov| image:: https://img.shields.io/codecov/c/github/andriygav/GrpcProxy
    :target: https://github.com/andriygav/GrpcProxy/tree/master
    :alt: Test coverage
    
.. |docker| image:: https://img.shields.io/docker/v/andriygav/grpc-proxy
    :target: https://hub.docker.com/repository/docker/andriygav/grpc-proxy
    :alt: Docker Hub Version

.. |docs| image:: https://github.com/andriygav/GrpcProxy/workflows/docs/badge.svg
    :target: https://andriygav.github.io/GrpcProxy/
    :alt: Docs status

Basic information
=================

A simple solution for gRPC proxy with multiple hosts by pick first host to resolving. Currently supports only single packet data transfer (unary_unary grpc type).

Usage
=====

For running proxy with default parameters (50 routing connections simultaneously)

.. code-block:: bash

    docker run -p 9878 -v <path to your configuration yaml file>:/config/setup.yaml andriygav/grpc-proxy:latest


Example of setup file
=====================

.. code-block:: bash

    - service: example.v1.ExampleService
      match:
      - name: somename
        headers:
          someheaderkey:
            exact: someheadervalue
        hosts:
        - address-one
        - address-two
        loadBalancer:
          type: pick_first
      - name: someothername
        headers:
          someheaderkey:
            exact: someotherheadervalue
        hosts:
        - address-three
        - address-four
        loadBalancer:
          type: random
      hosts:
      - default-adress
      loadBalancer:
        type: pick_first

- Firstly, need to specify the `service` for routing discovery (for example we are using `example.v1.ExampleService`).
- Secondly, need to specify headers information for specific routing (we are using key: value pairs from header such as `someheaderkey` and `someheadervalue`).
- Thirdly, need to specify hosts for routing and type of use it (now only `pick_first` and `random` available).
