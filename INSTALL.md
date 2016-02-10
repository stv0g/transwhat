# Installation and configuration guide

I assume that you have a basic understanding of XMPP and the the concept of a XMPP component / transport. If not, please get a book about Jabber or read the standards.

transWhat is a XMPP transport. By this means it extends the functionallity of an existing XMPP server. It acts as a gateway between the XMPP and WhatsApp networks. It receives WhatsApp messages and forwards them to your XMPP client (and vice-versa).

The implementation of transWhat is based on the [Spectrum 2](http://www.spectrum.im) framework and the [Yowsup 2](https://github.com/tgalal/yowsup) library to interface with WhatsApp.

The following chart summarizes the involved components and the protocols they use to communicate.

## Prosody

### Installation

I will not cover the installation of Prosody in this guide. Please look for some other tutorials on how to do that.

### Configuration

The only important thing for us is the configuration of a XMPP component (Spectrum 2 in our case).
See http://prosody.im/doc/components.

Append the following at the end of `/etc/prosody/prosody.cfg.lua`

    Component "whatsapp.0l.de"
        component_secret = "whatsappsucks"
        component_ports = { 5221 }
        component_interface = "127.0.0.1"

## Spectrum 2

#### Installation

Manual compile latest version from [Github](https://github.com/hanzz/libtransport).
You can use the following guide: http://spectrum.im/documentation/installation/from_source_code.html.

#### Configuration

Create a new file `/etc/spectrum2/transports/whatsapp.cfg` with the following content:

    [service]
    user = spectrum
    group = spectrum

    jid = whatsapp.0l.de

    server = localhost
    password = whatsappsucks
    port = 5221

    backend_host = localhost
    backend = /location/to/transwhat/transwhat.py
    
    users_per_backend = 10
    more_resources = 1
    
    admin_jid = your@jid.example
    
    [identity]
    name = transWhat
    type = xmpp
    category = gateway
    
    [logging]
    config = /etc/spectrum2/logging.cfg
    backend_config = /etc/spectrum2/backend-logging.cfg
    
    [database]
    type = sqlite3

## transWhat

### Installation

Checkout the latest version of transWhat from GitHub:

    $ git clone git@github.com:stv0g/transwhat.git
    
Install required dependencies:

    $ pip install --pre e4u protobuf python-dateutil yowsup2

  - **e4u**: is a simple emoji4unicode python bindings
  - [**yowsup**](https://github.com/tgalal/yowsup): is a python library that enables you build application which use WhatsApp service.
