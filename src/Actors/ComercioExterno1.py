# -*- coding: utf-8 -*-
"""
filename: Comercio Externo1

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""

from multiprocessing import Process, Queue
import logging
import argparse

from flask import Flask, request
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal
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


__author__ = 'adria'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--b', help="Host del agente Buscador Productos")

# parsing de los parametros de la linea de comandos
args = parser.parse_args()


if args.b is None:
    print("Usage: python3 ComercioExterno1.py --b hostNameBuscador <ejemplo: 127.0.0.1>")
    exit()
else:
    hostaddrBuscador = args.b

# Configuration stuff
port = 9003

hostname = '0.0.0.0'
hostaddr = gethostname()

print('DS Hostname =', hostaddr)

# Flask stuff
app = Flask(__name__)

# Configuration constants and variables
agn = Namespace("http://www.agentes.org#")

portBuscador = 9010

AgenteBuscadorProductos = Agent('AgenteSimple',
                       agn.AgenteSimple,
                       'http://%s:%d/comm' % (hostaddrBuscador, portBuscador),
                       'http://%s:%d/Stop' % (hostaddrBuscador, portBuscador))

# Contador de mensajes
mss_cnt = 0

# Datos del Agente
ComercioExterno1 = Agent('AgentePersonal',
                       agn.AgentePersonal,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))



# Configuration of the namespaprint(cnt)ce of comercio-electronico ontology
CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

def actualizar_info_productos():
    nproductos = int(input("Introduce la cantidad de productos que vas a actualizar:"))
    print("Introduce el nombre del producto y sus atributos a cambiar (insertar '-' si no se desea cambiar")
    print("\tFormato: nombre(str) categoria(str) descripcion(str) restricciones_devolucion(str)")
    
    # Crea el grafo de la acción ActualizarInformacionProductos
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    # Crea la Acción ActualizarInformacionProductos
    bp = CEO.ActualizarInformacionProductos
    gm.add((bp, RDF.type, CEO.ActualizarInformacionProductos))
    gm.add((CEO.ActualizarInformacionProductos, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    for i in range(nproductos):
        # Lee una linea de terminal que sorresponde con un Producto (no entero)
        atributosProducto = input().split()
        # Añade la LineaBusqueda al grafo
        p = CEO[atributosProducto[0]]
        gm.add((p, RDF.type, CEO.Producto))
        gm.add((p, CEO.categoria, Literal(atributosProducto[1])))
        gm.add((p, CEO.descripcion, Literal(atributosProducto[2])))
        gm.add((p, CEO.restricciones_devolucion, Literal(atributosProducto[3])))
    
    print(gm.serialize(format='turtle'))

    msg = build_message(gm, perf=ACL.request,
                        sender=ComercioExterno1.uri,
                        receiver=AgenteBuscadorProductos.uri,
                        content=bp)

    gr = send_message(msg, AgenteBuscadorProductos.address)

    return gr
        
def do(value):
    if value == 1:
        actualizar_info_productos()
        """Comprobar ack """
        print('\n' + 'El mensaje se ha enviado:\n ')
        

if __name__ == '__main__':
    print("Bienvenido a ComercioExterno1")
    
    while 1:
        print("Que acción deseas realizar?")
        print("[1] Actualizar información productos")
        print("[0] Cerrar")
        value = int(input())
        
        if value == 0:
            exit()
        else:
            do(value)
    