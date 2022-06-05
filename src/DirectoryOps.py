from rdflib import RDF, RDFS, Graph, Literal, Namespace
from AgentUtil.ACL import ACL

from AgentUtil.ACLMessages import build_message, send_message
from AgentUtil.Agent import Agent

CEO = Namespace("http://www.semanticweb.org/samragu/ontologies/comercio-electronico#")

def register_agent(agent, ds, logger):
    # Registro al ServicioDirectorio
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    ra = CEO.registraragente
    gm.add((ra, RDF.type, CEO.RegistrarAgente))
    gm.add((CEO.RegistrarAgente, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    a = CEO.agente
    gm.add((a, RDF.type, agent.uri))
    gm.add((agent.uri, RDFS.subClassOf, CEO.Agente))
    gm.add((a, CEO.direccion, Literal(agent.address)))
    gm.add((a, CEO.uri, agent.uri))
    gm.add((ra, CEO.con_agente, a))

    msg = build_message(gm,
                        ACL.request,
                        sender=agent.uri,
                        receiver=ds.uri,
                        content=ra)
    
    gr = send_message(msg, ds.address)

    if (None, ACL.performative, ACL.confirm) in gr:
        print('\n * Registro de agente CONFIRMADO')
    else:
        print('\n * Registro de agente NO confirmado')


def unregister_agent(agent, ds):
    # Desregistro del ServicioDirectorio
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)
    
    ra = CEO.desregistraragente
    gm.add((ra, RDF.type, CEO.DesregistrarAgente))
    gm.add((CEO.DesregistrarAgente, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    a = CEO.agente
    gm.add((a, RDF.type, agent.uri))
    gm.add((agent.uri, RDFS.subClassOf, CEO.Agente))
    gm.add((a, CEO.direccion, Literal(agent.address)))
    gm.add((a, CEO.uri, agent.uri))
    gm.add((ra, CEO.con_agente, a))

    msg = build_message(gm,
                        ACL.request,
                        sender=agent.uri,
                        receiver=ds.uri,
                        content=ra)
    
    gr = send_message(msg, ds.address)

    if (None, ACL.performative, ACL.confirm) in gr:
        print('\n * Desregistro de agente CONFIRMADO')
    else:
        print('\n * Desregistro de agente NO confirmado')


def search_agent(agn_uri, agent, ds):
    # Obtiene un agente
    gm = Graph()
    gm.namespace_manager.bind('rdf', RDF)
    gm.namespace_manager.bind('ceo', CEO)

    ba = CEO.buscaragente
    gm.add((ba, RDF.type, CEO.BuscarAgente))
    gm.add((CEO.BuscarAgente, RDFS.subClassOf, CEO.Accion))
    gm.add((CEO.Accion, RDFS.subClassOf, CEO.Comunicacion))

    a = CEO.agente
    gm.add((a, RDF.type, agn_uri))
    gm.add((agn_uri, RDFS.subClassOf, CEO.Agente))
    gm.add((ba, CEO.con_agente, a))

    msg = build_message(gm,
                        ACL.request,
                        sender=agent.uri,
                        receiver=ds.uri,
                        content=ba)

    gr = send_message(msg, ds.address)

    address = gr.value(subject=CEO.agente, predicate=CEO.direccion)

    print(' * Agent address: ' + address)

    return Agent('BuscadorProductos',
                 CEO.BuscadorProductos,
                 address,
                 '')