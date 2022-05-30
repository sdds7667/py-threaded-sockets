from socket import socket, error
import threading
import time
import sys
import uuid

from commands import *

music = {}
response_lock = threading.Lock()
sent_requests: List[Command] = []
data_list = []
my_music = {}


def send_dict(d: Dict):
    ClientSocket.send(json.dumps(d).encode("utf-8"))


def generate_music_list():
    global my_music
    my_music.clear()
    my_music = {str(uuid.uuid4()): x for x in data_list}


def find_request_by_key(key: str):
    print(key)
    for i in sent_requests:
        if isinstance(i, RequestObjectCommand) and i.payload.get("key") == key:
            return i
    return None


def threaded_client(client: socket):
    while True:
        response = Response(client.recv(1024))
        if response.command is CommandList.ReceiveObject:
            # should come as a response for a request
            with response_lock:
                print(response.key)
                request = find_request_by_key(response.key)
                if request is None:
                    print("Received an object that was not requested")
                else:
                    request.response = response
                    print("response received!")
                    sent_requests.remove(request)
        elif response.command is CommandList.RequestObject:
            ReceiveObjectCommand(client, response.key, my_music[response.key]).send()
        elif response.command is CommandList.SendKeyList:
            ReceiveKeyListCommand(client, list(my_music.keys())).send()
        elif response.command is CommandList.ReceiveKeyList:
            music.clear()
            with response_lock:
                music.update({x: None for x in response.key_list if x not in my_music})
        elif response.command is CommandList.DeleteKey:
            with response_lock:
                music.pop(response.key)
        elif response.command is CommandList.AddKey:
            with response_lock:
                music[response.key] = None
        elif response.command is CommandList.RefuseKeyList:
            # reshuffle the key list
            with response_lock:
                generate_music_list()
                SendKeyListCommand(client, list(my_music.keys())).send()
        elif response.command is CommandList.RefuseNewKey:
            with response_lock:
                request = find_request_by_key(response.key)
                if request is None:
                    print("Refused a key that does not exist")
                else:
                    request.response = response
                sent_requests.remove(request)

        elif response.command is CommandList.RefuseObjectRequest:
            with response_lock:
                request = find_request_by_key(response.key)
                if request is None:
                    print("Refused an object request that does not exist")
                else:
                    request.response = response
                sent_requests.remove(request)


def handle_menu(option: int):
    if option == 1:
        for i in music:
            print(i)

    elif option == 2:
        required_key = None
        key = input("required key")
        for k, v in music.items():
            if k == key:
                required_key = k
                break
            if k.endswith(key):
                if input(f"Did you mean {k}[Y/N]?") == "Y":
                    required_key = k
                    break

        if required_key is None:
            return
        # send request for key
        request = RequestObjectCommand(ClientSocket, required_key)
        request.send()
        sent_requests.append(request)

        while True:
            time.sleep(.3)
            with response_lock:
                if request.response is None:
                    continue
                else:
                    if request.response.command is RefuseObjectRequestCommand:
                        print("Key not found on the server")
                    else:
                        music[request.response.key] = request.response.obj
                        print(f"Received object: {music[request.response.key]}")
                        break

    elif option == 3:
        ReceiveKeyListCommand(ClientSocket, list(my_music.keys())).send()


if __name__ == '__main__':
    with open(sys.argv[1], "r") as f:
        data_list = [x.strip() for x in f.readlines()]
        generate_music_list()

    ClientSocket = socket()
    host = '127.0.0.1'
    port = 1233

    try:
        ClientSocket.connect((host, port))
    except error as e:
        print(str(e))

    incoming_messages = []
    threading.Thread(target=threaded_client, args=(ClientSocket,)).start()
    while True:
        print("1) Show all keys")
        print("2) Receive by key")
        print("3) Send our music")
        try:
            handle_menu(int(input("> ")))
        except ValueError:
         print("NaN")
