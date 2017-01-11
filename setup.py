# -*- coding: utf-8 -*-
"""Setup file for easy installation"""
from setuptools import setup


version = __import__('pyparams').__version__

LONG_DESCRIPTION = """
pyparams is a module for the processing of program parameters
from the command line, the environment or config files.

After a simple parameter specification, the parameters are
processed from the various sources.

"""


def long_description():
    return LONG_DESCRIPTION


setup(name='pyparams',
      version=version,
      author='Juergen Brendel',
      author_email='juergen@brendel.com',
      description='Simple, powerfule program parameter processing.',
      license='Apache',
      keywords='python, command line, parameters, environment, config file',
      url='https://github.com/jbrendel/pyparams',
      packages=['pyparams'],
      long_description=long_description(),
      install_requires=['ruamen.yaml','json'],
      classifiers=[
                   'License :: OSI Approved :: Apache License',
                   'Intended Audience :: Developers',
                   'Programming Language :: Python :: 2.7'],
      zip_safe=False)
