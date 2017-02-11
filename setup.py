import os
import codecs
from setuptools import setup


def read_file(filename, encoding='utf8'):
    """Read unicode from given file."""
    with codecs.open(filename, encoding=encoding) as fd:
        return fd.read()


here = os.path.abspath(os.path.dirname(__file__))
readme = read_file(os.path.join(here, 'README.rst'))


setup(name='transwhat',
	version='0.2.2',
	description='A gateway between the XMPP and the WhatsApp IM networks',
	long_description=readme,
	keywords='whatsapp xmpp im gateway transport yowsup',
	url='https://github.com/stv0g/transwhat',
	author='Steffen Vogel',
	author_email='stv0g@0l.de',
	classifiers=[
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Development Status :: 4 - Beta',
		'Environment :: Plugins',
		'Operating System :: POSIX',
		'Topic :: Communications :: Chat'
	],
	license='GPL-3+',
	packages=[
		'transWhat',
		'Spectrum2'
	],
	install_requires=[
		'protobuf',
		'yowsup2',
		'e4u',
		'Pillow',
		'python-dateutil'
	],
	entry_points={
		'console_scripts': ['transwhat=transWhat.transwhat:main'],
	},
	zip_safe=False,
	include_package_data=True
)
