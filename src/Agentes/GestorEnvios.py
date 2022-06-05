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

jobs = []

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

def gestionInterna(g):
    # Informar productos externos a ComerciosExternos
    for envio in g.subjects(RDF.type, CEO.Envio):
        gm = Graph()
        gm.namespace_manager.bind('ceo', CEO)

        accion = CEO.solicitarenvio
        gm.add((accion, RDF.type, CEO.SolicitarEnvio))
        gm.add((CEO.SolicitarEnvio, RDFS.subClassOf, CEO.Accion))
        gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

        gm.add((accion, CEO.tiene_envio, envio))
        for p, o in g.predicate_objects(envio):
            gm.add((envio, p, o))
            if p == CEO.tiene_linea_producto:
                for p2, o2 in g.predicate_objects(o):
                    gm.add((o, p2, o2))
                    if p2 == CEO.tiene_producto:
                        for p3, o3 in g.predicate_objects(o2):
                            gm.add((o2, p3, o3))
        destino = g.value(envio, CEO.con_destino)
        ciudad = g.value(destino, CEO.ciudad)
        gm.add((destino, envio, CEO.con_destino))
        gm.add((destino, RDF.type, CEO.Lugar))
        gm.add((destino, CEO.ciudad, ciudad))

        logger.info('\n\nGM_INT:')
        logger.info(gm.serialize(format='turtle'))

        #CentroLogistico = search_agent(CEO.CentroLogistico, GestorEnvios, ServicioDirectorio) #, int(g.value(envio, CEO.n_centro_logistico))
        #msg = build_message(gm,
        #                    ACL.request,
        #                    sender=GestorEnvios.uri,
        #                    receiver=CEO.ComercioExterno,
        #                    content=accion)
        #gr = send_message(msg, str())


def gestionExterna(g):
    # SolicitarEnvio a ComerciosExternos
    for envio in g.subjects(RDF.type, CEO.Envio):
        gm = Graph()
        gm.namespace_manager.bind('ceo', CEO)

        accion = CEO.solicitarenvio
        gm.add((accion, RDF.type, CEO.SolicitarEnvio))
        gm.add((CEO.SolicitarEnvio, RDFS.subClassOf, CEO.Accion))
        gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))
        
        gm.add((accion, CEO.tiene_envio, envio))
        for p, o in g.predicate_objects(envio):
            gm.add((envio, p, o))
            if p == CEO.tiene_linea_producto:
                for p2, o2 in g.predicate_objects(o):
                    gm.add((o, p2, o2))
                    if p2 == CEO.tiene_producto:
                        for p3, o3 in g.predicate_objects(o2):
                            gm.add((o2, p3, o3))
        destino = g.value(envio, CEO.con_destino)
        ciudad = g.value(destino, CEO.ciudad)
        gm.add((destino, envio, CEO.con_destino))
        gm.add((destino, RDF.type, CEO.Lugar))
        gm.add((destino, CEO.ciudad, ciudad))
        
        logger.info('\n\nGM_EXT:')
        logger.info(gm.serialize(format='turtle'))

        msg = build_message(gm,
                            ACL.Request,
                            sender=GestorEnvios.uri,
                            receiver=CEO.ComercioExterno,
                            content=accion)
        gr = send_message(msg, str(g.value(envio, CEO.vendedor)))

        if not (None, ACL.performative, ACL.confirm) in gr:
            print("Ha habido un error (GestorEnvios:163)")
            exit()

def gestionarEnvioProceso(ge):
    print(ge.serialize(format='turtle'))

    # Grafo para envios de gestion externa
    genv_ext = Graph()
    genv_ext.namespace_manager.bind('ceo', CEO)

    # Grafo para envios de gestion interna
    genv_int = Graph()
    genv_int.namespace_manager.bind('ceo', CEO)

    destino = CEO.destino
    genv_ext.add((destino, RDF.type, CEO.lugar))
    genv_int.add((destino, RDF.type, CEO.lugar))
    lugar_d = ge.value(predicate=RDF.type, object=CEO.Lugar)
    genv_ext.add((destino, CEO.ciudad, ge.value(lugar_d, CEO.ciudad)))
    genv_int.add((destino, CEO.ciudad, ge.value(lugar_d, CEO.ciudad)))

    n_envio = 0
    for lp in ge.subjects(RDF.type, CEO.LineaProducto):
        producto = ge.value(lp, CEO.tiene_producto)
        gestion_envio = products_graph.value(producto, CEO.gestion_envio)
        
        if str(gestion_envio) == 'externa':
            #Gestion externa
            vendedor_addr = products_graph.value(producto, CEO.vendedor)
            if not (None, CEO.vendedor, vendedor_addr) in genv_ext:
                # Si no existe un envio desde vendedor_addr, se crea
                envio = CEO['envio_' + str(n_envio)]
                genv_ext.add((envio, RDF.type, CEO.Envio))
                genv_ext.add((envio, CEO.con_destino, destino))
                genv_ext.add((envio, CEO.vendedor, vendedor_addr))
                n_envio += 1
            else:
                # Ya existe un envio desde vendedor_addr
                envio = genv_ext.value(predicate=CEO.vendedor, object=vendedor_addr)
            
            genv_ext.add((envio, CEO.tiene_linea_producto, lp))
            genv_ext.add((lp, RDF.type, CEO.LineaProducto))
            genv_ext.add((CEO.LineaProducto, RDFS.subClassOf, CEO.Linea))
            genv_ext.add((lp, CEO.tiene_producto, producto))
            for p, o in ge.predicate_objects(producto):
                genv_ext.add((producto, p, o))
            genv_ext.add((producto, CEO.gestion_envio, gestion_envio))
            genv_ext.add((producto, CEO.vendedor, vendedor_addr))
            genv_ext.add((envio, CEO.estado, Literal("PENDING")))

        else:
        # Gestion interna
            n_cl = products_graph.value(producto, CEO.n_centro_logistico)
            if not (None, CEO.n_centro_logistico, n_cl) in genv_int:
                # Si no existe un envio desde n_cl, se crea
                envio = CEO['envio_' + str(n_envio)]
                genv_int.add((envio, RDF.type, CEO.Envio))
                genv_int.add((envio, CEO.con_destino, destino))
                genv_int.add((envio, CEO.n_centro_logistico, n_cl))
                n_envio += 1
            else:
                # Ya existe un envio desde n_cl
                envio = genv_int.value(predicate=CEO.n_centro_logistico, object=n_cl)

            genv_int.add((envio, CEO.tiene_linea_producto, lp))
            genv_int.add((lp, RDF.type, CEO.LineaProducto))
            genv_int.add((CEO.LineaProducto, RDFS.subClassOf, CEO.Linea))
            genv_int.add((lp, CEO.tiene_producto, producto))
            for p, o in ge.predicate_objects(producto):
                genv_int.add((producto, p, o))
            genv_int.add((producto, CEO.gestion_envio, gestion_envio))
            genv_int.add((producto, CEO.n_centro_logistico, n_cl))
            genv_ext.add((envio, CEO.estado, Literal("PENDING")))

            if (producto, CEO.vendedor, None) in products_graph:
                # Producto externo
                genv_int.add((producto, CEO.vendedor, products_graph.value(producto, CEO.vendedor)))

    logger.info('\n\nGENV_EXT:')
    logger.info(genv_ext.serialize(format='turtle'))

    logger.info('\n\nGENV_INT:')
    logger.info(genv_int.serialize(format='turtle'))

    gestionInterna(genv_int)
    gestionExterna(genv_ext)

    #p1 = Process(target=gestionInterna, args=(genv_int,))
    #p2 = Process(target=gestionExterna, args=(genv_ext,))
    #jobs.append(p1)
    #jobs.append(p2)
    #p1.start()
    #p2.start()

    #p1.join()
    #p2.join()

def gestionarEnvio(ge):
    gestionarEnvioProceso(ge)
    
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
    global jobs
    for job in jobs:
        job.join()
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
