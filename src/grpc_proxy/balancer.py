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
    def __init__(self, adresses=[], options=[]):
        r'''
        Constructor method.

        :param adresses: A list of hosts for routing.
        :type adresses: list
        :param options: A list of parameters for gRPC channel.
        :type options: list
        '''
        self.adresses = adresses
        self.options = options
        
    def sent(self, request, metadata, service, method):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: tuple
        :param service: A name of discovery service.
        :type service: str
        :param method: A name of method in discovered service.
        :type method: str
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)

        '''
        raise NotImplementedError

class RandomChoice(LoadBalancer):
    r'''
    Implementation of random balancer with random host choosing.
    '''
    def sent(self, request, metadata, service, method):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: tuple
        :param service: A name of discovery service.
        :type service: str
        :param method: A name of method in discovered service.
        :type method: str
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)
        '''
        if not self.adresses:
            raise GrpcProxyNoHostError()

        host = random.choice(self.adresses)

        channel = grpc.insecure_channel(host, options=self.options)
        stub = channel.unary_unary(
            f'/{service}/{method}', 
            request_serializer=None, 
            response_deserializer=None)
        
        logging.info(f'{host} request')
        try:
            response = stub.future(request, metadata=metadata).result(None)
            return host, response
        except grpc.RpcError as e:
            logging.info(f'{host}: {e.code()}')
            raise e

class PickFirst(LoadBalancer):
    r'''
    Implementation of pick first balancer with random host choosing.
    '''
    def sent(self, request, metadata, service, method):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: tuple
        :param service: A name of discovery service.
        :type service: str
        :param method: A name of method in discovered service.
        :type method: str
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)
        '''
        if not self.adresses:
            raise GrpcProxyNoHostError()

        for host in self.adresses:
            channel = grpc.insecure_channel(host, options=self.options)
            stub = channel.unary_unary(
                f'/{service}/{method}', 
                request_serializer=None, 
                response_deserializer=None)
            
            logging.info(f'{host} request')
            try:
                response = stub.future(request, metadata=metadata).result(None)
                return host, response
            except grpc.RpcError as e:
                logging.info(f'{host}: {e.code()}')
                error = e

        raise error
