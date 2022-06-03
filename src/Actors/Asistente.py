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
from time import gmtime

from flask import Flask, request
from matplotlib import get_backend
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

from DirectoryOps import search_agent


__author__ = 'raul'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--open',
                    help="Define si el servidor est abierto al exterior o no",
                    action='store_true',
                    default=False)
parser.add_argument('--dir',
                    default=None,
                    help="Direccion del servicio de directorio")
parser.add_argument('--port',
                    type=int,
                    help="Puerto de comunicacion del agente")
parser.add_argument('--verbose',
                    help="Genera un log de la comunicacion del servidor web",
                    action='store_true',
                    default=False)
                    
# parsing de los parametros de la linea de comandos
args = parser.parse_args()

if args.dir is None:
    raise NameError('A Directory Service addess is needed')
else:
    diraddress = args.dir

# Configuration stuff
if args.port is None:
    port = 9002
else:
    port = args.port

if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

print('DS Hostname =', hostaddr)

# Flask stuff
app = Flask(__name__)

# Configuration constants and variables
agn = Namespace("http://www.agentes.org#")

# Configuration of the namespace of comercio-electronico ontology
CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# Contador de mensajes
mss_cnt = 0

# Datos del Agente
Asistente = Agent('Asistente',
                       CEO.Asistente,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

def buscar_productos():
    ncategorias = int(input("Introduce la cantidad de categorias de productos que te interesan:"))
    print("Introduce las categorias de productos que te interesan:")
    print("\tFormato: categoria(str) cantidad(int) precio_min(int) precio_max(int)")

    # Crea el grafo de la acción BuscarProductos
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    # Crea la Acción BuscarProductos
    bp = CEO.buscarproductos
    gm.add((bp, RDF.type, CEO.BuscarProductos))
    gm.add((CEO.BuscarProductos, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    # Añade la Busqueda al grafo
    b = CEO.Busqueda
    gm.add((b, RDF.type, CEO.Busqueda))
    gm.add((bp, CEO.busca, b))

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
    
    # print(gm.serialize(format='turtle'))

    BuscadorProductos = search_agent(CEO.BuscadorProductos, Asistente, ServicioDirectorio)

    msg = build_message(gm,
                        perf=ACL.request,
                        sender=Asistente.uri,
                        receiver=BuscadorProductos.uri,
                        content=bp)    

    gr = send_message(msg, BuscadorProductos.address)

    return gr
        
def do(value):
    if value == 1:
        gr = Graph()
        gr = buscar_productos()
        print('\n' + 'Las ofertas de productos son:\n ')
        for s, p, o in gr.triples((None, RDF.type, CEO.Oferta)):
            precio = gr.value(s, CEO.precio)
            
            length = len(s)
            name = s[76:length]
            
            print(name + ' con precio: ' + precio + '€')
        print('\n')
        

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
    