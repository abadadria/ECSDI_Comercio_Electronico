# -*- coding: iso-8859-1 -*-
"""
.. module:: RandomInfo

RandomInfo
*************

:Description: RandomInfo

    Genera un grafo RDF con aserciones generando los valores de los atributos aleatoriamente

    Corresponde a la BD de Información productos


"""

from pyexpat import model
from rdflib import Graph, RDF, RDFS, OWL, XSD, Namespace, Literal
import string
import random

__author__ = 'adria'


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
    CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")
    
    # Diccionario de atributos f= tipo float, i= tipo int, s= tipo string, otro => clase existente en la ontologia
    # Faltan atributos que no son necesarios para esta entrega
    product_properties = {'cantidad': 'i',
                          'categoria': 's',
                          'descripcion': 's',
                          'restricciones_devolucion': 's',
                          'valoracion_media': 'f'}

    ofert_properties = {'gestion_envio' : 's',
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

    products_graph.namespace_manager.bind('rdf', RDF)
    products_graph.namespace_manager.bind('ceo', CEO)

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
        products_graph.add((CEO[rmarca], RDF.type, CEO.Marca))
        # Le asignamos una propiedad nombre a la marca
        products_graph.add((CEO[rmarca], CEO.nombre, Literal(rmarca)))
        # Creamos cinco instancias de modelo y le asignamos esta marca
        for k in range(5):
            # instancia al azar
            rmodelo = 'Modelo_' + str(j*5 + k)
            modelos[j*5 + k] = rmodelo
            # print(rmodelo)
            # Añadimos la instancia de modelo
            products_graph.add((CEO[rmodelo], RDF.type, CEO.Modelo))
            # Le asignamos una propiedad nombre al modelo
            products_graph.add((CEO[rmodelo], CEO.nombre, Literal(rmodelo)))
            # Le asignamos la marca que acabamos de crear
            products_graph.add((CEO[rmodelo], CEO.tiene_marca, CEO[rmarca]))
    
    for i in range(40):
        # generamos instancias de productos
        rproduct = 'Product_' + str(i)
        # print(rproduct)
        # Añadimos la instancia de producto
        products_graph.add((CEO[rproduct], RDF.type, CEO.Producto))
        # Le asignamos una propiedad nombre al producto
        products_graph.add((CEO[rproduct], CEO.nombre, Literal(rproduct)))
        # Le asignamos un modelo al producto
        products_graph.add((CEO[rproduct], CEO.tiene_modelo, CEO[modelos[i]]))
        
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
            products_graph.add((CEO[rproduct], CEO[prop_key], val)) 

        # generamos dos instancias de oferta para cada uno de los productos creados
        oferta1 = 'Oferta_1_' + rproduct
        oferta2 = 'Oferta_2_' + rproduct

        # Añadimos la instancia de oferta
        products_graph.add((CEO[oferta1], RDF.type, CEO.Oferta))
        products_graph.add((CEO[oferta2], RDF.type, CEO.Oferta))

        for of_key, of_value in ofert_properties.items():
            # el atributo es real
            if of_value == 'f':
                number = format(round(random.uniform(0, 100), 2), '.2f')
                number2 = format(round(random.uniform(0, 100), 2), '.2f')
                val = Literal(number)
                val2 = Literal(number2)
            # el atributo es entero
            elif of_value == 'i':
                val = Literal(random.randint(0, 50))
                val2 = Literal(random.randint(0, 50))
            # el atributo es string
            else:
                if of_key == 'gestion_envio':
                    tipoGestion = ['interna', 'externa']
                    val = Literal(random.choice(tipoGestion))
                    val2 = val
                else:
                    val = Literal(random_name(str(prop_key)))
                    val2 = Literal(random_name(str(prop_key)))

            products_graph.add((CEO[oferta1], CEO[of_key], val))
            products_graph.add((CEO[oferta2], CEO[of_key], val2))

        
        
        products_graph.add((CEO[rproduct], CEO.ofertado_en, CEO[oferta1]))
        products_graph.add((CEO[rproduct], CEO.ofertado_en, CEO[oferta2]))



    # Grabamos la ontologia resultante en turtle
    # Lo podemos cargar en Protege para verlo y cargarlo con RDFlib o en una triplestore (Fuseki)
    ofile = open('../informacion productos.ttl', "w")
    ofile.write(products_graph.serialize(format='turtle'))
    ofile.close()
