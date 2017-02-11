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

import asyncore, socket
import logging
import sys

class IOChannel(asyncore.dispatcher):
	def __init__(self, host, port, callback, closeCallback):
		asyncore.dispatcher.__init__(self)

		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((host, port))
		self.logger = logging.getLogger(self.__class__.__name__)

		self.callback = callback
		self.closeCallback = closeCallback
		self.buffer = bytes("")

	def sendData(self, data):
		self.buffer += data

	def handle_connect(self):
		pass

	def handle_close(self):
		self.close()

	def handle_read(self):
		data = self.recv(65536)
		self.callback(data)

	def handle_write(self):
		sent = self.send(self.buffer)
		self.buffer = self.buffer[sent:]

	def handle_close(self):
		self.logger.info('Connection to backend closed, terminating.')
		self.close()
		self.closeCallback()

	def writable(self):
		return (len(self.buffer) > 0)

	def readable(self):
		return True
