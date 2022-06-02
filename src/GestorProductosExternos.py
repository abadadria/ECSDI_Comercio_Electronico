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

from flask import Flask, request, render_template
from rdflib import Graph, RDF, Namespace, RDFS, Literal
from rdflib.namespace import FOAF

from AgentUtil.ACL import ACL
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.ACLMessages import build_message, send_message, get_message_properties
from AgentUtil.Logging import config_logger
from AgentUtil.DSO import DSO
from AgentUtil.Util import gethostname

from decimal import Decimal
from multiprocessing import Process


__author__ = 'adria'

# Configuration stuff
hostname = socket.gethostname()
port = 9011

agn = Namespace("http://www.agentes.org#")

CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

# Contador de mensajes
mss_cnt = 0

hostaddrBuscador = "adria-VirtualBox"
portBuscador = 9010

AgenteBuscadorProductos = Agent('AgenteSimple',
                       agn.AgenteSimple,
                       'http://%s:%d/comm' % (hostaddrBuscador, portBuscador),
                       'http://%s:%d/Stop' % (hostaddrBuscador, portBuscador))

# Datos del Agente
GestorProductosExternos = Agent('AgenteSimple',
                       agn.AgenteSimple,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Global triplestore graph
products_graph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)


def gestionarActualizacion(ge):
    print("gestionando actualización de productos")
    """
    De momento solo se puede cambiar la informacion que le corresponde al buscador de productos, ampliar en un futuro
    Ahora solo redirecciona, en un futuro tendra que separar la informacion y enviar varios mensajes
    """

    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)
    
    bp = CEO.ActualizarInformacionProductos
    gm.add((bp, RDF.type, CEO.ActualizarInformacionProductos))
    gm.add((CEO.ActualizarInformacionProductos, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))
    
    for s, p, o in ge.triples((None, RDF.type, CEO.Producto)):
        descripcion = ge.value(s, CEO.descripcion)
        categoria = ge.value(s, CEO.categoria)
        restricciones_devolucion = ge.value(s, CEO.restricciones_devolucion)
        gm.add((s, RDF.type, CEO.Producto))
        gm.add((s, CEO.categoria, Literal(descripcion)))
        gm.add((s, CEO.descripcion, Literal(categoria)))
        gm.add((s, CEO.restricciones_devolucion, Literal(restricciones_devolucion)))

    msg = build_message(gm, perf=ACL.request,
                        sender=GestorProductosExternos.uri,
                        receiver=AgenteBuscadorProductos.uri,
                        content=bp)

    gr = send_message(msg, AgenteBuscadorProductos.address)
        
    msgdic = get_message_properties(gr)
    if msgdic['performative'] == ACL.confirm:
        print('\n' + 'El mensaje se ha enviado y gestionado correctamente\n ')
    else:
        print('\n' + 'Ha habido un error durante el proceso\n ')
    
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
                print(gm.serialize(format='turtle'))
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
    tidyup()
    shutdown_server()
    return "Parando Servidor"


def tidyup():
    """
    Acciones previas a parar el agente

    """
    pass
    


def agentbehavior1(cola):
    """
    Un comportamiento del agente

    :return:
    """
    """
    Aqui metemos la comunicacion con el servicio directoria para registrarse como agente GestorProductosExternos
    """
    
    
    pass
    
    
def setup():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()
    
    setup()

    print('\nRunning on https://' + str(hostname) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
