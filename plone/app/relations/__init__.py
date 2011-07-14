from Products.PluggableAuthService import registerMultiPlugin
from Products.CMFCore.permissions import ManagePortal
import local_role

registerMultiPlugin(local_role.RelationshipLocalRoleManager.meta_type)

def initialize(context):
    # Register our PAS plugin
    context.registerClass(local_role.RelationshipLocalRoleManager,
                          permission = ManagePortal,
                          constructors = (local_role.manage_addRelationshipLocalRoleManagerForm,
                                          local_role.manage_addRelationshipLocalRoleManager),
                          visibility = None)
