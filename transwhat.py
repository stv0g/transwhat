#!/usr/bin/python

__author__ = "Steffen Vogel"
__copyright__ = "Copyright 2013, Steffen Vogel"
__license__ = "GPLv3"
__maintainer__ = "Steffen Vogel"
__email__ = "post@steffenvogel.de"
__status__ = "Prototype"

"""
 This file is part of transWhat

 transWhat is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 any later version.

 transwhat is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with transWhat. If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import traceback
import logging
import asyncore
import sys, os
import MySQLdb
import e4u
import threading
import Queue

sys.path.insert(0, os.getcwd())

from Spectrum2.iochannel import IOChannel

from whatsappbackend import WhatsAppBackend
from constants import *
from yowsup.common import YowConstants
from yowsup.stacks import YowStack

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true')
parser.add_argument('--host', type=str, required=True)
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--service.backend_id', metavar="ID", type=int, required=True)
parser.add_argument('config', type=str)
parser.add_argument('-j', type=str, required=True)

args, unknown = parser.parse_known_args()

YowConstants.PATH_STORAGE='/var/lib/spectrum2/' + args.j
loggingfile = '/var/log/spectrum2/' + args.j + '/backends/backend.log'
# Logging
logging.basicConfig( \
	filename=loggingfile,\
	format = "%(asctime)-15s %(levelname)s %(name)s: %(message)s", \
	level = logging.DEBUG if args.debug else logging.INFO \
)

# Handler
def handleTransportData(data):
	plugin.handleDataRead(data)

e4u.load()

closed = False
def connectionClosed():
	global closed
	closed = True

# Main
db = MySQLdb.connect(DB_HOST, DB_USER, DB_PASS, DB_TABLE)
io = IOChannel(args.host, args.port, handleTransportData, connectionClosed)

plugin = WhatsAppBackend(io, db)

while True:
	try:
		asyncore.loop(timeout=1.0, count=10, use_poll = True)
		try:
			callback = YowStack._YowStack__detachedQueue.get(False) #doesn't block
			callback()
		except Queue.Empty:
			pass
		else:
			break
		if closed:
			break
	except SystemExit:
		break
	except:
		logger = logging.getLogger('transwhat')
		logger.error(traceback.format_exc())
