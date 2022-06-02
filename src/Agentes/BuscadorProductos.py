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
    port = 9010
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
BuscadorProductos = Agent('BuscadorProductos',
                       CEO.BuscadorProductos,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# Global triplestore graph
products_graph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)

if not args.verbose:
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.ERROR)

@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """

    def buscarProductos():
        gr = Graph()
        gr.namespace_manager.bind('rdf', RDF)
        gr.namespace_manager.bind('ceo', CEO)
        
        for s, p, o in gm.triples((None, RDF.type, CEO.LineaBusqueda)):
            cantidad = gm.value(s, CEO.cantidad)
            categoria = gm.value(s, CEO.categoria)
            precio_max = gm.value(s, CEO.precio_max)
            precio_min = gm.value(s, CEO.precio_min)
            
            
            ''' NO FUNCIONA
            
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
            
            print('graph despues de query)
            for row in graph:
                print(row)
            print('graph despues de query)    
            
            '''
            
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


    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml')

    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if not msgdic:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(),
                           ACL['not-understood'],
                           sender=BuscadorProductos.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=BuscadorProductos.uri)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.BuscarProductos:
                gr = buscarProductos()
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=BuscadorProductos.uri)
            
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

    # Registro al ServicioDirectorio
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    ra = CEO.registraragente
    gm.add((ra, RDF.type, CEO.RegistrarAgente))
    gm.add((CEO.RegistrarAgente, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    a = CEO.agente
    gm.add((a, RDF.type, CEO.BuscadorProductos))
    gm.add((CEO.BuscadorProductos, RDFS.subClassOf, CEO.Agente))
    gm.add((a, CEO.direccion, Literal(BuscadorProductos.address)))
    gm.add((a, CEO.uri, BuscadorProductos.uri))
    gm.add((ra, CEO.con_agente, a))

    logger.info('Peticion de registro al ServicioDirectorio')
    logger.info(gm.serialize(format='turtle'))

    msg = build_message(gm,
                        ACL.request,
                        sender=BuscadorProductos.uri,
                        receiver=ServicioDirectorio.uri,
                        content=ra)
    
    gr = send_message(msg, ServicioDirectorio.address)

    logger.info(gr.serialize(format='turtle'))

    if (None, ACL.performative, ACL.confirm) in gr:
        print('\n  * Registro de agente CONFIRMADO')
    else:
        print('\n  * Registro de agente NO confirmado')


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()
    
    setup()

    print('\nRunning on http://' + str(hostaddr) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
