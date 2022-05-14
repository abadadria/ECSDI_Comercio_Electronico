"""
.. module:: Logging

Logging
******

:Description: Logging

    Configura un logger para poder registrar la actividad de un programa por salida
    estandar o fichero

    crear el logger con:

    logger = config_logger(level=1)

    registrar eventos con:

    logger.info('alguna informacion %s %s', var1, var2)
    logger.debug('esta variable vale %d', var)
    logger.warning('alguna cosa va mal')
    logger.error('esto no funciona')

    Detalles en https://docs.python.org/2/howto/logging.html

:Authors:
    bejar

:Version: 

:Date:  01/04/2015
"""

import logging

__author__ = 'bejar'

def config_logger(level=0, file=None):
    """
    Configure the logging of a program
    Log is written in stdio, alternatively also in a file

    :param level: If level is 0 only errors are logged, else all is logged
    :param file: Log is written in a file,
    :return:
    """
    if file is not None:
        logging.basicConfig(filename=file + '.log', filemode='w')

    # Logging configuration
    logger = logging.getLogger('log')
    if level == 0:
        logger.setLevel(logging.ERROR)
    else:
        logger.setLevel(logging.INFO)


    console = logging.StreamHandler()
    if level == 0:
        console.setLevel(logging.ERROR)
    else:
        console.setLevel(logging.INFO)

    formatter = logging.Formatter('[%(asctime)-15s] - %(filename)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('log').addHandler(console)
    return logger