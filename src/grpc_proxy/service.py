#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
The :mod:`grpc_proxy.service` contains functions:

- :func:`grpc_proxy.service.start`
'''
from __future__ import print_function
__docformat__ = 'restructuredtext'

import time
import json
import logging
import argparse
from concurrent import futures

import grpc
import yaml
from configobj import ConfigObj
from prometheus_client import start_http_server
from python_grpc_prometheus.prometheus_server_interceptor import (
    PromServerInterceptor,)

from .interceptors import ProxyInterceptor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s:%(funcName)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
    )

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

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
    options = [(f'grpc.{key}', int(config['grpc'][key])) for key in config['grpc']]
    logging.info(
        f'configuration file:\n{json.dumps(config, indent=2)}')

    with open(argv['setup']) as f:
    	setup = yaml.safe_load(f)

    logging.info(
        f'initialize service with setup file:\n{json.dumps(setup, indent=2)}')

    
    server = grpc.server(
        futures.ThreadPoolExecutor(
            max_workers=int(config['service']['max workers']),
        ),
        options=options,
        interceptors=(
            PromServerInterceptor(), 
            ProxyInterceptor(setup['routingRules'], options)) 
    )

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
