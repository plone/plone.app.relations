from Products.GenericSetup import EXTENSION, profile_registry
from Products.CMFCore.interfaces import ISiteRoot

def initialize(context):
    """Intializer called when used as a Zope 2 product."""
    profile_registry.registerProfile('default',
                                     'plone.app.relations',
                                     'Extension profile for plone.app.relatons',
                                     'profiles/default',
                                     'plone.app.relations',
                                     EXTENSION,
                                     for_=ISiteRoot)
