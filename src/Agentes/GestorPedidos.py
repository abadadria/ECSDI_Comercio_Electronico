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

from DirectoryOps import register_agent, unregister_agent


__author__ = 'raul'

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
    port = 9020
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
n_pedidos = 0

# Datos del Agente
GestorPedidos = Agent('GestorPedidos',
                       CEO.GestorPedidos,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# Global triplestore graph
grafo_pedidos = Graph()

# Flask stuff
app = Flask(__name__)

if not args.verbose:
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.ERROR)

def cobrar_pedido():
    pass

def almacenar_pedido_cerrado():
    pass

def actualizar_informacion_productos():
    pass

@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """
    def crear_pedido():
        gr = Graph()
        gr.namespace_manager.bind('rdf', RDF)
        gr.namespace_manager.bind('ceo', CEO)

        p = CEO['pedido_' + str(n_pedidos)]
        gr.add((p, RDF.type, CEO.Pedido))
        gr.add(())
        pass
    

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml')

    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if not msgdic:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(),
                           ACL['not-understood'],
                           sender=GestorPedidos.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] == ACL.request:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.RealizarPedido:
                gr = crear_pedido()
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorPedidos.uri)
        elif msgdic['performative'] == ACL.inform:
            pass
        else:
            # Si no es un request ni un inform, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorPedidos.uri)
            
    return gr.serialize(format='xml')


def setup():
    pass

def tidyup():
    """
    Acciones previas a parar el agente

    """
    unregister_agent(GestorPedidos, ServicioDirectorio)

if __name__ == '__main__':
    setup()
    register_agent(GestorPedidos, ServicioDirectorio, logger)

    print('\nRunning on http://' + str(hostaddr) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)
    tidyup()
    print('The End')