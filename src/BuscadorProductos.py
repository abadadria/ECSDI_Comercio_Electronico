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
from AgentUtil.ACLMessages import build_message, get_message_properties
from AgentUtil.Logging import config_logger
from AgentUtil.DSO import DSO
from AgentUtil.Util import gethostname

from decimal import Decimal
from multiprocessing import Process


__author__ = 'adria'

# Configuration stuff
hostname = socket.gethostname()
port = 9010

agn = Namespace("http://www.agentes.org#")

CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente
AgenteBuscadorProductos = Agent('AgenteSimple',
                       agn.AgenteSimple,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Global triplestore graph
products_graph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)


def buscarProductos(gm):
        gr = Graph()
        gr.namespace_manager.bind('rdf', RDF)
        gr.namespace_manager.bind('ceo', CEO)
        
        for s, p, o in gm.triples((None, RDF.type, CEO.LineaBusqueda)):
            cantidad = gm.value(s, CEO.cantidad)
            categoria = gm.value(s, CEO.categoria)
            precio_max = gm.value(s, CEO.precio_max)
            precio_min = gm.value(s, CEO.precio_min)
            
            for s, p, o in products_graph.triples((None, RDF.type, CEO.Producto)):                
                categoriap = products_graph.value(s, CEO.categoria)
                categoriaOk = False
                if categoriap == categoria:
                     categoriaOk = True
                            
                if categoriaOk:
                    oferta = products_graph.value(s, CEO.ofertado_en)
                    precio = products_graph.value(oferta, CEO.precio)
                    precioOk = False
                    if Decimal(precio) < int(precio_max) and Decimal(precio) > int(precio_min):
                        precioOk = True
                    if precioOk:
                        gr.add((s, RDF.type, CEO.Producto))
                        gr.add((s, CEO.categoria, categoriap))
                        gr.add((oferta, RDF.type, CEO.Oferta))
                        gr.add((oferta, CEO.precio, precio))
                        gr.add((s, CEO.ofertado_en, oferta))

        return gr

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
                           sender=AgenteBuscadorProductos.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=AgenteBuscadorProductos.uri)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.BuscarProductos:
                gr = buscarProductos(gm)
                """
                Crear proceso que almacene la busqueda
                """
            elif accion == CEO.ActualizarInformacionProductos:
                """
                Crar proceso que actualice la información de busqueda de productos
                """
                gr = build_message( Graph(),
                                ACL['confirm'],
                                sender=AgenteBuscadorProductos.uri)
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=AgenteBuscadorProductos.uri)
            
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
    Aqui metemos la comunicacion con el servicio directoria para registrarse como agente buscadorProductos
    """
    
    
    pass
    
    
def setup():
    products_graph.parse('informacion productos.ttl', format='turtle')
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
