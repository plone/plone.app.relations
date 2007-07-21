from Globals import InitializeClass
from Acquisition import aq_inner, aq_parent, aq_base
from AccessControl import ClassSecurityInfo
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zope.component import getAdapters

from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin

from plone.app.relations.interfaces import ILocalRoleProvider

manage_addRelationshipLocalRoleManagerForm = PageTemplateFile(
        "AddLocalRoleManagerForm.pt", globals(),
        __name__="manage_addRelationshipRoleManagerForm")

def manage_addRelationshipLocalRoleManager(dispatcher, id, title=None,
                                           REQUEST=None):
    """Add a ProjectLocalRoleManager to a Pluggable Authentication Services."""
    lrm = RelationshipLocalRoleManager(id, title)
    dispatcher._setObject(lrm.getId(), lrm)

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(
                '%s/manage_workspace?manage_tabs_message='
                'RelationshipLocalRoleManager+added.'%dispatcher.absolute_url())

class RelationshipLocalRoleManager(BasePlugin):
    """Though it's aimed for use in defining local roles based on relationships,
    this local role manager is completely generic, and simply uses the Zope 3
    CA to look up local role providing components via adaptation.  Essentially
    this is the result of my being to lazy to write individual persistent
    plugins for every different usecase which may come up.


    First we need to make and register an adapter to provide some roles::

        >>> from zope.interface import implements, Interface
        >>> from zope.component import adapts
        >>> class SimpleLocalRoleProvider(object):
        ...     adapts(Interface)
        ...     implements(ILocalRoleProvider)
        ...
        ...     def __init__(self, context):
        ...         self.context = context
        ...
        ...     def getRoles(self, user):
        ...         '''Grant everyone the 'Foo' role'''
        ...         return ('Foo',)
        ...
        ...     def getAllRoles(self):
        ...         '''In the real world we would enumerate all users and
        ...         grant the 'Foo' role to each, but we won't'''
        ...         yield ('bogus_user', ('Foo',))

        >>> from zope.component import provideAdapter
        >>> provideAdapter(SimpleLocalRoleProvider)


    We need an object to adapt, we require nothing of this object,
    except it must be adaptable::

        >>> class DummyObject(object):
        ...     implements(Interface)
        >>> ob = DummyObject()

    And we need some users that we'll check the permissions of::

        >>> class DummyUser(object):
        ...     def __init__(self, uid):
        ...         self.id = uid
        ...
        ...     def _check_context(self, obj):
        ...         return True
        >>> user1 = DummyUser('bogus_user')
        >>> user2 = DummyUser('bogus_user2')

    Now we're ready to make one of our RoleManagers and try it out.
    First we'll verify that our users have the 'Foo' role, then we'll
    make sure they can access objects which require that role, but not
    others::

        >>> rm = RelationshipLocalRoleManager('rm', 'A Role Manager')
        >>> rm.getRolesInContext(user1, ob)
        ['Foo']
        >>> rm.checkLocalRolesAllowed(user1, ob, ['Bar', 'Foo', 'Baz'])
        1
        >>> rm.checkLocalRolesAllowed(user1, ob, ['Bar', 'Baz']) is None
        True
        >>> rm.getAllLocalRolesInContext(ob)
        {'bogus_user': set(['Foo'])}

    It is a bit more interesting when we have more than one adapter registered::

        >>> class LessSimpleLocalRoleProvider(SimpleLocalRoleProvider):
        ...     def getRoles(self, user):
        ...         '''Grant bogus_user2 the 'Foo' and 'Baz' roles'''
        ...         if user.id == 'bogus_user2':
        ...             return ('Foo', 'Baz')
        ...         return ()
        ...
        ...     def getAllRoles(self):
        ...         yield ('bogus_user2', ('Foo', 'Baz'))

        >>> provideAdapter(LessSimpleLocalRoleProvider, name='adapter2')

   This should have no effect on our first user::

        >>> rm.getRolesInContext(user1, ob)
        ['Foo']
        >>> rm.checkLocalRolesAllowed(user1, ob, ['Bar', 'Foo', 'Baz'])
        1
        >>> rm.checkLocalRolesAllowed(user1, ob, ['Bar', 'Baz']) is None
        True
        >>> rm.getAllLocalRolesInContext(ob)
        {'bogus_user2': set(['Foo', 'Baz']), 'bogus_user': set(['Foo'])}

    But our second user notices the change, note that even though two
    of our local role providers grant the role 'Foo', it is not duplicated::

        >>> rm.getRolesInContext(user2, ob)
        ['Foo', 'Baz']
        >>> rm.checkLocalRolesAllowed(user2, ob, ['Bar', 'Foo', 'Baz'])
        1
        >>> rm.checkLocalRolesAllowed(user2, ob, ['Bar', 'Baz'])
        1
        >>> rm.checkLocalRolesAllowed(user2, ob, ['Bar']) is None
        True

    Finally, to ensure full test coverage, we provide a user object
    which pretends to be wrapped in such a way that the user object
    does not recognize it.  We check that it always gets an empty set
    of roles and a special 0 value when checking access::

        >>> class BadUser(DummyUser):
        ...     def _check_context(self, obj):
        ...         return False
        >>> bad_user = BadUser('bad_user')
        >>> rm.getRolesInContext(bad_user, ob)
        []
        >>> rm.checkLocalRolesAllowed(bad_user, ob, ['Bar', 'Foo', 'Baz'])
        0

    """
    meta_type = "Relationship Roles Manager"
    security  = ClassSecurityInfo()

    def __init__(self, id, title=''):
        self.id = id
        self.title = title

    #
    # ILocalRolesPlugin implementation
    #

    def _getAdapters(self, obj):
        adapters = getAdapters((obj,), ILocalRoleProvider)
        # this is sequence of tuples of the form (name, adapter),
        # we don't really care about the names
        return (a[1] for a in adapters)

    def _parent_chain(self, obj):
        """Iterate over the containment chain, stopping if we hit a
        local role blocker"""
        while obj is not None:
            obj = aq_inner(obj)
            yield obj
            if getattr(obj, '__ac_local_roles_block__', None):
                raise StopIteration
            obj = aq_parent(obj)
            obj = getattr(obj, 'im_self', obj)

    security.declarePrivate("getRolesInContext")
    def getRolesInContext(self, user, object):
        roles = set()
        if user._check_context(object):
            for obj in self._parent_chain(object):
                for a in self._getAdapters(obj):
                    roles.update(a.getRoles(user))
        return list(roles)

    security.declarePrivate("checkLocalRolesAllowed")
    def checkLocalRolesAllowed(self, user, object, object_roles):
        roles = []
        if not user._check_context(object):
            return 0
        for role in self.getRolesInContext(user, object):
            if role in object_roles:
                return 1
        return None

    security.declarePrivate("getAllLocalRolesInContext")
    def getAllLocalRolesInContext(self, object):
        rolemap = {}
        for obj in self._parent_chain(object):
            for a in self._getAdapters(obj):
                iter_roles = a.getAllRoles()
                for principal, roles in iter_roles:
                    rolemap.setdefault(principal, set()).update(roles)

        return rolemap

classImplements(RelationshipLocalRoleManager, ILocalRolesPlugin)
InitializeClass(RelationshipLocalRoleManager)
