# -*- coding: utf-8 -*-
"""

Esqueleto de agente usando los servicios web de Flask

/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""

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


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """

    def buscarProductos():
        gr = Graph()

        print('graph------------')
        print(gm.serialize(format='turtle'))
        print('graph------------')
        
        for s, p, o in gm.triples((None, RDF.type, CEO.LineaBusqueda)):
            cantidad = gm.value(s, CEO.cantidad)
            print(cantidad)
            categoria = gm.value(s, CEO.categoria)
            print(categoria)
            precio_max = gm.value(s, CEO.precio_max)
            print(precio_max)
            precio_min = gm.value(s, CEO.precio_min)
            print(precio_min)
            
            # FILTER (?precio <= '""" + str(precio_max) + """' && ?precio >= '""" + str(precio_min) + """' && ?categoria = '""" + categoria + """')
            
            query = """PREFIX ceo: <http://www.semanticweb.org/samragu/ontologies/comercio-electronico#>
                    SELECT ?Oferta ?Producto ?categoria ?precio
                    WHERE {
                        ?Oferta rdf:type ceo:Oferta .
                        ?Oferta ceo:precio ?precio .
                        ?Producto ceo:ofertado_en ?Oferta .
                        ?Producto ceo:categoria ?categoria .
                        FILTER (?precio <= '""" + str(precio_max) + """' && ?precio >= '""" + str(precio_min) + """' && ?categoria = '""" + categoria + """')
                    }"""
            
            graph = products_graph.query(query, initNs= {'rdf', RDF})
            
            print('graph despues de query------------')
            for row in graph:
                print(row)
            print('graph despues de query------------')       
              

        return gr


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

            print(gm.serialize(format='turtle'))

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.BuscarProductos:
                gr = buscarProductos()
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
    pass
    
    
def setup():
    products_graph.parse('product.ttl', format='turtle')


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()
    
    setup()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
