#########
GrpcProxy
#########

Basic information
=================

A simple solution for gRPC proxy with multiple hosts by peak first host to resolving.

Usage
=====

For running proxy with default parameters (50 routing connections simultaneously)

.. code-block:: bash

    docker run -p 9878 -v <path to your configuration yaml file>:/config/setup.yaml andriygav/grpc-proxy:latest


Example of setup file
=====================

.. code-block:: bash

    - name: somename
      service: example.v1.ExampleService
      methods:
      - name: ExampleMethod
        match:
        - name: somename
          headers:
            someheaderkey:
              exact: someheadervalue
          hosts:
          - address-one
          - address-two
          loadBalancer:
            type: peek_first
        match:
        - name: someothername
          headers:
            someheaderkey:
              exact: someotherheadervalue
          hosts:
          - address-three
          - address-four
          loadBalancer:
            type: peek_first
        hosts:
        - default-adress
        loadBalancer:
          type: peek_first

- Firstly, need to specify the `service` and `method` for routing discovery (for example we are using `example.v1.ExampleService` and `ExampleMethod` respectively).
- Secondly, need to specify headers information for specific routing (we are using key: value pairs from header such as `someheaderkey` and `someheadervalue`).
- Thirdly, need to specify hosts for routing and type of use it (now only `peek_first` and random available).