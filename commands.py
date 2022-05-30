import json
from enum import Enum
from socket import socket
from typing import Dict, List, Optional

"""
 Clientul se conecteaza la server si primeste o lista de chei, fiecare cheie
identificand un obiect publicat pe server de clientii conectati;
○ Un client poate cauta un obiect pe server dupa cheie;
○ Server-ul mentine un dictionar cu asocierile dintre chei si clientul pe care se
gaseste obiectul corespunzator unei chei;
○ La primirea unei solicitari de regasire a unui obiect dupa cheie, server-ul
identifica pe ce client se afla obiectul si solicita transferarea continutului
obiectului respectiv de pe clientul care-l stocheaza;
○ In momentul primirii obiectului, server-ul il livreaza clientului care l-a solicitat;
○ Un client poate publica un nou obiect pe server prin trimiterea unei chei care
este asociata obiectului;
○ Server-ul verifica unicitatea cheii in functie de care accepta inregistrarea
obiectului in dictionar, notificand toti clientii conectati cu noua cheie
publicata;
○ Un client poate sterge o cheie de pe server publicata de el in prealabil, caz in
care server-ul va notifica toti clientii conectati pentru stergerea cheii
respective din lista.
"""


class CommandList(Enum):
    RequestObject = "request_object"
    ReceiveObject = "receive_object"

    ReceiveKeyList = "receive_key_list"
    SendKeyList = "send_key_list"

    RefuseKeyList = "refuse_key_list"
    RefuseNewKey = "refuse_key"
    RefuseObjectRequest = "refuse_object_request"

    AddKey = "add_key"
    DeleteKey = "delete_key"


class Response:
    command: CommandList
    key: str = None
    obj: str = None
    key_list: List[str] = None

    def __init__(self, response: bytes):
        d = json.loads(response.decode("utf-8"))
        self.command = CommandList(d["command"])
        self.key: str = d.get('key')
        self.obj: str = d.get('obj')
        self.key_list: List[str] = d.get('key_list')

    def __repr__(self):
        return f"<{self.command.name} key={self.key}; obj={self.obj}; key_list={self.key_list}>"


class Command:
    client: socket
    payload: Dict
    response: Response = None

    def __init__(self, client: Optional[socket], command: CommandList):
        self.client = client
        self.payload = {
            "command": command.value
        }

    def send(self):
        self.client.send(json.dumps(self.payload).encode("utf-8"))


class RequestObjectCommand(Command):
    def __init__(self, client: Optional[socket], key: str):
        super().__init__(client, CommandList.RequestObject)
        self.payload["key"] = key


class ReceiveKeyListCommand(Command):
    def __init__(self, client: Optional[socket], key_list: List[str]):
        super().__init__(client, CommandList.ReceiveKeyList)
        self.payload["key_list"] = key_list


class ReceiveObjectCommand(Command):
    def __init__(self, client: Optional[socket], key: str, obj: str):
        super().__init__(client, CommandList.ReceiveObject)
        self.payload["key"] = key
        self.payload["obj"] = obj


class SendKeyListCommand(Command):
    def __init__(self, client: Optional[socket], key_list: List[str]):
        super().__init__(client, CommandList.SendKeyList)
        self.payload["key_list"] = key_list


class RefuseKeyListCommand(Command):
    def __init__(self, client: Optional[socket]):
        super().__init__(client, CommandList.RefuseKeyList)


class RefuseKeyCommand(Command):
    def __init__(self, client: Optional[socket], key: str):
        super().__init__(client, CommandList.RefuseNewKey)
        self.payload["key"] = key


class RefuseObjectRequestCommand(Command):
    def __init__(self, client: Optional[socket], key: str):
        super().__init__(client, CommandList.RefuseObjectRequest)
        self.payload["key"] = key


class AddKeyCommand(Command):
    def __init__(self, client: Optional[socket], key: str):
        super().__init__(client, CommandList.AddKey)
        self.payload["key"] = key


class DeleteKeyCommand(Command):
    def __init__(self, client: Optional[socket], key: str):
        super().__init__(client, CommandList.DeleteKey)
        self.payload["key"] = key
