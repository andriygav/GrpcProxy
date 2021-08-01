#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
The :mod:`grpc_proxy.service` contains classes:

- :class:`grpc_proxy.service.LoadBalancer`
- :class:`grpc_proxy.service.RandomChoice`
- :class:`grpc_proxy.service.PickFirst`
'''
from __future__ import print_function
__docformat__ = 'restructuredtext'

import grpc
import logging
import random

class GrpcProxyNoHostError(grpc.RpcError):
    def __init__(self):
        self._code = grpc.StatusCode.UNIMPLEMENTED
        self._details = "GrpcProxy: no hosts found for proxying."

    def code(self):
        return self._code
    
    def details(self):
        return self._details

class LoadBalancer(object):
    r'''
    Base class for all load nalancer classes.
    '''
    def __init__(self, 
                 service, 
                 method, 
                 adresses =[], 
                 options  =[], 
                 metadata =None):
        r'''
        Constructor method.

        :param service: A name of discovery service.
        :type service: str
        :param method: A name of method in discovered service.
        :type method: str
        :param adresses: A list of hosts for routing.
        :type adresses: list
        :param options: A list of parameters for gRPC channel.
        :type options: list
        :param metadata: A metadata for the service. 
            A dictionary with request and response type.
            Default request and response has 'unary' type.
        :type metadata: dict
        '''
        if metadata is None:
            metadata = {'request': 'unary', 'response': 'unary'}
        self.adresses = adresses
        self.options = options
        self.metadata = metadata

        self.service = service
        self.method = method

    def _get_stub(self, host):
        r'''
        A method for generate stub for given host.

        :param host: A host for stub generation
        :type host: str
        :return: A connection stub.
        :rtype: ???
        '''
        channel = grpc.insecure_channel(host, options=self.options)

        request = self.metadata['request']
        response = self.metadata['response']
        if request == 'unary' and response == 'unary':
            stub = channel.unary_unary
        elif request == 'stream' and response == 'stream':
            stub = channel.stream_stream
        elif request == 'unary' and response == 'stream':
            stub = channel.unary_stream
        elif request == 'stream' and response == 'unary':
            stub = channel.stream_unary

        return stub(
            f'/{self.service}/{self.method}', 
            request_serializer=None, 
            response_deserializer=None)

    def sent(self, request, metadata):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: tuple
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)
        '''
        raise NotImplementedError

class RandomChoice(LoadBalancer):
    r'''
    Implementation of random balancer with random host choosing.
    '''
    def sent(self, request, metadata):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: tuple
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)
        '''
        if not self.adresses:
            raise GrpcProxyNoHostError()

        host = random.choice(self.adresses)
        stub = self._get_stub(host)
        
        logging.info(f'{host} request')
        try:
            return host, stub(request, metadata=metadata)
        except grpc.RpcError as e:
            logging.info(f'{host}: {e.code()}')
            error = e

        raise error

class PickFirst(LoadBalancer):
    r'''
    Implementation of pick first balancer with random host choosing.
    '''
    def sent(self, request, metadata):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: tuple
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)
        '''
        if not self.adresses:
            raise GrpcProxyNoHostError()

        for host in self.adresses:
            stub = self._get_stub(host)
            
            logging.info(f'{host} request')
            try:
                return host, stub(request, metadata=metadata)
            except grpc.RpcError as e:
                logging.info(f'{host}: {e.code()}')
                error = e

        raise error
