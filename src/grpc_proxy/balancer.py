import grpc
import logging
import random

class LoadBalancer(object):
    def __init__(self, adresses=[]):
        self.adresses = adresses
        
    def sent(self, request, metadata, service, method):
        raise NotImplementedError

class RandomChoice(LoadBalancer):
    def sent(self, request, metadata, service, method):
        acc_host = None
        response = None
        host = random.choice(self.adresses)

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
            raise e
        else:
            acc_host = host

        return acc_host, response
        
class PeakFirst(LoadBalancer):
    def sent(self, request, metadata, service, method):
        acc_host = None
        response = None

        last_error = None

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
                last_error = e
            else:
                acc_host = host
                break

        if acc_host is None:
            raise last_error

        return acc_host, response