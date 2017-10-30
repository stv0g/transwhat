transWhat
=========

transWhat is a WhatsApp XMPP Gateway based on `Spectrum 2`_ and `Yowsup 2`_.

Support
-------

For support and discussions please join the XMPP MUC: **transwhat@conference.0l.de**.

Features
--------

-  Typing notifications
-  Receive images, audio & video
-  Set/get online status
-  Set status message
-  Groupchats

Installation
------------

transWhat requires a running and configured XMPP server.
Detailed instructions can be found on the `Installation`_ page.

Users find details on the  `Usage`_ page.

Branches
--------

-  `yowsup-1`_ My original version which is based on @tgalal first
   Yowsup version (**deprecated** and broken).
-  `yowsup-2`_ Major rewrite from @moyamo for @tgalal’s new Yowsup 2
   (**recommended**).

For production, please use the ``yowsup-2`` branch.

Contributors
------------

Pull requests, bug reports etc. are welcome. Help us to provide a open
implementation of the WhatsApp protocol.

The following persons have contributed major parts of this code:

-  @stv0g (Steffen Vogel): Idea and initial implementation based on
   Yowsup 1
-  @moyamo (Mohammed Yaseen Mowzer): Port to Yowsup 2
-  @DaZZZl: Improvements to group chats, media & message receipts

License
-------

transWhat is licensed under the GPLv3_ license.

Links
-----

-  An *outdated* project wiki is available `here`_.
-  An *outdated* writeup of this project is also availabe at my `blog`_.

.. _Spectrum 2: http://www.spectrum.im
.. _Yowsup 2: https://github.com/tgalal/yowsup
.. _yowsup-1: http://github.com/stv0g/transwhat/tree/yowsup-1
.. _yowsup-2: http://github.com/stv0g/transwhat/tree/yowsup-2
.. _Installation: INSTALL.rst
.. _Usage: USAGE.rst
.. _GPLv3: COPYING.rst
.. _here: https://dev.0l.de/wiki/projects/transwhat/
.. _blog: http://www.steffenvogel.de/2013/06/29/transwhat/
