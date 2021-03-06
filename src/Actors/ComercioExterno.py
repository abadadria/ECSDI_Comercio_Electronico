# -*- coding: utf-8 -*-
"""
filename: Comercio Externo

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""

from multiprocessing import Process, Queue
import logging
import argparse

from flask import Flask, request
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal
from rdflib.namespace import FOAF, RDF

from AgentUtil.ACL import ACL
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.ACLMessages import build_message, send_message, get_message_properties
from AgentUtil.Agent import Agent
from AgentUtil.Logging import config_logger
from AgentUtil.DSO import DSO
from AgentUtil.Util import gethostname
import socket
import threading
import time

from DirectoryOps import search_agent


__author__ = 'adria'

# Definimos los parametros de la linea de comandos
parser = argparse.ArgumentParser()
parser.add_argument('--open',
                    help="Define si el servidor est abierto al exterior o no",
                    action='store_true',
                    default=False)
parser.add_argument('--dir',
                    default=None,
                    help="Direccion del servicio de directorio")
parser.add_argument('--port',
                    type=int,
                    help="Puerto de comunicacion del agente")
parser.add_argument('--verbose',
                    help="Genera un log de la comunicacion del servidor web",
                    action='store_true',
                    default=False)

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

if args.dir is None:
    raise NameError('A Directory Service addess is needed')
else:
    diraddress = args.dir

# Configuration stuff
if args.port is None:
    port = 9040
else:
    port = args.port

if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

print('DS Hostname =', hostaddr)

# Flask stuff
app = Flask(__name__)

# Configuration constants and variables
agn = Namespace("http://www.agentes.org#")

# Configuration of the namespaprint(cnt)ce of comercio-electronico ontology
CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# Contador de mensajes
mss_cnt = 0

# Datos del Agente
ComercioExterno = Agent('AgentePersonal',
                       agn.AgentePersonal,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

products_graph = Graph()


def actualizar_info_productos():
    nproductos = int(input("Introduce la cantidad de productos que vas a actualizar:"))
    print("Introduce el nombre del producto y sus atributos a cambiar (insertar '-' si no se desea cambiar")
    print("\tFormato: nombre(str) cantidad(int) categoria(str) descripcion(str) precio(float) restricciones_devolucion(str) gestion_envio(str)")
    """
    Ampliar en un futuro para que se pueda cambiar todo tipo de informaci??n y que sea el gestor
    de productos externos el que decida a quien enviar esta informacion. De momento solo se puede cambiar la
    informacion que le corresponde al buscador de productos
    """
    # Crea el grafo de la acci??n ActualizarInformacionProductos
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    # Crea la Acci??n ActualizarInformacionProductos
    bp = CEO.ActualizarInformacionProductos
    gm.add((bp, RDF.type, CEO.ActualizarInformacionProductos))
    gm.add((CEO.ActualizarInformacionProductos, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    for i in range(nproductos):
        # Lee una linea de terminal que sorresponde con parte de la inforacion de un Producto
        atributosProducto = input().split()
        # A??ade la LineaBusqueda al grafo
        p = CEO[atributosProducto[0]]
        gm.add((p, RDF.type, CEO.Producto))
        if atributosProducto[1] != '-': gm.add((p, CEO.cantidad, Literal(atributosProducto[1])))
        if atributosProducto[2] != '-': gm.add((p, CEO.categoria, Literal(atributosProducto[2])))
        if atributosProducto[3] != '-': gm.add((p, CEO.descripcion, Literal(atributosProducto[3])))
        if atributosProducto[4] != '-': gm.add((p, CEO.precio, Literal(atributosProducto[4])))
        if atributosProducto[5] != '-': gm.add((p, CEO.restricciones_devolucion, Literal(atributosProducto[5])))
        if atributosProducto[6] != '-': gm.add((p, CEO.gestion_envio, Literal(atributosProducto[6])))
    
    GestorProductosExternos = search_agent(CEO.GestorProductosExternos, ComercioExterno, ServicioDirectorio)
    
    msg = build_message(gm, perf=ACL.request,
                        sender=ComercioExterno.uri,
                        receiver=GestorProductosExternos.uri,
                        content=bp)

    gr = send_message(msg, GestorProductosExternos.address)

    return gr
        
def do(value):
    if value == 1:
        gr = actualizar_info_productos()
        msgdic = get_message_properties(gr)
        if msgdic['performative'] == ACL.confirm:
            print('\n' + 'El mensaje se ha enviado y gestionado correctamente\n ')
        else:
            print('\n' + 'Ha habido un error durante el proceso\n ')
        
def inicializar_info_productos():
    bp = CEO.ActualizarInformacionProductos
    products_graph.add((bp, RDF.type, CEO.ActualizarInformacionProductos))
    products_graph.add((CEO.ActualizarInformacionProductos, RDFS.subClassOf, CEO.Accion))
    products_graph.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    GestorProductosExternos = search_agent(CEO.GestorProductosExternos, ComercioExterno, ServicioDirectorio)
    
    address = str(ComercioExterno.address)
    for s, p, o in products_graph.triples((None, RDF.type, CEO.Producto)):
        products_graph.add((s, CEO.vendedor, Literal(address)))
    
    msg = build_message(products_graph, perf=ACL.request,
                        sender=ComercioExterno.uri,
                        receiver=GestorProductosExternos.uri,
                        content=bp)

    gr = send_message(msg, GestorProductosExternos.address)

    return gr


def setup():
    if port == 9040: name = 'info_prod_CE1.ttl'
    elif port == 9041: name = 'info_prod_CE2.ttl'
    else: name = 'info_prod_CE3.ttl'
    products_graph.parse(name, format='turtle')
    
    gr = inicializar_info_productos()
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
    def enviarProductos():
        print("Petici??n de envio de productos recibida y gestionada\n")
        return build_message(Graph(),
                             ACL.confirm,
                             sender=ComercioExterno.uri)


    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml')

    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if not msgdic:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(),
                           ACL['not-understood'],
                           sender=ComercioExterno.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=ComercioExterno.uri)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.ActualizarInformacionProductos:
                pass
            elif accion == CEO.SolicitarEnvio:
                gr = enviarProductos()
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=ComercioExterno.uri)
            
    return gr.serialize(format='xml')


@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    shutdown_server()
    return "Parando Servidor"
    

if __name__ == '__main__':
    setup()
    print('\nRunning on https://' + str(hostname) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')
    
    threading.Thread(target=lambda: app.run(host=hostname, port=port)).start()
    
    time.sleep(0.5)
    print("Bienvenido a ComercioExterno")
    while 1:
        print("Que acci??n deseas realizar?")
        print("[1] Actualizar informaci??n productos")
        print("[0] Cerrar")
        value = int(input())
        
        if value == 0:
            exit()
        else:
            do(value)
