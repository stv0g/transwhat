#!/usr/bin/env python
# -*- encoding: UTF8 -*-

# author: Philipp Klaus, philipp.klaus →AT→ gmail.com

# This file is part of python-sipgate-xmlrpc.
#
# python-sipgate-xmlrpc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-sipgate-xmlrpc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-sipgate-xmlrpc. If not, see <http://www.gnu.org/licenses/>.


#####################################################################
###### This the most important file of the project:           #######
###### It contains the classe api, which                      #######
###### implements the XML-RPC communication with the          #######
###### Sipgate API.                                           #######

#from time import time
from sys import stderr
from xmlrpclib import ServerProxy, Fault, ProtocolError, ResponseError
from exceptions import TypeError
from socket import error as socket_error
import re

VERSION = "0.9.2"
NAME = "%s - python-sipgate-xmlrpc/sipgate.py"
VENDOR = "https://github.com/pklaus/python-sipgate-xmlrpc"

### ------- Here comes the most important piece of code: the api class with magic methods -----

class api (ServerProxy):
    def __init__ (self, username=False, password=False, prog_name=False, verbose=False):
        if not (username and password and prog_name):
            raise SipgateAPIException('To use the class sipgate.api you must provide, username, password and a program name.')
        address = SIPGATE_API_URL % {'username':username, 'password':password}
        ### The super() call would be more modern but it doesn't work with the current Python version yet.
        #super(api, self).__init__(address, verbose=debug)
        ServerProxy.__init__(self, address,verbose=verbose)
        ### It is considered good practice to Identify the client talking to the server:
        self.ClientIdentify({ "ClientName" : NAME % prog_name, "ClientVersion" : VERSION, "ClientVendor" : VENDOR })

    def __getattr__(self,name):
        return _Method(self.__request, name)

    def __request (self, methodname, params):
        if methodname.replace(API_PREFIX,'') not in VALID_METHODS:
            stderr.write( UNKNOWN_METHOD_MESSAGE % {
                'method': methodname.replace(API_PREFIX,''), 'api_prefix': API_PREFIX,
                'api_version': SIPGATE_API_DOC_V, 'api_date': SIPGATE_API_DOC_D } )
        if len(params)>0 and not type(params[0]) is dict:
            raise TypeError(DICT_AS_PARAM_MESSAGE % methodname.replace(API_PREFIX,''))
        method_function = ServerProxy.__getattr__(self,methodname)
        try:
            result = method_function(params[0] if len(params)>0 and type(params[0]) is dict else dict())
            # cast the result dictionary to a SipgateResponse (custom dictionary):
            result = SipgateResponse(result)
        except Fault, e:
            raise SipgateAPIFault(e.faultCode, e.faultString)
        except ProtocolError, e:
            raise SipgateAPIProtocolError(e.url, e.errcode, e.errmsg, e.headers)
        except socket_error, (value,message):
            raise SipgateAPISocketError(value, message)
        return result

## <http://stackoverflow.com/questions/2390827/how-to-properly-subclass-dict-and-override-get-set>
class SipgateResponse(dict):
    def __init__(self, response_dict):
        try:
            self.StatusCode, self.StatusString = int(response_dict['StatusCode']), response_dict['StatusString']
            self.success = self.StatusCode == 200
        except:
            raise TypeError(RESPONSE_NOT_A_DICTIONARY % response_dict)
        dict.__init__(self, response_dict)

class _Method:
    # With the help of this class the api class does not
    # need to state explicitly the possible XML-RPC calls.
    def __init__(self, send, name):
        self.__send = send
        self.__name = API_PREFIX+name
    def __call__(self, *args):
        return self.__send(self.__name, args)

### ------ now we define the exceptions that could occur ------

class SipgateAPIException(Exception):
    pass

class SipgateAPIFault(Fault, SipgateAPIException):
    # As this inherits from xmlrpclib.Fault it also has the
    # attributes faultCode and faultString.
    pass

class SipgateAPIProtocolError(ProtocolError, SipgateAPIException):
    # As this inherits from xmlrpclib.ProtocolError it also has the
    # attributes errcode and errmsg.
    pass

class SipgateAPISocketError(socket_error, SipgateAPIException):
    # As this inherits from socket.error it also has the
    # attributes .
    pass

### ------ This section contains message strings -------

UNKNOWN_METHOD_MESSAGE = "The method '%(method)s' for the API prefix '%(api_prefix)s' " + \
    "was called. This method, however, is currently not documented for the Sipgate API " + \
    "v%(api_version)s (%(api_date)s). Let's try but I've warned you.\n"
DICT_AS_PARAM_MESSAGE = 'Please specify a dictionary as function call parameter for api.%s().'
RESPONSE_NOT_A_DICTIONARY = 'The response "%s" does not seem to be a response from the ' + \
    'Sipgate XML-RPC API.'

### ------ This section contains constants of the Sipgate XML-RPC API -------

# This constant represents the version of the currently implemented Sipgate API
# ans is taken from the API description PDF:
SIPGATE_API_DOC_V = '1.06'
SIPGATE_API_DOC_D =  'August 21, 2007'

# Sipgate basic and plus accounts must use this API URL:
SIPGATE_API_URL = "https://%(username)s:%(password)s@samurai.sipgate.net/RPC2"
# Sipgate one and team have a different URL: api.sipgate.net.
# see <http://groups.google.com/group/sipgate-api/msg/51a3535b6d61241f>
API_PREFIX = 'samurai.'

VALID_METHODS = [
    'AccountStatementGet',
    'BalanceGet',
    'ClientIdentify',
    'HistoryGetByDate',
    'ItemizedEntriesGet',
    'OwnUriListGet',
    'PhonebookEntryGet',
    'PhonebookListGet',
    'RecommendedIntervalGet',
    'ServerdataGet',
    'SessionClose',
    'SessionInitiate',
    'SessionInitiateMulti',
    'SessionStatusGet',
    'TosListGet',
    'TosListGet',
    'UmSummaryGet',
    'UserdataGreetingGet',
    'UserdataSipGet',
]

SERVER_STATUS_CODES = {
    ### From Table A.1 and A.2 of the API docu: general server status codes
    200: 'Method success',
    400: 'Method not supported',
    401: 'Request denied (no reason specified)',
    402: 'Internal error',
    403: 'Invalid arguments',
    404: 'Resources exceeded (this MUST not be used to indicate parameters in error)',
    405: 'Invalid parameter name',
    406: 'Invalid parameter type',
    407: 'Invalid parameter value',
    408: 'Attempt to set a non-writable parameter',
    409: 'Notification request rejected.',
    410: 'Parameter exceeds maximum size.',
    411: 'Missing parameter.',
    412: 'Too many requests.',
    500: 'Date out of range.',
    501: 'Uri does not belong to user.',
    502: 'Unknown type of service.',
    503: 'Selected payment method failed.',
    504: 'Selected currency not supported.',
    505: 'Amount exceeds limit.',
    506: 'Malformed SIP URI.',
    507: 'URI not in list.',
    508: 'Format is not valid E.164.',
    509: 'Unknown status.',
    510: 'Unknown ID.',
    511: 'Invalid timevalue.',
    512: 'Referenced session not found.',
    513: 'Only single default per TOS allowed.',
    514: 'Malformed VCARD format.',
    515: 'Malformed PID format.',
    516: 'Presence information not available.',
    517: 'Invalid label name.',
    518: 'Label not assigned.',
    519: 'Label doesn’t exist.',
    520: 'Parameter includes invalid characters.',
    521: 'Bad password. (Rejected due to security concerns.)',
    522: 'Malformed timezone format.',
    523: 'Delay exceeds limit.',
    524: 'Requested VPN type not available.',
    525: 'Requested TOS not available.',
    526: 'Unified messaging not available.',
    527: 'URI not available for registration.',
}

TYPE_OF_SERVICE = {
    'fax':   'pages',      # fax transmission
    'text':  'characters', # text message (e.g. "SMS")
    'video': 'seconds',    # video communication
    'voice': 'seconds',    # voice communication
}


class helpers (object):
    @staticmethod
    def FQTN(phone_number, default_country_code):
        """
        Assures phone numbers are in the form of a E164 Fully Qualified Telephone Number
        without the leading + sign.
        The alternative would be the Python port of Google's libphonenumber:
        https://github.com/daviddrysdale/python-phonenumbers
        """
        phone_number = phone_number.replace(' ','').replace('-','').replace('+','').replace('/','')

        ## number starting with 00 (so it's an international format)
        if re.compile("^00[1-9][0-9]*$").match(phone_number):
            return phone_number[2:]

        ## number starting with your country code (so it was already a FQTN):
        if re.compile("^"+default_country_code+"[1-9][0-9]*$").match(phone_number):
            return phone_number

        if re.compile("^0[1-9]*$").match(phone_number):
            return default_country_code+phone_number[1:]

        if re.compile("^[1-9]*$").match(phone_number):
            return phone_number

        raise TypeError("Couldn't parse this phone number: "+phone_number)
