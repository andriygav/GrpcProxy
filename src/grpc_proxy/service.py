import grpc
import time
import yaml
import argparse
import logging
from functools import partial
from concurrent import futures
from grpc_reflection.v1alpha import reflection

from configobj import ConfigObj


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d %(levelname)s:%(funcName)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

MAX_MSG_LENGTH = 100 * 1024 * 1024
_ONE_DAY_IN_SECONDS = 60 * 60 * 24

class LoadBalancer(object):
    def __init__(self, adresses=[]):
        self.adresses = adresses
        
    def sent(self, request, metadata, service, method):
        raise NotImplementedError
        
class PeekFirst(LoadBalancer):
    def sent(self, request, metadata, service, method):
        acc_host = None
        response = None
        for host in self.adresses:
            channel = grpc.insecure_channel(
                host, options=[('grpc.max_send_message_length', MAX_MSG_LENGTH),
                               ('grpc.max_message_length', MAX_MSG_LENGTH),
                               ('grpc.max_receive_message_length', MAX_MSG_LENGTH)],)
            
            stub = channel.unary_unary(
                f'/{service}/{method}', request_serializer=None, response_deserializer=None)
            
            try:
                logging.info(f'{host} request')
                response = stub.future(request, metadata=metadata).result(None)
            except grpc.RpcError as e:
                logging.info(f'{host}: {e.code()}')
            else:
                acc_host = host
                break
        return acc_host, response
            
def proxy_method(request, context, service, method, config):
    metadata = dict(context.invocation_metadata())
    
    routing = config
    if 'match' in config:
        for item in config['match']:
            is_ok = True
            if 'headers' not in item:
                is_ok = False
            else:
                for header in item['headers']:
                    if header not in metadata or item['headers'][header]['exact'] != metadata[header]:
                        is_ok = False
            if is_ok:
                routing = item
    
    host, response = PeekFirst(routing['hosts']).sent(
        request, context.invocation_metadata(), service, method)
    
    logging.info(f'redirect to {host}')
    logging.info('response data.')
    return response
    
def add_to_server(config, server):
    services_hanldlers = []
    for item1 in config:
        service = item1['service']
        rpc_method_handlers = dict()
        for item2 in item1['methods']:
            method = item2['name']
            func = partial(proxy_method, service=service, method=method, config=item2)
            rpc_method_handlers[method] = grpc.unary_unary_rpc_method_handler(
                func, request_deserializer=None, response_serializer=None)
        services_hanldlers.append(grpc.method_handlers_generic_handler(service, rpc_method_handlers))
    server.add_generic_rpc_handlers(services_hanldlers)
        

def serve(config, setup):
    logging.warning('initialize service')

    server = grpc.server(
        futures.ThreadPoolExecutor(
            max_workers=int(config['service']['max workers'])
        ),
        options=[('grpc.max_send_message_length', MAX_MSG_LENGTH),
                 ('grpc.max_message_length', MAX_MSG_LENGTH),
                 ('grpc.max_receive_message_length', MAX_MSG_LENGTH)]
    )
    add_to_server(setup, server)

    server.add_insecure_port(config['service']['port'])

    server.start()

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)

def start():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='path to the config.cfg file')
    parser.add_argument('setup', help='path to the setup.yaml file')
    namespace = parser.parse_args()
    argv = vars(namespace)

    config = ConfigObj(infile=argv['config'], encoding='utf-8')

    with open(argv['setup']) as f:
    	setup = yaml.safe_load(f)

    serve(config, setup)


if __name__ == '__main__':
    start()
