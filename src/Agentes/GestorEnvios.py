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
    port = 9030
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
GestorEnvios = Agent('GestorEnvios',
                       CEO.GestorEnvios,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# Global triplestore graph
products_graph = Graph()
pedidos_envio_graph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)

if not args.verbose:
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.ERROR)

def gestionarEnvioProceso(ge):
    print(ge.serialize(format='turtle'))

    gr = Graph()
    gr.namespace_manager.bind('ceo', CEO)

    for lp in ge.subjects(RDF.type, CEO.LineaProducto):
        producto = ge.value(lp, CEO.tiene_producto)
        gestion_envio = products_graph.value(producto, CEO.gestion_envio)
        if str(gestion_envio) == 'externa':
            vendedor = products_graph.value(producto, CEO.vendedor)
            vendedor_addr = products_graph.value(vendedor, CEO.direccion)
            
        else:
            pass



def gestionarEnvio(ge):
    p1 = Process(taget=gestionarEnvioProceso, args=(ge,))
    p1.start()
    
    return build_message(Graph(),
                         ACL.agree,
                         sender=GestorEnvios.uri)


def gestionarActualizacion(ge): 
    print("actualizando")   
    print(ge.serialize(format='turtle'))
    for s, p, o in ge.triples((None, RDF.type, CEO.Producto)):
        
        boolean = False
        for ss, pp, oo in products_graph.triples((s,None,None)):
            boolean = True
            atributo = ge.value(s, pp)
            if atributo != None and atributo != RDF.type: 
                products_graph.set((ss, pp, Literal(atributo)))
                products_graph.set((ss, RDF.type, CEO.Producto))
        
        # el producto no existia
        if not boolean:
            for ss, pp, oo in ge.triples((s,None,None)):
                products_graph.add((ss, pp, oo))
    
    ofile = open('info_prod_env.ttl', "w")
    ofile.write(products_graph.serialize(format='turtle'))
    ofile.close()        

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
                           sender=GestorEnvios.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorEnvios.uri)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.RealizarEnvio:
                gestionarEnvio(gm)
                gr = build_message( Graph(),
                                ACL['agree'],
                                sender=GestorEnvios.uri)
            elif accion == CEO.ActualizarInformacionProductos:
                gestionarActualizacion(gm)
                
                gr = build_message( Graph(),
                                ACL['confirm'],
                                sender=GestorEnvios.uri)
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorEnvios.uri)
            
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
    products_graph.parse('info_prod_env.ttl', format='turtle')
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

def tidyup():
    """
    Acciones previas a parar el agente

    """
    unregister_agent(GestorEnvios, ServicioDirectorio)
    pass

if __name__ == '__main__': 
    setup()
    
    register_agent(GestorEnvios, ServicioDirectorio, logger)

    print('\nRunning on https://' + str(hostname) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    tidyup()
    print('The End')
