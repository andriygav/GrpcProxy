#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
The :mod:`grpc_proxy.interceptors` contains classes and functions:

- :class:`grpc_proxy.interceptors.ProxyInterceptor`
- :func:`grpc_proxy.interceptors.proxy_method`
'''
from __future__ import print_function
__docformat__ = 'restructuredtext'

import time
import logging
from functools import partial, wraps

import grpc
from prometheus_client import Summary, Gauge, Counter

from .balancer import RandomChoice, PickFirst

# available balancer type
_BALANCER_NAME_TO_CLASS = {
    'pick_first': PickFirst,
    'random': RandomChoice,
    'round_robin': RandomChoice
}

REQUEST_TIME = Gauge(
    'grpc_proxy_time', 
    'Time spent processing proxy',
    labelnames=('grpc_proxy_service', 'grpc_proxy_route_name', 'grpc_proxy_hostname', 'grpc_proxy_port'))
NUMBER_OF_PROCESSES = Gauge(
    'grpc_proxy_active_connections', 
    'Total number of active connections')
GRPC_PROXY_CONECTION = Gauge(
    'grpc_proxy_connections_passed_backend', 
    'Total number of passed conection',
    labelnames=('grpc_proxy_service', 'grpc_proxy_status', 'grpc_proxy_route_name', 'grpc_proxy_hostname', 'grpc_proxy_port'))

class GrpcProxyNoRuleError(grpc.RpcError):
    def __init__(self):
        self._code = grpc.StatusCode.UNIMPLEMENTED
        self._details = "GrpcProxy: rule for service is not setup."

    def code(self):
        return self._code
    
    def details(self):
        return self._details

class ProxyInterceptor(grpc.ServerInterceptor):
    r'''
    gRPC interceptor for initialise proxy.
    '''
    def __init__(self, setup, options):
        r'''
        Constructor method.
        
        :param setup: Configuration file for routing
        :type setup: dict()
        :param options: A list of parameters for gRPC chanel.
        :type options: list
        '''
        super(ProxyInterceptor, self).__init__()

        self._metadata_unary_unary = {
            'metadata': { 
                'request':  'unary',
                'response': 'unary'
            }
        }
        
        self.config = dict()
        for item in setup:
            for service in item['grpc-descriptions']:
                self.config[service] = item
                self.config[service]['metadata'] = self._metadata_unary_unary['metadata']

        self.proxy_method = partial(proxy_method, options=options)

    @staticmethod
    def _get_rpc_method_handler(request, response):
        r'''
        Return specific function for the given service type.
        '''
        if request == 'unary' and response == 'unary':
            return grpc.unary_unary_rpc_method_handler
        elif request == 'stream' and response == 'stream':
            return grpc.stream_stream_rpc_method_handler
        elif request == 'unary' and response == 'stream':
            return grpc.unary_stream_rpc_method_handler
        elif request == 'stream' and response == 'unary':
            return grpc.stream_unary_rpc_method_handler

    def intercept_service(self, continuation, handler_call_details):
        r'''
        Interceptor method for generate handler.
        
        :param continuation: Function for get net handler.
        :type continuation: function
        :param handler_call_details: Channel metainformation.
        :type handler_call_details: grpc._server._HandlerCallDetails
        '''
        parts = handler_call_details.method.split("/")
        if len(parts) < 3:
            service, method, is_ok = '', '', False
        else:
            (service, method, *_), is_ok = parts[1:], True
        
        if not is_ok:
            return continuation(handler_call_details)
        
        config = self.config.get(service, None)
        func = partial(self.proxy_method,
                       service=service,
                       method=method,
                       config=config)

        if config is None:
            config = self._metadata_unary_unary
        return self._get_rpc_method_handler(**config['metadata'])(
            func, request_deserializer=None, response_serializer=None)

def proxy_method(request, context, service, method, config, options):
    r'''
    Prototype for gRPC proxy method.

    :param request: Binary request without deserialisation.
    :type request: binary
    :param context: A gRPC service contex. 
        For more details read 
        https://grpc.github.io/grpc/python/grpc.html#service-side-context.
    :type context: grpc._server._Context
    :param service: A name of discovery service.
    :type service: str
    :param method: A name of method in discovered service.
    :type method: str
    :param config: A config dictionary with all information. 
        Must contain field 'hosts' and 'loadBalancer'.
        If None raise GrpcProxyNoRuleError.
    :type config: dict
    :param options: A list of parameters for gRPC channel.
    :type options: list
    :return: Responce from the target services.
    :rtype: binary
    '''
    try:
        NUMBER_OF_PROCESSES.inc()
        start_time = time.time()
        if config is None:
            raise GrpcProxyNoRuleError()
        
        metadata = set(context.invocation_metadata())

        routing = None
        for item in config.get('http', []):
            if 'match' in item:
                headers = {(header, item['match'][0]['headers'][header]['exact']) for header in item['match'][0]['headers']}
                if (headers & metadata) == headers:
                    routing = item
                    break
            else:
                routing = item
                break
            
        if routing is None:
            raise ValueError('Can\'t find routing rule')
        

        adresses = [f'{item["destination"]["host"]}:{item["destination"]["port"]["number"]}' for item in routing['route']]
        host, response = _BALANCER_NAME_TO_CLASS[routing['load-balancing-type']](
            service, 
            method, 
            adresses, 
            options, 
            config['metadata']).sent(
            request, context.invocation_metadata())
        
        GRPC_PROXY_CONECTION.labels(service, 'OK', routing.get('name', None), *host.split(':')).inc()
        REQUEST_TIME.labels(service, routing.get('name', None), *host.split(':')).inc(time.time()-start_time)
        logging.info(f'success redirect to {host} by using routing rule {routing["name"]}')
        return response
    except grpc.RpcError as e:
        context.set_code(e.code())
        context.set_details(e.details())
        return b''
    finally:
        NUMBER_OF_PROCESSES.dec()
