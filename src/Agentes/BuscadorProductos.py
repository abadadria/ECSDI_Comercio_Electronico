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
            cantidadp = products_graph.value(s, CEO.cantidad)
            categoriaOk = False
            if categoriap == categoria:
                categoriaOk = True
            
            if categoriaOk:
                precio = products_graph.value(s, CEO.precio)
                precioOk = False
                if Decimal(precio) < int(precio_max) and Decimal(precio) > int(precio_min):
                    precioOk = True
                if precioOk:
                    # Añadimos toda la informacion necessaria: producto, oferta, modelo, marca
                    gr.add((s, RDF.type, CEO.Producto))
                    gr.add((s, CEO.precio, precio))
                    gr.add((s, CEO.categoria, categoriap))
                    gr.add((s, CEO.cantidad, cantidadp))
                    
                    descripcion = products_graph.value(s, CEO.descripcion)
                    gr.add((s, CEO.descripcion, descripcion))
                    
                    nombre = products_graph.value(s, CEO.nombre)
                    gr.add((s, CEO.nombre, nombre))
                    
                    restricciones_devolucion = products_graph.value(s, CEO.restricciones_devolucion)
                    gr.add((s, CEO.restricciones_devolucion, restricciones_devolucion))
                    
                    valoracion_media = products_graph.value(s, CEO.valoracion_media)
                    gr.add((s, CEO.valoracion_media, valoracion_media))
                    
                    modelo = products_graph.value(s, CEO.tiene_modelo)
                    gr.add((s, CEO.tiene_modelo, modelo))
                    
                    # Creamos las instancias de marca y modelo
                    gr.add((modelo, RDF.type, CEO.Modelo))
                    nombreModelo = products_graph.value(modelo, CEO.nombre)
                    gr.add((modelo, CEO.nombre, nombreModelo))
                    tiene_marca = products_graph.value(modelo, CEO.tiene_marca)
                    gr.add((tiene_marca, RDF.type, CEO.Marca))
                    gr.add((modelo, CEO.tiene_marca, tiene_marca))
                    nombreMarca = products_graph.value(tiene_marca, CEO.nombre)
                    gr.add((tiene_marca, CEO.nombre, nombreMarca))

    return gr

def gestionarActualizacion(ge):    
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
    
    ofile = open('info_prod.ttl', "w")
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
                gr = buscarProductos(gm)
                """
                (extra) Crear proceso que envie un mensaje al recomendador/control calidad para que almacene la busqueda
                """
            elif accion == CEO.ActualizarInformacionProductos:
                gestionarActualizacion(gm)
                
                gr = build_message( Graph(),
                                ACL['confirm'],
                                sender=BuscadorProductos.uri)
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
    shutdown_server()
    return "Parando Servidor"
    
    
def setup():
    products_graph.parse('info_prod.ttl', format='turtle')
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

def tidyup():
    """
    Acciones previas a parar el agente

    """
    unregister_agent(BuscadorProductos, ServicioDirectorio)

if __name__ == '__main__':
    setup()
    register_agent(BuscadorProductos, ServicioDirectorio, logger)

    print('\nRunning on http://' + str(hostaddr) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)
    
    tidyup()
    print('The End')
