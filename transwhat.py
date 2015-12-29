#!/usr/bin/python

__author__ = u"Steffen Vogel"
__copyright__ = u"Copyright 2015, Steffen Vogel"
__license__ = u"GPLv3"
__maintainer__ = u"Steffen Vogel"
__email__ = u"post@steffenvogel.de"

u"""
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
import e4u
import threading
import Queue

sys.path.insert(0, os.getcwd())

from Spectrum2.iochannel import IOChannel

from whatsappbackend import WhatsAppBackend
from yowsup.common import YowConstants
from yowsup.stacks import YowStack

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument(u'--debug', action=u'store_true')
parser.add_argument(u'--host', type=str, required=True)
parser.add_argument(u'--port', type=int, required=True)
parser.add_argument(u'--service.backend_id', metavar=u"ID", type=int, required=True)
parser.add_argument(u'config', type=str)
parser.add_argument(u'-j', type=str, required=True)

args, unknown = parser.parse_known_args()

YowConstants.PATH_STORAGE=u'/var/lib/spectrum2/' + args.j
loggingfile = u'/var/log/spectrum2/' + args.j + u'/backends/backend.log'
# Logging
logging.basicConfig( \
	filename=loggingfile,\
	format = u"%(asctime)-15s %(levelname)s %(name)s: %(message)s", \
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
io = IOChannel(args.host, args.port, handleTransportData, connectionClosed)

plugin = WhatsAppBackend(io, args.j)

plugin.handleBackendConfig({
	u'features': [
		(u'send_buddies_on_login', 1),
		(u'muc', u'true'),
	],
})

while True:
	try:
		asyncore.loop(timeout=1.0, count=10, use_poll = True)
		try:
			callback = YowStack._YowStack__detachedQueue.get(False) #doesnu't block
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
