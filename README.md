# transWhat

transWhat is a WhatsApp XMPP Gateway based on [Spectrum 2](http://www.spectrum.im) and [Yowsup 2](https://github.com/tgalal/yowsup).

## Getting started

I assume that you have a basic understanding of XMPP and the transport concept.
transWhat is a XMPP transport. It is based on the Spectrum 2 XMPP transport framework and the Yowsup 2 library to interface with WhatsApp.

Before getting started, please make sure that you have a XMPP server running.
I am using Prosody for this.

After this we have to install several dependencies:

### Dependencies

#### Python packages

    pip install --pre e4u protobuf mysql python-dateutil

  - **e4u**: is a simple emoji4unicode python bindings
  - [**yowsup**](https://github.com/tgalal/yowsup): is a python library that enables you build application which use WhatsApp service.
  - **mysqldb**: MySQL client python bindings

#### Spectrum 2

Manual compile latest version from [Github](https://github.com/hanzz/libtransport).
You can use the following guide: http://spectrum.im/documentation/installation/from_source_code.html.

### Installation

    git clone git@github.com:stv0g/transwhat.git

### Configuration of Prosody

See http://prosody.im/doc/components.

    Component "whatsapp.0l.de"
         component_secret = "whatsappsucks"
        component_ports = { 5221 }
        component_interface = "127.0.0.1"

### Configuration of Spectrum

### Configuration of transWhat

First create a mySQL database named `transwhat` and fill it with the [schema](https://raw.githubusercontent.com/stv0g/transwhat/yowsup-2/conf/schema.sql) provided in the repo.

## Docker

In near future, there will be a Dockerfile for transWhat.

## Contributors

Pull requests, bug reports etc. are welcome. Help us to provide a open implementation of the WhatsApp protocol.

The following persons have contributed major parts of this code:

  - @stv0g (Steffen Vogel): Idea and initial implementation based on Yowsup 1
  - @moyamo (Mohammed Yaseen Mowzer): Port to Yowsup 2
  - @DaZZZl: Improvements to group chats, media & message receipts

## Documentation

A project wiki is available [here](https://dev.0l.de/wiki/projects/transwhat/).

An *outdated* writeup of this project is also availabe at my [blog](http://www.steffenvogel.de/2013/06/29/transwhat/).
