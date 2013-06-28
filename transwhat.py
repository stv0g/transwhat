#!/usr/bin/python

import argparse
import logging
import asyncore
import sys, os
import MySQLdb
import e4u
import threading

sys.path.insert(0, os.getcwd())

from Spectrum2.iochannel import IOChannel

from whatsappbackend import WhatsAppBackend
from constants import *

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
parser.add_argument('--host', type=str, required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--service.backend_id', metavar="ID", type=int, required=True)
parser.add_argument('config', type=str)

args, unknown = parser.parse_known_args()

# Logging
logging.basicConfig( \
	format = "%(asctime)-15s %(levelname)s %(name)s: %(message)s", \
	level = logging.DEBUG if args.debug else logging.INFO \
)

# Handler
def handleTransportData(data):
	plugin.handleDataRead(data)

e4u.load()

# Main
db = MySQLdb.connect(DB_HOST, DB_USER, DB_PASS, DB_TABLE)
io = IOChannel(args.host, args.port, handleTransportData)

plugin = WhatsAppBackend(io, db)

asyncore.loop(1)
