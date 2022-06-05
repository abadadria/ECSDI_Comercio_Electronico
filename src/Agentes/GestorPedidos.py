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
from Agentes.BuscadorProductos import BuscadorProductos

from DirectoryOps import register_agent, search_agent, unregister_agent


__author__ = 'raul'

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
    port = 9020
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
n_pedidos = 0

# Datos del Agente
GestorPedidos = Agent('GestorPedidos',
                       CEO.GestorPedidos,
                       'http://%s:%d/comm' % (hostaddr, port),
                       'http://%s:%d/Stop' % (hostaddr, port))

ServicioDirectorio = Agent('ServicioDirectorio',
                        CEO.ServicioDirectorio,
                        '%s/register' % (diraddress),
                        '%s/Stop' % (diraddress))

# Global triplestore graph
grafo_pedidos = Graph()
grafo_pedidos.namespace_manager.bind('ceo', CEO)

# Flask stuff
app = Flask(__name__)

if not args.verbose:
    logger = logging.getLogger('werkzeug')
    logger.setLevel(logging.ERROR)

def cobrar_pedido():
    pass

def almacenar_pedido_cerrado():
    pass

def actualizar_informacion_productos():
    pass

def informar_productos_pedidos(gm):
    accion = CEO.informarproductospedidos
    gm.add((accion, RDF.type, CEO.InformarProductosPedidos))
    gm.add((CEO.InformarProductosPedidos, RDFS.subClassOf, CEO.Informacion))
    gm.add((CEO.Informacion, RDFS.subClassOf, CEO.Accion))
    for lp in gm.subjects(predicate=RDF.type, object=CEO.LineaProducto):
        gm.add((accion, CEO.tiene_linea_producto, lp))

    BuscadorProductos = search_agent(CEO.BuscadorProductos, GestorPedidos, ServicioDirectorio)
    msg = build_message(gm,
                        ACL.inform,
                        sender=GestorPedidos.uri,
                        receiver=BuscadorProductos.uri,
                        content=accion)
    send_message(msg, BuscadorProductos.address)
    

@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """
    def crear_pedido():
        global n_pedidos

        gipp = Graph()
        gipp.namespace_manager.bind('ceo', CEO)

        # Crea el Pedido
        pedido = CEO['pedido_' + str(n_pedidos + 1)]
        grafo_pedidos.add((pedido, RDF.type, CEO.Pedido))
        for p, o in gm.predicate_objects(CEO.targetacredito):
            grafo_pedidos.add((CEO.targetacredito, p, o))
        grafo_pedidos.add((pedido, CEO.tiene_metodo_pago, CEO.targetacredito))
        grafo_pedidos.add((pedido, CEO.prioridad, gm.value(subject=CEO.pedido, predicate=CEO.prioridad)))
        grafo_pedidos.add((CEO.lugar, RDF.type, CEO.Lugar))
        grafo_pedidos.add((CEO.lugar, CEO.ciudad, gm.value(CEO.lugar, CEO.ciudad)))
        grafo_pedidos.add((pedido, CEO.se_entrega_en, CEO.lugar))
        for lp in gm.objects(CEO.pedido, CEO.tiene_linea_producto):
            # Se añaden las LineaProducto del Pedido
            cantidad = gm.value(subject=lp, predicate=CEO.cantidad)
            producto = gm.value(subject=lp, predicate=CEO.tiene_producto)
            grafo_pedidos.add((lp, RDF.type, CEO.LineaProducto))
            grafo_pedidos.add((lp, CEO.cantidad, cantidad))
            grafo_pedidos.add((lp, CEO.tiene_producto, producto))

            # Grafo para actualizar el BuscadorProductos
            gipp.add((lp, RDF.type, CEO.LineaProducto))
            gipp.add((lp, CEO.cantidad, cantidad))
            gipp.add((lp, CEO.tiene_producto, producto))

            for p, o in gm.predicate_objects(producto):
                # Se añade el Producto
                grafo_pedidos.add((producto, p, o))
                if p == CEO.tiene_modelo:
                    # Se añade el Modelo
                    for p2, o2 in gm.predicate_objects(o):
                        grafo_pedidos.add((o, p2, o2))
                        if (p2 == CEO.tiene_marca):
                            # Se añade la Marca
                            for p3, o3 in gm.predicate_objects(o2):
                                grafo_pedidos.add((o2, p3, o3))

            grafo_pedidos.add((pedido, CEO.tiene_linea_producto, lp))    

        print(grafo_pedidos.serialize(format='turtle'))

        informar_productos_pedidos(gipp)

        n_pedidos += 1

        # Informar factura de compra
        gf = Graph()
        gf.namespace_manager.bind('ceo', CEO)

        accion = CEO.informarfacturapedido
        gf.add((accion, RDF.type, CEO.InformarFacturaPedido))
        gf.add((CEO.InformarFacturaPedido, RDFS.subClassOf, CEO.Informacion))
        gf.add((CEO.Informacion, RDFS.subClassOf, CEO.Comunicacion))
        factura = CEO.factura
        gf.add((factura, RDF.type, CEO.Factura))
        gf.add((accion, CEO.tiene_factura, factura))
        gf.add((CEO.LineaFactura, RDFS.subClassOf, CEO.Linea))
        importe_pedido = 0
        i = 0
        for lp in grafo_pedidos.objects(pedido, CEO.tiene_linea_producto):
            cantidad = grafo_pedidos.value(subject=lp, predicate=CEO.cantidad)
            producto = grafo_pedidos.value(subject=lp, predicate=CEO.tiene_producto)
            modelo = grafo_pedidos.value(producto, CEO.tiene_modelo)
            marca = grafo_pedidos.value(modelo, CEO.tiene_marca)
            precio = grafo_pedidos.value(producto, CEO.precio)
            importe_total = Literal(float(precio) * int(cantidad))
            lf = CEO['lineafactura' + str(i)]
            gf.add((lf, RDF.type, CEO.LineaFactura))
            gf.add((factura, CEO.tiene_linea_factura, lf))
            gf.add((lf, CEO.cantidad, cantidad))
            gf.add((lf, CEO.marca, marca))
            gf.add((lf, CEO.modelo, modelo))
            gf.add((lf, CEO.precio, Literal(float(precio))))
            gf.add((lf, CEO.importe_total, importe_total))
            importe_pedido += float(importe_total)
            i += 1

        gf.add((factura, CEO.importe_total, Literal(importe_pedido)))        

        print(gf.serialize(format='turtle'))

        return build_message(gf,
                      ACL.inform,
                      sender=GestorPedidos.uri,
                      content=accion)
    

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml')

    msgdic = get_message_properties(gm)

    # Comprobamos que sea un mensaje FIPA ACL
    if not msgdic:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(),
                           ACL['not-understood'],
                           sender=GestorPedidos.uri)
    else:
        # Obtenemos la performativa
        if msgdic['performative'] == ACL.request:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia
            # de registro
            content = msgdic['content']

            # Averiguamos el tipo de la accion
            accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            if accion == CEO.RealizarPedido:
                gr = crear_pedido()
            else:
                gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorPedidos.uri)
        elif msgdic['performative'] == ACL.inform:
            pass
        else:
            # Si no es un request ni un inform, respondemos que no hemos entendido el mensaje
            gr = build_message( Graph(),
                                ACL['not-understood'],
                                sender=GestorPedidos.uri)
            
    return gr.serialize(format='xml')


def setup():
    pass

def tidyup():
    """
    Acciones previas a parar el agente

    """
    unregister_agent(GestorPedidos, ServicioDirectorio)

if __name__ == '__main__':
    setup()
    register_agent(GestorPedidos, ServicioDirectorio, logger)

    print('\nRunning on http://' + str(hostaddr) + ':' + str(port) + '/ (Press CTRL+C to quit)\n')

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)
    tidyup()
    print('The End')