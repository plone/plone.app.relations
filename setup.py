from setuptools import setup, find_packages

version = '2.0'

setup(name='plone.app.relations',
      version=version,
      description="A set of components to provide a content centric API for "
        "the engine from plone.relations, as well as a few different core "
        "relationship types and policies.",
      long_description=open("README.txt").read() + "\n" +
                       open("CHANGES.txt").read(),
      classifiers=[
        "Framework :: Plone",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
        ],
      keywords='relationships references plone',
      author='Plone Foundation',
      author_email='plone-developers@lists.sourceforge.net',
      url='http://pypi.python.org/pypi/plone.app.relations',
      license='GPL version 2',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['plone', 'plone.app'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "setuptools",
          "plone.relations",
          "zope.site",
          "zope.intid",
          "Zope2 >= 2.13",
      ],
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
