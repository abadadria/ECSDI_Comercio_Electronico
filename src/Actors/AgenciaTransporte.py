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
from numpy import prod
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

import random

from DirectoryOps import register_agent, unregister_agent


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
    port = 9050
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
AgenciaTransporte = Agent('AgenciaTransporte',
                       CEO.AgenciaTransporte,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# precio envio menos de 5 productos, precio envio entre 5 y 15 prodcutos, precio envios mas de 15 productos
tarifaPrecio = [[5, 15 ,30],
                [3, 18 ,40],
                [7, 12 ,40]]

cola1 = Queue()

# Flask stuff
app = Flask(__name__)

if not args.verbose:
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.ERROR)


def tarifaAgencia(graph):
    gm = Graph()
    gm.namespace_manager.bind('ceo', CEO)
    # Construir el mensaje
    respuestaInfo = CEO.RespuestaInformacionTransporteEnvio
    gm.add((respuestaInfo, RDF.type, CEO.RespuestaInformacionTransporteEnvio))
    gm.add((CEO.RespuestaInformacionTransporteEnvio, RDFS.subClassOf, CEO.Respuesta))
    precio = random.choice(random.choice(tarifaPrecio))
    gm.add((respuestaInfo, CEO.precio, Literal(precio)))
    print("Respondiendo a solicitud de tarifa con un precio de: " + str(precio) + "???")
    return gm
    


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
                           sender=AgenciaTransporte.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=AgenciaTransporte.uri)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.SolicitarInformacionTransporteEnvio:
                gr = tarifaAgencia(gm)
            elif accion == CEO.ContratarEnvio:
                # La agencia se encarga del envio (fuera del alcance del problema)
                print("Se ha contratado un envio")
                gr = build_message( Graph(),
                                ACL['confirm'],
                                sender=AgenciaTransporte.uri)
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=AgenciaTransporte.uri)
            
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
    unregister_agent(AgenciaTransporte, ServicioDirectorio)
    pass


if __name__ == '__main__':
    setup()
    
    register_agent(AgenciaTransporte, ServicioDirectorio, logger)

    print('\nRunning on http://' + str(hostaddr) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)
    
    tidyup()
    print('The End')
