# -*- coding: utf-8 -*-
"""
filename: SimpleDirectoryAgent

Antes de ejecutar hay que añadir la raiz del proyecto a la variable PYTHONPATH

Agente que lleva un registro de otros agentes

Utiliza un registro simple que guarda en un grafo RDF

El registro no es persistente y se mantiene mientras el agente funciona

Las acciones que se pueden usar estan definidas en la ontología
directory-service-ontology.owl


@author: javier
"""

from multiprocessing import Process, Queue
import argparse
import logging

from flask import Flask, request, render_template
from rdflib import Graph, RDF, Namespace, RDFS, Literal
from rdflib.namespace import FOAF

from AgentUtil.ACL import ACL
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.Logging import config_logger
from AgentUtil.DSO import DSO
from AgentUtil.Util import gethostname
import socket

__author__ = 'raul'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--verbose', help="Genera un log de la comunicacion del servidor web",
action='store_true',
                    default=False)
parser.add_argument('--open',
                    help="Define si el servidor est abierto al exterior o no",
                    action='store_true',
                    default=False)
parser.add_argument('--port',
                    type=int,
                    help="Puerto de comunicacion del agente")

# Logging
logger = config_logger(level=1)

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

# Configuration stuff
if args.port is None:
    port = 9000
else:
    port = args.port

if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

print('DS Hostname =', hostaddr)

# Directory Service Graph
dsgraph = Graph()

# Vinculamos todos los espacios de nombre a utilizar
CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

dsgraph.bind('acl', ACL)
dsgraph.bind('rdf', RDF)
dsgraph.bind('rdfs', RDFS)
dsgraph.bind('foaf', FOAF)
dsgraph.bind('dso', DSO)
dsgraph.bind('ceo', CEO)

agn = Namespace("http://www.agentes.org#")
ServicioDirectorio = Agent('ServicioDirectorio',
                       agn.Directory,
                       'http://%s:%d/Register' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))
app = Flask(__name__)

if not args.verbose:
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

mss_cnt = 0


@app.route("/register")
def register():
    """
    Entry point del agente que recibe los mensajes de registro
    La respuesta es enviada al retornar la funcion,
    no hay necesidad de enviar el mensaje explicitamente

    Asumimos una version simplificada del protocolo FIPA-request
    en la que no enviamos el mesaje Agree cuando vamos a responder

    :return:
    """

    def process_register():
        # Si la hay extraemos el nombre del agente (FOAF.name), el URI del agente
        # su direccion y su tipo

        logger.info('Peticion de registro')
        logger.info(gm.serialize(format='turtle'))

        agn_type = gm.value(subject=CEO.agente, predicate=RDF.type)
        agn_uri = gm.value(subject=CEO.agente, predicate=CEO.uri)
        agn_adr = gm.value(subject=CEO.agente, predicate=CEO.direccion)

        dsgraph.add((agn_adr, RDF.type, agn_type))
        dsgraph.add((agn_adr, CEO.uri, agn_uri))
        dsgraph.add((agn_adr, CEO.direccion, agn_adr))

        logger.info('Grafo del ServicioDirectorio')
        logger.info(dsgraph.serialize(format='turtle'))

        # Generamos un mensaje de respuesta
        return build_message(Graph(),
                             ACL.confirm,
                             sender=ServicioDirectorio.uri,
                             receiver=agn_uri,
                             msgcnt=mss_cnt)


    def process_unregister():
        agn_type = gm.value(subject=CEO.agente, predicate=RDF.type)
        agn_adr = gm.value(subject=CEO.agente, predicate=CEO.direccion)
        agn_uri = gm.value(subject=CEO.agente, predicate=CEO.uri)

        dsgraph.remove((agn_adr, RDF.type, agn_type))
        dsgraph.remove((agn_adr, CEO.uri, agn_uri))
        dsgraph.remove((agn_adr, CEO.direccion, agn_adr))

        logger.info('Grafo del ServicioDirectorio')
        logger.info(dsgraph.serialize(format='turtle'))
        
        # Generamos un mensaje de respuesta
        return build_message(Graph(),
                             ACL.confirm,
                             sender=ServicioDirectorio.uri,
                             receiver=agn_uri,
                             msgcnt=mss_cnt)


    def process_search():
        # Asumimos que hay una accion de busqueda que puede tener
        # diferentes parametros en funcion de si se busca un tipo de agente
        # o un agente concreto por URI o nombre
        # Podriamos resolver esto tambien con un query-ref y enviar un objeto de
        # registro con variables y constantes

        # Solo consideramos cuando Search indica el tipo de agente
        # Buscamos una coincidencia exacta
        # Retornamos el primero de la lista de posibilidades

        logger.info('Peticion de busqueda')

        agn_type = gm.value(subject=CEO.agente, predicate=RDF.type)
        rsearch = dsgraph.triples((None, RDF.type, agn_type))
        if rsearch is not None:
            agn = next(rsearch)

            gr = Graph()
            gr.namespace_manager.bind('rdf', RDF)
            gr.namespace_manager.bind('ceo', CEO)

            ra = CEO.RespuestaAgente
            gr.add((ra, RDF.type, CEO.RespuestaAgente))
            gr.add((CEO.RespuestaAgente, RDFS.subClassOf, CEO.Respuesta))
            gr.add((CEO.Respuesta, RDFS.subClassOf, CEO.Comunicacion))

            a = CEO.agente
            gr.add((a, RDF.type, agn_type))
            gr.add((agn_type, RDFS.subClassOf, CEO.Agente))
            gr.add((a, CEO.direccion, Literal(agn[0])))
            gr.add((a, CEO.uri, agn_type))
            gr.add((ra, CEO.con_agente, a))


            return build_message(gr,
                                 ACL.inform,
                                 sender=ServicioDirectorio.uri,
                                 msgcnt=mss_cnt,
                                 content=ra)

        else:
            # Si no encontramos nada retornamos un inform sin contenido
            return build_message(Graph(),
                                 ACL.inform,
                                 sender=ServicioDirectorio.uri,
                                 msgcnt=mss_cnt)

    global dsgraph
    global mss_cnt
    # Extraemos el mensaje y creamos un grafo con él
    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml')


    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if not msgdic:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(),
                           ACL['not-understood'],
                           sender=ServicioDirectorio.uri,
                           msgcnt=mss_cnt)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(),
                               ACL['not-understood'],
                               sender=ServicioDirectorio.uri,
                               msgcnt=mss_cnt)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']
            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Accion de registro
            if accion == CEO.RegistrarAgente:
                gr = process_register()
            # Accion de busqueda
            elif accion == CEO.BuscarAgente:
                gr = process_search()
            elif accion == CEO.DesregistrarAgente:
                gr = process_unregister()
            # No habia ninguna accion en el mensaje
            else:
                gr = build_message(Graph(),
                                   ACL['not-understood'],
                                   sender=ServicioDirectorio.uri,
                                   msgcnt=mss_cnt)
    mss_cnt += 1
 
    return gr.serialize(format='xml')


@app.route('/info')
def info():
    """
    Entrada que da informacion sobre el agente a traves de una pagina web
    """
    global dsgraph
    global mss_cnt

    return render_template('info.html', nmess=mss_cnt, graph=dsgraph.serialize(format='turtle'))


@app.route("/stop")
def stop():
    """
    Entrada que para el agente
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"


def tidyup():
    """
    Acciones previas a parar el agente

    """


if __name__ == '__main__':
    # Ponemos en marcha el servidor Flask
    app.run(host=hostname, port=port, debug=True)

    logger.info('The End')