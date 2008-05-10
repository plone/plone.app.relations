from setuptools import setup, find_packages

version = '1.0b2'

setup(name='plone.app.relations',
      version=version,
      description="A set of components to provide a content centric API for the engine from plone.relations, as well as a few different core relationship types and policies.",
      long_description="""\
""",
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Framework :: Zope2",
        "Framework :: Zope3",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='relationships references plone',
      author='Alec Mitchell',
      author_email='apm13@columbia.edu',
      url='http://svn.plone.org/svn/plone/plone.app.relations',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['plone.app'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "plone.relations",
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
