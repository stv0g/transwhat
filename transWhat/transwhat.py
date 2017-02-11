#!/usr/bin/python

# use unicode encoding for all literals by default (for python2.x)
from __future__ import unicode_literals

__author__ = "Steffen Vogel"
__copyright__ = "Copyright 2015-2017, Steffen Vogel"
__license__ = "GPLv3"
__maintainer__ = "Steffen Vogel"
__email__ = "post@steffenvogel.de"

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
import e4u
import Queue
import threadutils

sys.path.insert(0, os.getcwd())

from Spectrum2.iochannel import IOChannel
from config import SpectrumConfig
from whatsappbackend import WhatsAppBackend
from yowsup.common import YowConstants
from yowsup.stacks import YowStack

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
	specConf = SpectrumConfig(args.config)
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

e4u.load()

closed = False
def connectionClosed():
	global closed
	closed = True

# Main
io = IOChannel(args.host, args.port, handleTransportData, connectionClosed)

plugin = WhatsAppBackend(io, args.j, specConf)

plugin.handleBackendConfig({
	'features': [
		('send_buddies_on_login', 1),
		('muc', 'true'),
	],
})


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
		while True:
			try:
				callback = threadutils.eventQueue.get_nowait()
			except Queue.Empty:
				break
			else:
				callback()
	except SystemExit:
		break
	except:
		logger = logging.getLogger('transwhat')
		logger.error(traceback.format_exc())
