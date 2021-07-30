#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
The :mod:`grpc_proxy.service` contains classes:

- :class:`grpc_proxy.service.LoadBalancer`
- :class:`grpc_proxy.service.RandomChoice`
- :class:`grpc_proxy.service.PeakFirst`
'''
from __future__ import print_function
__docformat__ = 'restructuredtext'

import grpc
import logging
import random

MAX_MSG_LENGTH = 100 * 1024 * 1024
_ONE_DAY_IN_SECONDS = 60 * 60 * 24

class LoadBalancer(object):
    r'''
    Base class for all load nalancer classes.
    '''
    def __init__(self, adresses=[]):
        r'''
        Constructor method.

        :param adresses: A list of hosts for routing.
        :type adresses: list
        '''
        self.adresses = adresses
        
    def sent(self, request, metadata, service, method):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: ???
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
        :type metadata: ???
        :param service: A name of discovery service.
        :type service: str
        :param method: A name of method in discovered service.
        :type method: str
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)
        '''
        acc_host = None
        response = None
        host = random.choice(self.adresses)

        channel = grpc.insecure_channel(
            host, options=[
                ('grpc.max_send_message_length',    MAX_MSG_LENGTH),
                ('grpc.max_message_length',         MAX_MSG_LENGTH),
                ('grpc.max_receive_message_length', MAX_MSG_LENGTH)],)
        
        stub = channel.unary_unary(
            f'/{service}/{method}', 
            request_serializer=None, 
            response_deserializer=None)
        
        try:
            logging.info(f'{host} request')
            response = stub.future(request, metadata=metadata).result(None)
        except grpc.RpcError as e:
            logging.info(f'{host}: {e.code()}')
            raise e
        else:
            acc_host = host

        return acc_host, response
        
class PeakFirst(LoadBalancer):
    r'''
    Implementation of peak first balancer with random host choosing.
    '''
    def sent(self, request, metadata, service, method):
        r'''
        A method for process given request.

        :param request: Binary request without deserialisation.
        :type request: binary
        :param metadata: A gRPC service metadata (included http2 headers). 
            For more details read 
            https://grpc.github.io/grpc/python/grpc.html.
        :type metadata: ???
        :param service: A name of discovery service.
        :type service: str
        :param method: A name of method in discovered service.
        :type method: str
        :return: Return tuple of host and responce from the target services.
        :rtype: (str, binary)
        '''
        acc_host = None
        response = None

        last_error = None

        for host in self.adresses:
            channel = grpc.insecure_channel(
                host, options=[
                    ('grpc.max_send_message_length',    MAX_MSG_LENGTH),
                    ('grpc.max_message_length',         MAX_MSG_LENGTH),
                    ('grpc.max_receive_message_length', MAX_MSG_LENGTH)],)
            
            stub = channel.unary_unary(
                f'/{service}/{method}', 
                request_serializer=None, 
                response_deserializer=None)
            
            try:
                logging.info(f'{host} request')
                response = stub.future(request, metadata=metadata).result(None)
            except grpc.RpcError as e:
                logging.info(f'{host}: {e.code()}')
                last_error = e
            else:
                acc_host = host
                break

        if acc_host is None:
            raise last_error

        return acc_host, response