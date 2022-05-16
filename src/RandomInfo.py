# -*- coding: iso-8859-1 -*-
"""
.. module:: RandomInfo

RandomInfo
*************

:Description: RandomInfo

    Genera un grafo RDF con aserciones generando los valores de los atributos aleatoriamente

    Asumimos que tenemos ya definida una ontologia y simplemente escogemos una o varias de las clases
    y generamos aleatoriamente los valores para sus atributos.

    Solo tenemos que añadir aserciones al grafo RDFlib y despues grabarlo en OWL (o turtle), el resultado
    deberia poder cargarse en Protege, en un grafo RDFlib o en una triplestore (Stardog, Fuseki, ...)

    Se puede añadir tambien aserciones sobre las clases y los atributos si no estan ya en una ontologia
      que hayamos elaborado con Protege

:Authors: bejar
    

:Version: 

:Created on: 22/04/2016 12:30 

"""

from pyexpat import model
from rdflib import Graph, RDF, RDFS, OWL, XSD, Namespace, Literal
import string
import random

__author__ = 'abadadria'


def random_name(prefix, size=6, chars=string.ascii_uppercase + string.digits):
    """
    Genera un nombre aleatorio a partir de un prefijo, una longitud y una lista con los caracteres a usar
    en el nombre
    :param prefix:
    :param size:
    :param chars:
    :return:
    """
    return prefix + '_' + ''.join(random.choice(chars) for _ in range(size))

if __name__ == '__main__':
    # Declaramos espacios de nombres de nuestra ontologia, al estilo DBPedia (clases, propiedades, recursos)
    myOnto = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

    # Diccionario de atributos f= tipo float, i= tipo int, s= tipo string, otro => clase existente en la ontologia
    # Faltan atributos que no son necesarios para esta entrega
    product_properties = {'cantidad': 'i',
                          'categoria': 's',
                          'descripcion': 's',
                          'restricciones_devolucion': 's',
                          'valoracion_media': 'f'}

    ofert_properties = {'cantidad': 'i',
                        'gestion_envio' : 's',
                        'identificador': 'i',
                        'precio': 'f'}
    
    categorias_productos = ['producto_hogar', 
                            'ropa', 
                            'comida', 
                            'informatica', 
                            'electrodomestico', 
                            'juguete', 
                            'instrumento_musical', 
                            'producto_jardin']

    # model_properties = {'tieneMarca': 'Marca', 'nombre': 's'}
    # marca_properties = {'nombre': 's'}

    # contiene 40 productos, 8 marcas y 40 modelos
    products_graph = Graph()

    # Listas con todas las marcas y los modelos que se van a crear
    marcas = [None] * 8
    modelos = [None] * 40
    
    # Generamos 8 instancias de marcas al azar y 5 instancias de modelo para cada marca
    for j in range(8):
        # instancia al azar
        rmarca = 'Marca_' + str(j)
        marcas[j] = rmarca
        # print(rmarca)
        # Añadimos la instancia de marca
        products_graph.add((myOnto[rmarca], RDF.type, myOnto.Marca))
        # Le asignamos una propiedad nombre a la marca
        products_graph.add((myOnto[rmarca], myOnto.nombre, Literal(rmarca)))
        # Creamos cinco instancias de modelo y le asignamos esta marca
        for k in range(5):
            # instancia al azar
            rmodelo = 'Modelo_' + str(j*5 + k)
            modelos[j*5 + k] = rmodelo
            # print(rmodelo)
            # Añadimos la instancia de modelo
            products_graph.add((myOnto[rmodelo], RDF.type, myOnto.Modelo))
            # Le asignamos una propiedad nombre al modelo
            products_graph.add((myOnto[rmodelo], myOnto.nombre, Literal(rmodelo)))
            # Le asignamos la marca que acabamos de crear
            products_graph.add((myOnto[rmodelo], myOnto.tiene_marca, myOnto[rmarca]))
    
    for i in range(40):
        # generamos instancias de productos
        rproduct = 'Product_' + str(i)
        # print(rproduct)
        # Añadimos la instancia de producto
        products_graph.add((myOnto[rproduct], RDF.type, myOnto.Producto))
        # Le asignamos una propiedad nombre al producto
        products_graph.add((myOnto[rproduct], myOnto.nombre, Literal(rproduct)))
        # Le asignamos un modelo al producto
        products_graph.add((myOnto[rproduct], myOnto.tiene_modelo, Literal(modelos[i])))
        
        # Generamos sus atributos
        for prop_key, prop_value in product_properties.items():
            # el atributo es real
            if prop_value == 'f':
                number = format(round(random.uniform(0, 10), 2), '.2f')
                val = Literal(number)
            # el atributo es entero
            elif prop_value == 'i':
                val = Literal(random.randint(0, 50))
            # el atributo es string
            else:
                if prop_key == 'categoria':
                    val = Literal(random.choice(categorias_productos))
                else:
                    val = Literal(random_name(str(prop_key)))
            products_graph.add((myOnto[rproduct], myOnto[prop_key], val)) 

        # generamos dos instancias de oferta para cada uno de los productos creados
        oferta1 = 'Oferta_1_' + rproduct
        oferta2 = 'Oferta_2_' + rproduct

        # Añadimos la instancia de oferta
        products_graph.add((myOnto[oferta1], RDF.type, myOnto.Oferta))
        products_graph.add((myOnto[oferta2], RDF.type, myOnto.Oferta))

        for of_key, of_value in ofert_properties.items():
            # el atributo es real
            if of_value == 'f':
                number = format(round(random.uniform(0, 100), 2), '.2f')
                number2 = format(round(random.uniform(0, 100), 2), '.2f')
                val = Literal(number)
                val2 = Literal(number)
            # el atributo es entero
            elif of_value == 'i':
                if of_key == 'cantidad':
                    val = Literal(1)
                    val2 = val
                else:
                    val = Literal(random.randint(0, 50))
                    val2 = Literal(random.randint(0, 50))
            # el atributo es string
            else:
                if of_key == 'gestion_envio':
                    val = Literal('interna')
                    val2 = val
                else:
                    val = Literal(random_name(str(prop_key)))
                    val2 = Literal(random_name(str(prop_key)))

            products_graph.add((myOnto[oferta1], myOnto[of_key], val))
            products_graph.add((myOnto[oferta2], myOnto[of_key], val2))

        
        
        products_graph.add((myOnto[rproduct], myOnto.ofertado_en, myOnto[oferta1]))
        products_graph.add((myOnto[rproduct], myOnto.ofertado_en, myOnto[oferta2]))



    # Grabamos la ontologia resultante en turtle
    # Lo podemos cargar en Protege para verlo y cargarlo con RDFlib o en una triplestore (Fuseki)
    ofile = open('product.ttl', "w")
    ofile.write(products_graph.serialize(format='turtle'))
    ofile.close()
