# ECSDI_Comercio_Electronico

## Authors
- Adrià Abad Moreno
- Raül Sampietro Gutierrez

========================
Descripcióin del sistema
========================

Sistema distribuido para un comercio electrónico

El sistema esta formado por los siguientes agentes:

 * Agentes/ServicioDirectorio.py

    Mantiene un registro de los agentes y actores que pueden ser contactados en el sistema

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9000 por defecto)

 * Agentes/BuscadorProductos.py

    Motor de busqueda de productos

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9010 por defecto)
      --dir = Direccion completa del servicio de directorio

 * Agentes/GestorProductosExternos.py

    Interfaz de entrada de las actualizaciones de productos de los ComerciosExternos.
    Reparte la información de los productos que le llegan entre los otros agentes.

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9001 por defecto)
      --dir = Direccion completa del servicio de directorio

 * Agentes/GestorPedidos.py

    Crea y gestiona los pedidos activos

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9020 por defecto)
      --dir = Direccion completa del servicio de directorio

 * Agentes/GestorEnvios.py

    Gestiona y organiza los envios de los pedidos activos

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9030 por defecto)
      --dir = Direccion completa del servicio de directorio

 * Agentes/CentroLogistico.py

    Contrata los envios de los productos que almacena en sí.

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9060 por defecto)
      --dir = Direccion completa del servicio de directorio

El sistema interactua con los siguientes actores:

 * Actors/Asitente.py

    Interfaz del usuario con el sistema mediante CLI.

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9000 por defecto)
      --dir = Direccion completa del servicio de directorio

 * Actors/ComercioExterno.py

    Comercio externo al sistema que pone a la venta sus productos.

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9040 por defecto)
      --dir = Direccion completa del servicio de directorio

 * Actors/AgenciaTransporte.py

    Ofrece transporte de productos a cambio de dinero.

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9050 por defecto)
      --dir = Direccion completa del servicio de directorio

 * Actors/GestorPagos.py

    Efectua los pagos relacionados con el sistema.

    Parametros
      --open = permite conexiones desde hosts remotos (no por defecto)
      --verbose = va escribiendo por terminal las peticiones que recibe el servidor http
      --port = port de comunicacion (9004 por defecto)
      --dir = Direccion completa del servicio de directorio

=====================
Ejecución del sistema
=====================

 1. Situarse en el directorio /src

 2. Iniciar el ServicioDirectorio

    $ python3 Agentes/ServicioDirectorio.py

 3. Iniciar 3 instancias de agente CentroLogistico con puertos diferentes entre 9060 y 9069

    $ python3 Agentes/CentroLogistico.py --dir http://nombre.de.la.maquina:9000 --port 9060
    $ python3 Agentes/CentroLogistico.py --dir http://nombre.de.la.maquina:9000 --port 9061
    $ python3 Agentes/CentroLogistico.py --dir http://nombre.de.la.maquina:9000 --port 9062     

 4. Iniciar 1 instancia del resto de agentes indicando la dirección completa del ServicioDirectorio

    $ python3 Actors/NombreAgente.py --dir http://nombre.de.la.maquina:9000  

 5. Iniciar hasta 3 instancias de actor ComercioExterno con puertos 9040, 9041 y 9042 respectivamente

    $ python3 Actors/ComercioExterno.py --dir http://nombre.de.la.maquina:9000 --port 9040
    $ python3 Actors/ComercioExterno.py --dir http://nombre.de.la.maquina:9000 --port 9041
    $ python3 Actors/ComercioExterno.py --dir http://nombre.de.la.maquina:9000 --port 9042     

 6. Iniciar 1 instancia del resto de actores indicando la dirección completa del ServicioDirectorio

    $ python3 Actors/NombreActor.py --dir http://nombre.de.la.maquina:9000  

 7. Usar el sistema mediante el CLI del actor Asistente