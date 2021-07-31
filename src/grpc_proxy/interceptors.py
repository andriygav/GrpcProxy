#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
The :mod:`grpc_proxy.interceptors` contains classes and functions:

- :class:`grpc_proxy.interceptors.ProxyInterceptor`
- :func:`grpc_proxy.interceptors.proxy_method`
'''
from __future__ import print_function
__docformat__ = 'restructuredtext'

import logging
from functools import partial, wraps

import grpc
from prometheus_client import Summary, Gauge

from .balancer import RandomChoice, PickFirst

MAX_MSG_LENGTH = 100 * 1024 * 1024

# available balancer type
_BALANCER_NAME_TO_CLASS = {
    'pick_first': PickFirst,
    'random': RandomChoice
}

REQUEST_TIME = Summary('proxy_method_seconds', 'Time spent processing proxy')
NUMBER_OF_PROCESSES = Gauge('proxy_method_processes', 'Time spent processing proxy')

class ProxyInterceptor(grpc.ServerInterceptor):
    r'''
    gRPC interceptor for initialise proxy.
    '''
    def __init__(self, setup):
        r'''
        Constructor method.
        
        :param setup: configuration file for routing
        :type setup: dict()
        '''
        super(ProxyInterceptor, self).__init__()

        self.config = dict()
        for item in setup:
            self.config[item['service']] = item

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
        
        if not is_ok or service not in self.config:
            return continuation(handler_call_details)

        func = partial(proxy_method,
                       service=service,
                       method=method,
                       config=self.config[service])

        return grpc.unary_unary_rpc_method_handler(
            func, request_deserializer=None, response_serializer=None)

def _fixer(wrapper):
    def decorator(f):
        @wraps(f)
        @wrapper
        def func(*args, **kwargs):
            return f(*args, **kwargs)
        return func
    return decorator

@_fixer(REQUEST_TIME.time())
def proxy_method(request, context, service, method, config):
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
    :type config: dict
    :return: Responce from the target services.
    :rtype: binary
    '''
    try:
        NUMBER_OF_PROCESSES.inc()
        
        metadata = dict(context.invocation_metadata())

        routing = config
        if 'match' in config:
            for item in config['match']:
                is_ok = True
                if 'headers' not in item:
                    is_ok = False
                else:
                    for header in item['headers']:
                        if header not in metadata \
                           or item['headers'][header]['exact'] != metadata[header]:
                            is_ok = False
                if is_ok:
                    routing = item

        host, response = _BALANCER_NAME_TO_CLASS[routing['loadBalancer']['type']](
            routing['hosts']).sent(
            request, context.invocation_metadata(), service, method)

        logging.info(f'redirect to {host}')
        logging.info('response data.')
    except:
        pass
    finally:
        NUMBER_OF_PROCESSES.dec()
    return response
