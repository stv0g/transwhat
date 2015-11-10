# transWhat

transWhat is a WhatsApp XMPP Gateway based on [Spectrum 2](http://www.spectrum.im) and [Yowsup 2](https://github.com/tgalal/yowsup).

## Dependencies

#### Python packages

    pip install e4u protobuf mysql dateutil

  - **e4u**: is a simple emoji4unicode python bindings
  - [**yowsup**](https://github.com/tgalal/yowsup): is a python library that enables you build application which use WhatsApp service.
  - **mysqldb**: MySQL client python bindings

#### Spectrum 2
is a XMPP transport

Manual compile latest version from https://github.com/hanzz/libtransport.

## Contributors

Pull requests, bug reports etc. are welcome. Help us to provide a open implementation of the WhatsApp protocol.

The following persons have contributed major parts of this code:

  - **Steffen Vogel** (@stv0g): Idea and initial implementation based on Yowsup 1
  - **Mohammed Yaseen Mowzer** (@moyamo): Port to Yowsup 2

## Documentation

A project wiki is available [here](https://dev.0l.de/wiki/projects/transwhat/).

An *outdated* writeup of this project is also availabe at my [blog](http://www.steffenvogel.de/2013/06/29/transwhat/).
