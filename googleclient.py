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

import sys

import gdata.gauth
import gdata.contacts.client
import gdata.contacts.data
import atom.data

from constants import *

gdata.contacts.REL_MOBILE='http://schemas.google.com/g/2005#mobile'

class GoogleClient():

	def __init__(self):
		self.client = gdata.contacts.client.ContactsClient()
	#	self.token = gdata.gauth.OAuth2Token(
	#		client_id = GOOGLE_CLIENT_ID,
	#		client_secret = GOOGLE_CLIENT_SECRET,
	#		scope = 'https://www.google.com/m8/feeds/contacts',
	#		user_agent = 'whatTrans'
	#	)

	def getTokenUrl(self, uri = 'urn:ietf:wg:oauth:2.0:oob'):
		return self.token.generate_authorize_url(redirect_uri=uri)

	def getContacts(self, request_token):
		access_token = self.token.get_access_token(request_token)

		self.token.authorize(self.client)

		numbers = { }

		feed = self.client.GetContacts()
		while feed:
			for i, entry in enumerate(feed.entry):
				for number in entry.phone_number:
					numbers[number.text] = entry.title.text

			next = feed.GetNextLink()
			if next:
				feed = self.client.GetContacts(next.href)
			else:
				break

		return numbers
