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


__author__ = 'raul'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--b', help="Host del agente Buscador Productos")

# parsing de los parametros de la linea de comandos
args = parser.parse_args()
'''
if args.b is None:
    print("Usage: python3 Asistente.py --b http://<IP_Buscador>:<Port_Buscador>")
    exit()
else:
    bhost = args.b
'''
# Configuration of the namespace of comercio-electronico ontology
CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

def buscar_productos():
    ncategorias = int(input("Introduce la cantidad de categorias de productos que te interesan:"))
    print("Introduce las categorias de productos que te interesan:")
    print("\tFormato: categoria(str) cantidad(int) precio_min(int) precio_max(int)")
    
    # Crea el grafo de la acción BuscarProductos
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    # Añade la Busqueda al grafo
    b = CEO.busqueda
    gm.add((b, RDF.type, CEO.Busqueda))

    for i in range(ncategorias):
        # Lee una linea de terminal que sorresponde con una LineaBusqueda
        linea = input().split()
        # Añade la LineaBusqueda al grafo
        l = CEO["lineabusqueda" + str(i)]
        gm.add((l, RDF.type, CEO.LineaBusqueda))
        gm.add((CEO.LineaBusqueda, RDFS.subClassOf, CEO.Linea))
        gm.add((l, CEO.cantidad, Literal(int(linea[1]))))
        gm.add((b, CEO.tiene_linea_busqueda, l))
        gm.add((l, CEO.categoria, Literal(linea[0])))
        gm.add((l, CEO.precio_min, Literal(int(linea[2]))))
        gm.add((l, CEO.precio_max, Literal(int(linea[3]))))
    
    print(gm.serialize(format='turtle'))

    gr = send_message(
        build_message(gm, perf=ACL.request,
                      sender="Asistente",
                      receiver="Buscador_productos",
                      content="Asistente1-BuscarProductos"),
            'http://*********:****/buscar')
        
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
    