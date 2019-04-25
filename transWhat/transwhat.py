#!/usr/bin/python

import argparse
import traceback
import logging
import asyncore
import sys
import queue

import Spectrum2
from yowsup.common import YowConstants
from yowsup.stacks import YowStack

from .whatsappbackend import WhatsAppBackend
from . import threadutils

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
parser.add_argument('--log', type=str)
parser.add_argument('--host', type=str, required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--service.backend_id', metavar="ID", type=int, required=True)
parser.add_argument('config', type=str)
parser.add_argument('-j', type=str, metavar="JID", required=True)

args, unknown = parser.parse_known_args()

YowConstants.PATH_STORAGE='/var/lib/spectrum2/' + args.j

if args.log is None:
    args.log = '/var/log/spectrum2/' + args.j + '/backends/backend.log'

# Logging
logging.basicConfig(
    filename = args.log,
    format = "%(asctime)-15s %(levelname)s %(name)s: %(message)s",
    level = logging.DEBUG if args.debug else logging.INFO
)

if args.config is not None:
    specConf = Spectrum2.Config(args.config)
else:
    specConf = None

# Handler
def handleTransportData(data):
    try:
        plugin.handleDataRead(data)
    except SystemExit as e:
        raise e
    except:
        logger = logging.getLogger('transwhat')
        logger.error(traceback.format_exc())

closed = False
def connectionClosed():
    global closed
    closed = True

# Main
io = Spectrum2.IOChannel(args.host, args.port, handleTransportData, connectionClosed)

plugin = WhatsAppBackend(io, args.j, specConf)

plugin.handleBackendConfig({
    'features': [
        ('send_buddies_on_login', 1),
        ('muc', 'true'),
    ],
})

def main():
    while True:
        try:
            asyncore.loop(timeout=1.0, count=10, use_poll = True)
            try:
                callback = YowStack._YowStack__detachedQueue.get(False) #doesn't block
                callback()
            except queue.Empty:
                pass
            else:
                break
            if closed:
                break
            while True:
                try:
                    callback = threadutils.eventQueue.get_nowait()
                except queue.Empty:
                    break
                else:
                    callback()
        except SystemExit:
            break
        except:
            logger = logging.getLogger('transwhat')
            logger.error(traceback.format_exc())
