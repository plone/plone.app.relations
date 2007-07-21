from Products.GenericSetup import EXTENSION, profile_registry
from Products.CMFCore.interfaces import ISiteRoot

from Products.PluggableAuthService import registerMultiPlugin
from Products.CMFCore.permissions import ManagePortal
import local_role

registerMultiPlugin(local_role.RelationshipLocalRoleManager.meta_type)

def initialize(context):
    """Intializer called when used as a Zope 2 product."""

    # Register our PAS plugin
    context.registerClass(local_role.RelationshipLocalRoleManager,
                          permission = ManagePortal,
                          constructors = (local_role.manage_addRelationshipLocalRoleManagerForm,
                                          local_role.manage_addRelationshipLocalRoleManager),
                          visibility = None)

    profile_registry.registerProfile('default',
                                     'plone.app.relations',
                                     'Extension profile for plone.app.relatons',
                                     'profiles/default',
                                     'plone.app.relations',
                                     EXTENSION,
                                     for_=ISiteRoot)
