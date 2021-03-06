# -*- coding: utf-8 -*-
"""

Esqueleto de agente usando los servicios web de Flask

/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""

import logging
from multiprocessing import Process, Queue
import socket
from SPARQLWrapper import SPARQLWrapper
import argparse

from flask import Flask, request, render_template
from rdflib import Graph, RDF, Namespace, RDFS, Literal
from rdflib.namespace import FOAF

from AgentUtil.ACL import ACL
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.ACLMessages import *
from AgentUtil.Logging import config_logger
from AgentUtil.DSO import DSO
from AgentUtil.Util import gethostname

from decimal import Decimal
from multiprocessing import Process
from Agentes.GestorEnvios import GestorEnvios

from DirectoryOps import register_agent, search_agent, unregister_agent


__author__ = 'adria'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--dir',
                    default=None,
                    help="Direccion del servicio de directorio")
parser.add_argument('--open',
                    help="Define si el servidor esta abierto al exterior o no",
                    action='store_true',
                    default=False)
parser.add_argument('--port',
                    type=int,
                    help="Puerto de comunicacion del agente")
parser.add_argument('--verbose',
                    help="Genera un log de la comunicacion del servidor web",
                    action='store_true',
                    default=False)

# Logging
logger = config_logger(level=1)

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

if args.dir is None:
    raise NameError('A Directory Service addess is needed')
else:
    diraddress = args.dir

# Configuration stuff
if args.port is None:
    port = 9001
else:
    port = args.port

if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

print('DS Hostname =', hostaddr)

agn = Namespace("http://www.agentes.org#")

CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente
GestorProductosExternos = Agent('GestorProductosExternos',
                       CEO.GestorProductosExternos,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

cola1 = Queue()

# Flask stuff
app = Flask(__name__)

if not args.verbose:
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.ERROR)


def gestionarActualizacion(ge):
    
    print(ge.serialize(format='turtle'))
    
    gmB = Graph()
    gmB.namespace_manager.bind('rdf', RDF)
    gmB.namespace_manager.bind('ceo', CEO)
    
    bpB = CEO.ActualizarInformacionProductos
    gmB.add((bpB, RDF.type, CEO.ActualizarInformacionProductos))
    gmB.add((CEO.ActualizarInformacionProductos, RDFS.subClassOf, CEO.Accion))
    gmB.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))
    
    gmE = Graph()
    gmE.namespace_manager.bind('rdf', RDF)
    gmE.namespace_manager.bind('ceo', CEO)
    
    bpE = CEO.ActualizarInformacionProductos
    gmE.add((bpE, RDF.type, CEO.ActualizarInformacionProductos))
    gmE.add((CEO.ActualizarInformacionProductos, RDFS.subClassOf, CEO.Accion))
    gmE.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))
    
    for s, p, o in ge.triples((None, RDF.type, CEO.Producto)):
        gmB.add((s, RDF.type, CEO.Producto))
        for ss, pp, oo in ge.triples((s,None,None)):
            length = len(pp)
            name = pp[67:length]
            if name in ['cantidad','categoria','descripcion','nombre','precio','restricciones_devolucion','tiene_modelo','valoracion_media']: 
                gmB.add((ss, pp, oo))
            else:
                gmE.add((ss, pp, oo))

    BuscadorProductos = search_agent(CEO.BuscadorProductos, GestorProductosExternos, ServicioDirectorio)

    msgB = build_message(gmB, perf=ACL.request,
                        sender=GestorProductosExternos.uri,
                        receiver=BuscadorProductos.uri,
                        content=bpB)

    send_message(msgB, BuscadorProductos.address)
    
    GestorEnvios = search_agent(CEO.GestorEnvios, GestorProductosExternos, ServicioDirectorio)
    
    msgE = build_message(gmE, perf=ACL.request,
                        sender=GestorProductosExternos.uri,
                        receiver=BuscadorProductos.uri,
                        content=bpE)

    send_message(msgE, GestorEnvios.address)
    
    return

        

@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml')

    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if not msgdic:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(),
                           ACL['not-understood'],
                           sender=GestorProductosExternos.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorProductosExternos.uri)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.ActualizarInformacionProductos:
                ab1 = Process(target=gestionarActualizacion, args=(gm,))
                ab1.start()
                gr = build_message( Graph(),
                                ACL['confirm'],
                                sender=GestorProductosExternos.uri)
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorProductosExternos.uri)
            
    return gr.serialize(format='xml')


@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    shutdown_server()
    return "Parando Servidor"
    
    
def setup():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

def tidyup():
    """
    Acciones previas a parar el agente

    """
    unregister_agent(GestorProductosExternos, ServicioDirectorio)
    pass

if __name__ == '__main__': 
    setup()
    
    register_agent(GestorProductosExternos, ServicioDirectorio, logger)

    print('\nRunning on https://' + str(hostname) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    tidyup()
    print('The End')
