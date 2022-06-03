from rdflib import RDF, RDFS, Graph, Literal, Namespace
from AgentUtil.ACL import ACL

from AgentUtil.ACLMessages import build_message, send_message

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

    logger.info('Peticion de registro al ServicioDirectorio')
    logger.info(gm.serialize(format='turtle'))

    msg = build_message(gm,
                        ACL.request,
                        sender=agent.uri,
                        receiver=ds.uri,
                        content=ra)
    
    gr = send_message(msg, ds.address)

    logger.info(gr.serialize(format='turtle'))

    if (None, ACL.performative, ACL.confirm) in gr:
        print('\n  * Registro de agente CONFIRMADO')
    else:
        print('\n  * Registro de agente NO confirmado')

