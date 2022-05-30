import json
from socket import socket, error
import threading
import time
from typing import Dict
from commands import *

ServerSocket = socket()
host = '127.0.0.1'
port = 1233
try:
    ServerSocket.bind((host, port))
except error as e:
    print(str(e))
print('Waiting for a Connection..')
ServerSocket.listen(5)
connections = []

data_lock = threading.Lock()
ownership: Dict[str, socket] = {}
data = {"test": "test-object"}
listeners: Dict[str, List[socket]] = {}


def send_dict(client, d: Dict):
    client.send(json.dumps(d).encode("utf-8"))


def broadcast(command, source, targets: Optional[List[socket]] = None):
    if targets is None:
        targets = connections
    for i in targets:
        if i != source:
            command.client = i
            command.send()


def debug_server():
    print("Ownership")
    for k, v in ownership.items():
        print(f"\t{k} : {v.getsockname()}")
    print("Data")
    for k, v in data.items():
        print(f"\t{k} : {v}")
    print("Listeners")
    for k, v in listeners.items():
        print(f"\t{k} : {[x.getsockname() for x in v]}")


def threaded_client(client, _connections):
    while True:
        response = Response(client.recv(1024))
        print(response)

        if (response.command is CommandList.RefuseKeyList or response.command is CommandList.RefuseNewKey or
                response.command is CommandList.RefuseObjectRequest):
            print("Unknown client command")

        elif response.command is CommandList.ReceiveKeyList:
            print(f"Key list received, {response.key_list}")
            with data_lock:
                ownership.update({x: client for x in response.key_list})
                data.update({x: None for x in response.key_list})
                listeners.update({x: [] for x in response.key_list})
                debug_server()
            broadcast(ReceiveKeyListCommand(None, list(data.keys())), client)

        elif response.command is CommandList.AddKey:
            print(f"Request to add key {response.key}")
            with data_lock:
                if response.key in ownership:
                    RefuseKeyCommand(client, response.key).send()
                    continue
                ownership[response.key] = client
                data[response.key] = None
                listeners[response.key] = []
                debug_server()
            broadcast(AddKeyCommand(None, response.key), client)

        elif response.command is CommandList.DeleteKey:
            print(f"Request to delete key: {response.key}")
            with data_lock:
                del ownership[response.key]
                del data[response.key]
                del listeners[response.key]
                debug_server()
            broadcast(DeleteKeyCommand(None, response.key), client)

        elif response.command is CommandList.ReceiveObject:
            print(f"Object {response.key} received, broadcasting it to every listener")
            with data_lock:
                data[response.key] = response.obj
                debug_server()
            broadcast(ReceiveObjectCommand(None, response.key, response.obj), client, listeners[response.key])
            listeners[response.key].clear()

        elif response.command is CommandList.RequestObject:
            print(f"Client requests object [{response.key}]")
            try:
                if data[response.key] is not None:
                    print("Data already cached, sending with request")
                    ReceiveObjectCommand(client, response.key, data[response.key]).send()
                else:
                    print("Data not found. Requesting from the source, adding client to the listener list")
                    RequestObjectCommand(ownership[response.key], response.key).send()
                    with data_lock:
                        listeners[response.key].append(client)
            except KeyError:
                print("Object not found")
                RefuseObjectRequestCommand(client, response.key)
            debug_server()


def threaded_send(client):
    while True:
        client.send("Server".encode("utf-8"))
        time.sleep(1)


while True:
    Client, address = ServerSocket.accept()
    print("New client connected!")
    connections.append(Client)
    ReceiveKeyListCommand(Client, list(data.keys())).send()
    threading.Thread(target=threaded_client, args=(Client, connections)).start()
