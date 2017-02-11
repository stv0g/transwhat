# transWhat

transWhat is a WhatsApp XMPP Gateway based on Spectrum2                         

#### Branches

 - [yowsup-1](http://github.com/stv0g/transwhat/tree/yowsup-1) My original version which is based on @tgalal first Yowsup version (**deprecated** and broken).
 - [yowsup-2](http://github.com/stv0g/transwhat/tree/yowsup-2) Major rewrite from @moyamo for @tgalal's new Yowsup 2 (**recommended**).

For production, please use the `yowsup-2` branch.

## Dependencies

#### Spectrum 2
is a XMPP transport

Manual compile latest version from https://github.com/hanzz/libtransport

#### e4u
is a simple emoji4unicode python wrapper library

Install with `pip install e4u`

#### Yowsup
is a Implementation of the WhatsApp protocol in python

Use my patched version at https://github.com/stv0g/yowsup

#### Google Atom and GData Python wrappers
required for Google contacts import

## Contribute

Pull requests, bug reports etc. are welcome.
Help us to provide a open implementation of the WhatsApp protocol.

## Documentation

A project wiki is available [here](http://dev.0l.de/projects/transwhat/start).
A mailinglist for discussion is available [here](http://lists.0l.de/listinfo/whatsapp).

A writeup of this project is also availabe at my [blog](http://www.steffenvogel.de/2013/06/29/transwhat/).
