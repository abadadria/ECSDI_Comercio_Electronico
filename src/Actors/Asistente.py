# -*- coding: utf-8 -*-
"""
filename: Asistente

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

"""

from multiprocessing import Process, Queue
import logging
import argparse
from time import gmtime

from flask import Flask, request
from markupsafe import _MarkupEscapeHelper
from matplotlib import get_backend
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal
import rdflib
from rdflib.namespace import FOAF, RDF

from AgentUtil.ACL import ACL
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.ACLMessages import build_message, send_message, get_message_properties
from AgentUtil.Agent import Agent
from AgentUtil.Logging import config_logger
from AgentUtil.DSO import DSO
from AgentUtil.Util import gethostname
import socket
import requests
import json

from DirectoryOps import search_agent


__author__ = 'raul'

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
    port = 9002
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

# Configuration of the namespace of comercio-electronico ontology
CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# Contador de mensajes
mss_cnt = 0

# Datos del Agente
Asistente = Agent('Asistente',
                       CEO.Asistente,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

def buscar_productos():
    ncategorias = int(input("Introduce la cantidad de categorias de productos que te interesan:"))
    print("Introduce las categorias de productos que te interesan:")
    print("\tFormato: categoria(str) cantidad(int) precio_min(int) precio_max(int)")

    # Crea el grafo de la acción BuscarProductos
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    # Crea la Acción BuscarProductos
    bp = CEO.buscarproductos
    gm.add((bp, RDF.type, CEO.BuscarProductos))
    gm.add((CEO.BuscarProductos, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    # Añade la Busqueda al grafo
    b = CEO.Busqueda
    gm.add((b, RDF.type, CEO.Busqueda))
    gm.add((bp, CEO.busca, b))

    for i in range(ncategorias):
        # Lee una linea de terminal que sorresponde con una LineaBusqueda
        linea = input().split()
        # Añade la LineaBusqueda al grafo
        l = CEO["lineabusqueda" + str(i)]
        gm.add((l, RDF.type, CEO.LineaBusqueda))
        gm.add((CEO.LineaBusqueda, RDFS.subClassOf, CEO.Linea))
        gm.add((l, CEO.cantidad, Literal(int(linea[1]))))
        gm.add((b, CEO.tiene_linea_busqueda, l))
        gm.add((l, CEO.categoria, Literal(linea[0])))
        gm.add((l, CEO.precio_min, Literal(int(linea[2]))))
        gm.add((l, CEO.precio_max, Literal(int(linea[3]))))
    
    # print(gm.serialize(format='turtle'))

    BuscadorProductos = search_agent(CEO.BuscadorProductos, Asistente, ServicioDirectorio)

    msg = build_message(gm,
                        perf=ACL.request,
                        sender=Asistente.uri,
                        receiver=BuscadorProductos.uri,
                        content=bp)    

    gr = send_message(msg, BuscadorProductos.address)

    print(gr.serialize(format='turtle'))

    print('\n' + 'Las ofertas de productos son:\n ')
    for s, p, o in gr.triples((None, RDF.type, CEO.Producto)):
        precio = gr.value(s, CEO.precio)
        length = len(s)
        name = s[67:length]
        
        print(name + ' con precio: ' + str(precio) + '€')
    print('\n')

    gp = Graph()
    gp.namespace_manager.bind('ceo', CEO)

    pedido = CEO.pedido
    gp.add((pedido, RDF.type, CEO.Pedido))
    gp.add((CEO.LineaProducto, RDFS.subClassOf, CEO.Linea))

    # Se filtra el resultado obtenido de la búsqueda según las preferencias del usuario
    for s, p, o in gm.triples((None, RDF.type, CEO.LineaBusqueda)):
        # Para cada linea de busqueda del usuario se busca que producto/s es/son el/los mejor/es
        categoria = gm.value(subject=s, predicate=CEO.categoria)
        cantidad_pedida = gm.value(subject=s, predicate=CEO.cantidad)
        q = """SELECT ?p ?c
            WHERE {
                ?p rdf:type ceo:Producto .
                ?p ceo:categoria ?cat .
                ?p ceo:precio ?precio .
                ?p ceo:cantidad ?c
            }
            ORDER BY ?precio
            """
        
        res = gr.query(q, initBindings={'cat': Literal(categoria)})

        remaining = int(cantidad_pedida)
        n_linea = 0
        for p, c in res:
            if int(c) == 0: continue

            lp = CEO["lineaproducto" + str(n_linea)]
            n_linea += 1
            gp.add((lp, RDF.type, CEO.LineaProducto))
            gp.add((pedido, CEO.tiene_linea_producto, lp))

            if int(c) >= remaining:
                # el producto satisface la cantidad deseada
                gp.add((lp, CEO.cantidad, Literal(remaining)))
                gr.set((p, CEO.cantidad, Literal(int(c) - remaining)))
                remaining = 0
            else:
                # el producto NO satisface la cantidad deseada
                gp.add((lp, CEO.cantidad, c))
                gr.set((p, CEO.cantidad, Literal(0)))
                remaining -= int(c)

            for res in gr.predicate_objects(p):
                gp.add((p, res[0], res[1]))
            gp.add((lp, CEO.tiene_producto, p))

            modelo = gr.value(subject=p, predicate=CEO.tiene_modelo)
            for res in gr.predicate_objects(modelo):
                gp.add((modelo, res[0], res[1]))

            marca = gr.value(subject=modelo, predicate=CEO.tiene_marca)
            for res in gr.predicate_objects(marca):
                gp.add((marca, res[0], res[1]))

            if remaining <= 0: break  

        print(gp.serialize(format='turtle'))          

        return gp

def pedir(g):
    GestorPedidos = search_agent(CEO.GestorPedidos, Asistente, ServicioDirectorio)

    accion = CEO.realizarpedido
    g.add((accion, RDF.type, CEO.RealizarPedido))
    g.add((CEO.RealizarPedido, RDFS.subClassOf, CEO.Accion))
    g.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))
    g.add((accion, CEO.tiene_pedido, CEO.pedido))

    print("Datos de tarjeta de pago:")
    print("\tFormato: pan(str) cvv(int) fecha_caducidad(str)")
    metodo_pago = input().split()

    tc = CEO.targetacredito
    g.add((tc, RDF.type, CEO.TargetaCredito))
    g.add((CEO.TargetaCredito, RDFS.subClassOf, CEO.MetodoPago))
    g.add((tc, CEO.pan, Literal(str(metodo_pago[0]))))
    g.add((tc, CEO.cvv, Literal(int(metodo_pago[1]))))
    g.add((tc, CEO.fecha_caducidad, Literal(str(metodo_pago[2]))))
    g.add((CEO.pedido, CEO.tiene_metodo_pago, tc))

    print("Datos de envio:")
    print("\tFormato: prioridad[alta/media/baja] ciudad_destino(str)")
    datos_envio = input().split()
    g.add((CEO.pedido, CEO.prioridad, Literal(str(datos_envio[0]))))
    lugar = CEO.lugar
    g.add((lugar, RDF.type, CEO.Lugar))
    g.add((lugar, CEO.ciudad, Literal(str(datos_envio[1]))))
    g.add((CEO.pedido, CEO.se_entrega_en, lugar))

    print('Pedido:')
    print(g.serialize(format='turtle'))

    msg = build_message(g,
                        perf=ACL.request,
                        sender=Asistente.uri,
                        receiver=GestorPedidos.uri,
                        content=accion)

    gr = send_message(msg, GestorPedidos.address)

    if (None, ACL.performative, ACL.inform) in gr:
        print('\n * Pedido realizado con éxito')
        print('\n\n-----------------------------------------------')
        print('            FACTURA DE COMPRA')
        print('-----------------------------------------------\n')
        for lf in gr.subjects(RDF.type, CEO.LineaFactura):
            cantidad = gr.value(lf, CEO.cantidad)
            marca = gr.value(lf, CEO.marca)
            modelo = gr.value(lf, CEO.modelo)
            precio = gr.value(lf, CEO.precio)
            importe_linea = gr.value(lf, CEO.importe_total)
            print(f'{cantidad} {marca[67:]} {modelo[67:]} {precio}€ {importe_linea}€')
        pedido = gr.value(predicate=RDF.type, object=CEO.Factura)
        print('\n-----------------------------------------------')
        print('IMPORTE FINAL: ' + gr.value(pedido, CEO.importe_total))
        print('-----------------------------------------------\n\n')
    else:
        print('\n * No se ha hecho el pedido')

def do(value):
    if value == 1:
        gp = buscar_productos()
        # categoria marca modelo cantidad precio_unitario precio_total
        # precio_pedido
        
        print('\n' + 'Los productos recomendados son:')
        print("\tFormato: categoria marca modelo cantidad precio_unitario precio_total\n")
        precio_pedido = 0
        for s, p, o in gp.triples((None, RDF.type, CEO.Producto)):
            categoria = gp.value(subject=s, predicate=CEO.categoria)
            modelo = gp.value(subject=s, predicate=CEO.tiene_modelo)
            marca = gp.value(subject=modelo, predicate=CEO.tiene_marca)
            linea = gp.value(predicate=CEO.tiene_producto, object=s)
            cantidad = gp.value(subject=linea, predicate=CEO.cantidad)
            precio = gp.value(s, CEO.precio)
            precio_total = float(precio) * int(cantidad)
            precio_pedido += precio_total
            
            print(f'{categoria} {marca[67:]} {modelo[67:]} {cantidad} {precio}€ {precio_total}€')
        print(f'PRECIO TOTAL: {precio_pedido}€\n')

        print("Deseas pedir estos productos?")
        print("[1] Pedir productos")
        print("[0] Cerrar")
        value = int(input())

        if value == 0:
            exit()
        else:
            pedir(gp)
        
        

if __name__ == '__main__':
    print("Bienvenido a el Asistente de Comercio Electronico")
    
    while 1:
        print("Que acción deseas realizar?")
        print("[1] Buscar productos")
        print("[0] Cerrar")
        value = int(input())
        
        if value == 0:
            exit()
        else:
            do(value)
    