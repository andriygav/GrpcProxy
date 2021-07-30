#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
The :mod:`grpc_proxy.service` contains functions:

- :func:`grpc_proxy.service.proxy_method`
- :func:`grpc_proxy.service.add_to_server`
- :func:`grpc_proxy.service.start`
'''
from __future__ import print_function
__docformat__ = 'restructuredtext'

import time
import json
import logging
import argparse
from functools import partial
from concurrent import futures

import grpc
import yaml
from configobj import ConfigObj
from prometheus_client import start_http_server, Counter
from python_grpc_prometheus.prometheus_server_interceptor import (
    PromServerInterceptor,)

from .balancer import RandomChoice, PeakFirst

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s:%(funcName)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
    )

MAX_MSG_LENGTH = 100 * 1024 * 1024
_ONE_DAY_IN_SECONDS = 60 * 60 * 24

# available balancer type
_BALANCER_NAME_TO_CLASS = {
    'peak_first': PeakFirst,
    'random': RandomChoice
}

def proxy_method(request, context, service, method, config):
    r'''
    Prototype for gRPC proxy method.

    :param request: Binary request without deserialisation.
    :type request: binary
    :param context: A gRPC service contex. 
        For more details read 
        https://grpc.github.io/grpc/python/grpc.html#service-side-context.
    :type context: ???
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
    return response
    
def add_to_server(config, server):
    r'''
    Generate proxy service handlers from the given config.
    
    :param config: Configuration dictionary from the setup.yaml file.
    :type config: dict
    :param server: AInitialised server without handlers.
    :type server: ???
    '''
    services_hanldlers = []
    for item1 in config:
        service = item1['service']
        rpc_method_handlers = dict()
        for item2 in item1['methods']:
            method = item2['name']
            func = partial(
                proxy_method, service=service, method=method, config=item2)
            rpc_method_handlers[method] = grpc.unary_unary_rpc_method_handler(
                func, request_deserializer=None, response_serializer=None)
        services_hanldlers.append(
            grpc.method_handlers_generic_handler(service, rpc_method_handlers))
    server.add_generic_rpc_handlers(services_hanldlers)

def start():
    r'''
    Setup and initialise service for proxing.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='path to the config.cfg file')
    parser.add_argument('setup', help='path to the setup.yaml file')
    namespace = parser.parse_args()
    argv = vars(namespace)

    config = ConfigObj(infile=argv['config'], encoding='utf-8')

    with open(argv['setup']) as f:
    	setup = yaml.safe_load(f)

    logging.info(
        f'initialize service with setup file:\n{json.dumps(setup, indent=2)}')

    server = grpc.server(
        futures.ThreadPoolExecutor(
            max_workers=int(config['service']['max workers']),
        ),
        options=[('grpc.max_send_message_length',    MAX_MSG_LENGTH),
                 ('grpc.max_message_length',         MAX_MSG_LENGTH),
                 ('grpc.max_receive_message_length', MAX_MSG_LENGTH)],
        interceptors=(PromServerInterceptor(),) 
    )
    add_to_server(setup, server)
    server.add_insecure_port(config['service']['port'])
    logging.info(
        f'service start on port={config["service"]["port"]} '
        f'and working with {config["service"]["max workers"]} threads')

    start_http_server(int(config['prometheus']['port']))
    server.start()

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    start()
