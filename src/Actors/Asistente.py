# -*- coding: utf-8 -*-
"""
filename: Asistente

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""

from multiprocessing import Process, Queue
import logging
import argparse

from flask import Flask, request
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import FOAF, RDF

from AgentUtil.ACL import ACL
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.ACLMessages import build_message, send_message, get_message_properties
from AgentUtil.Agent import Agent
from AgentUtil.Logging import config_logger
from AgentUtil.DSO import DSO
from AgentUtil.Util import gethostname
import socket
import requests
import json


__author__ = 'raul'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--b', help="Host del agente Buscador Productos")

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

if args.b is None:
    print("Usage: python3 Asistente.py --b http://<IP_Buscador>:<Port_Buscador>")
    exit()
else:
    bhost = args.b

def mensaje_busqueda(list):
    print(json.dumps(list))
    return requests.get(bhost + "/buscar", json=json.dumps(list))

def buscar_productos():
    ncategorias = int(input("Introduce la cantidad de categorias de productos que te interesan:"))
    print("Introduce las categorias de productos que te interesan:")
    print("\tFormato: categoria(str) cantidad(int) precio_min(int) precio_max(int)")
    
    

    for i in range(ncategorias):
        linea = input().split();
    
    res = mensaje_busqueda(list)
        
def do(value):
    if value == 1:
        buscar_productos()        

if __name__ == '__main__':
    print("Bienvenido a el Asistente de Comercio Electronico")
    
    while 1:
        print("Que acción deseas realizar?")
        print("[1] Buscar productos")
        print("[0] Cerrar")
        value = int(input())
        
        if value == 0:
            exit()
        else:
            do(value)
    