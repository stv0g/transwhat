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

import threading
import inspect
import re
import urllib
import time
import os
import utils

class Bot():
	def __init__(self, session, name = "Bot"):
		self.session = session
		self.name = name

		self.commands = {
			"help": self._help,
			"groups": self._groups,
			"getgroups": self._getgroups
		}

	def parse(self, message):
		args = message.strip().split(" ")
		cmd = args.pop(0)

		if len(cmd) > 0 and cmd[0] == '\\':
			try:
				self.call(cmd[1:], args)
			except KeyError:
				self.send("invalid command")
			except TypeError:
				self.send("invalid syntax")
		else:
			self.send("a valid command starts with a backslash")

	def call(self, cmd, args = []):
		func = self.commands[cmd.lower()]
		spec = inspect.getargspec(func)
		maxs = len(spec.args) - 1
		reqs = maxs - len(spec.defaults or [])
		if (reqs > len(args)) or (len(args) > maxs):
			raise TypeError()

		thread = threading.Thread(target=func, args=tuple(args))
		thread.start()

	def send(self, message):
		self.session.backend.handleMessage(self.session.user, self.name, message)

	# commands
	def _help(self):
		self.send("""following bot commands are available:
\\help			show this message

following user commands are available:
\\lastseen		request last online timestamp from buddy

following group commands are available
\\leave			permanently leave group chat
\\groups		print all attended groups
\\getgroups		get current groups from WA""")

	def _groups(self):
		for group in self.session.groups:
			buddy = self.session.groups[group].owner
			try:
				nick = self.session.buddies[buddy].nick
			except KeyError:
				nick = buddy

			self.send(self.session.groups[group].id + "@" + self.session.backend.spectrum_jid + " " + self.session.groups[group].subject + " Owner: " + nick )

	def _getgroups(self):
		#self.session.call("group_getGroups", ("participating",))
		self.session.requestGroupsList(self.session._updateGroups)

