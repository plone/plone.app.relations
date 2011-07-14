from itertools import izip, repeat

from AccessControl.class_init import InitializeClass
from Acquisition import aq_inner, aq_parent
from AccessControl import ClassSecurityInfo
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from zope.component import getAdapters, adapts
from zope.interface import implements

from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin

from plone.app.relations.interfaces import ILocalRoleProvider
from plone.app.relations.interfaces import IFactoryTempFolder

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

        >>> from zope.component import provideAdapter
        >>> from plone.app.relations.tests import SimpleLocalRoleProvider
        >>> from zope.app.testing import placelesssetup
        >>> placelesssetup.setUp()
        >>> provideAdapter(SimpleLocalRoleProvider, adapts=(Interface,))


    We need an object to adapt, we require nothing of this object,
    except it must be adaptable (e.g. have an interface)::

        >>> class DummyObject(object):
        ...     implements(Interface)
        >>> ob = DummyObject()

    And we need some users that we'll check the permissions of::

        >>> from plone.app.relations.tests import DummyUser
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


    Multiple Role Providers
    -----------------------

    It is a bit more interesting when we have more than one adapter
    registered.  We register it with a name so that it supplements,
    rather than conflict with or override the existing adapter::

        >>> class LessSimpleLocalRoleProvider(SimpleLocalRoleProvider):
        ...     userid = 'bogus_user2'
        ...     roles = ('Foo', 'Baz')
        ...     def getRoles(self, userid):
        ...         '''Grant bogus_user2 the 'Foo' and 'Baz' roles'''
        ...         if userid == self.userid:
        ...             return self.roles
        ...         return ()
        ...
        ...     def getAllRoles(self):
        ...         yield (self.userid, self.roles)

        >>> provideAdapter(LessSimpleLocalRoleProvider,
        ...                adapts=(Interface,), name='adapter2')

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


    Role Acquisition and Blocking
    -----------------------------

    This plugin will acquire role definitions from parent objects,
    unless explicitly blocked.  To test this, we need some objects
    which support acquisition::

        >>> from Acquisition import Implicit
        >>> class DummyImplicit(DummyObject, Implicit):
        ...     def stupid_method(self):
        ...         return 1
        >>> root = DummyImplicit()
        >>> next = DummyImplicit().__of__(root)
        >>> last = DummyImplicit().__of__(next)
        >>> other = DummyImplicit().__of__(root)

    So we now have /root/next/last and /root/other, we'll create and
    register special adapters for our next and other objects.

        >>> class ISpecial1(Interface):
        ...     pass
        >>> class ISpecial2(Interface):
        ...     pass
        >>> from zope.interface import directlyProvides
        >>> directlyProvides(next, ISpecial1)
        >>> directlyProvides(other, ISpecial2)
        >>> class Adapter1(LessSimpleLocalRoleProvider):
        ...     adapts(ISpecial1)
        ...     userid = 'bogus_user'
        ...     roles = ('Bar',)
        >>> class Adapter2(LessSimpleLocalRoleProvider):
        ...     adapts(ISpecial2)
        ...     userid = 'bogus_user3'
        ...     roles = ('Foobar',)
        >>> user3 = DummyUser('bogus_user3')

    We'll register these to override the existing unnamed adapter:

        >>> provideAdapter(Adapter1)
        >>> provideAdapter(Adapter2)

    Now we can show how acquisition of roles works, first we look at the
    'last' item, which should have roles provided by
    SimpleLocalRoleProvider, and LessSimpleLocalRoleProvider, as well
    as acquired from Adapter1 on 'next':

        >>> rm.getRolesInContext(user1, last)
        ['Foo', 'Bar']

        >>> rm.getRolesInContext(user2, last)
        ['Foo', 'Baz']

    If we look at the parent, we get the same results, because the
    SimpleLocalRoleProvider adapter also applies to the 'root'
    object. However, if we enable local role blocking on 'next' we
    won't see the roles from the 'root'::

        >>> rm.getRolesInContext(user1, next)
        ['Foo', 'Bar']
        >>> next.__ac_local_roles_block__ = True
        >>> rm.getRolesInContext(user1, next)
        ['Bar']

    The checkLocalRolesAllowed and getAllLocalRolesInContext methods
    take acquisition and blocking into account as well::

        >>> rm.checkLocalRolesAllowed(user1, last,  ['Bar'])
        1
        >>> rm.checkLocalRolesAllowed(user1, next,  ['Foo', 'Baz']) is None
        True
        >>> rm.getAllLocalRolesInContext(last)
        {'bogus_user2': set(['Foo', 'Baz']), 'bogus_user': set(['Foo', 'Bar'])}

    It's important to note, that roles are acquired only by
    containment.  Additional wrapping cannot change the security on an
    object.  For example if we were to wrap 'last' in the context of
    other, which provides a special role for 'user3', we should see no
    effect::

        >>> rm.getRolesInContext(user3, last)
        ['Foo']
        >>> rm.getRolesInContext(user3, other)
        ['Foobar', 'Foo']
        >>> rm.getRolesInContext(user3, last.__of__(other))
        ['Foo']

    It's also important that methods of objects yield the same local
    roles as the objects would

        >>> rm.getRolesInContext(user3, other.stupid_method)
        ['Foobar', 'Foo']

    Group Support
    -------------

    This plugin also handles roles granted to user groups, calling up
    the adapters to get roles for any groups the user might belong
    to::

        >>> user4 = DummyUser('bogus_user4', ('Group1', 'Group2'))
        >>> user4.getGroups()
        ('Group1', 'Group2')
        >>> rm.getRolesInContext(user4, last)
        ['Foo']
        >>> class Adapter3(LessSimpleLocalRoleProvider):
        ...     userid = 'Group2'
        ...     roles = ('Foobar',)

        >>> provideAdapter(Adapter3, adapts=(Interface,), name='group_adapter')
        >>> rm.getRolesInContext(user4, last)
        ['Foobar', 'Foo']


    Wrong User Folder
    -----------------

    Finally, to ensure full test coverage, we provide a user object
    which pretends to be wrapped in such a way that the user folder
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

        >>> placelesssetup.tearDown()


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
            new = aq_parent(obj)
            # if the obj is a method we get the class
            obj = getattr(obj, 'im_self', new)

    def _get_principal_ids(self, user):
        """Returns a list of the ids of all involved security
        principals: the user and all groups that they belong
        to. (Note: recursive groups are not yet supported"""
        principal_ids = list(user.getGroups())
        principal_ids.insert(0, user.getId())
        return principal_ids

    security.declarePrivate("getRolesInContext")
    def getRolesInContext(self, user, object):
        # we combine the permission of the user with those of the
        # gorups she belongs to
        principal_ids = self._get_principal_ids(user)
        roles = set()
        if user._check_context(object):
            for obj in self._parent_chain(object):
                for a in self._getAdapters(obj):
                    for pid in principal_ids:
                        roles.update(a.getRoles(pid))
        return list(roles)

    security.declarePrivate("checkLocalRolesAllowed")
    def checkLocalRolesAllowed(self, user, object, object_roles):
        """Checks if the user has one of the specified roles in the
        given context, short circuits when the first provider granting
        one of the roles is found."""
        check_roles = dict(izip(object_roles, repeat(True)))
        principal_ids = self._get_principal_ids(user)
        if not user._check_context(object):
            return 0
        for obj in self._parent_chain(object):
            for a in self._getAdapters(obj):
                for pid in principal_ids:
                    roles = a.getRoles(pid)
                    for role in check_roles:
                        if role in roles:
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

from Products.CMFCore.utils import getToolByName

class FactoryTempFolderProvider(object):
    """A simple local role provider which just gathers the roles from
    the desired context::

        >>> from zope.app.testing import placelesssetup
        >>> placelesssetup.setUp()
        >>> from zope.component import provideAdapter
        >>> from zope.interface import Interface, implements, directlyProvides
        >>> from plone.app.relations.local_role import RelationshipLocalRoleManager
        >>> rm = RelationshipLocalRoleManager('rm', 'A Role Manager')

        >>> from Acquisition import Implicit
        >>> class DummyObject(Implicit):
        ...     implements(Interface)
        >>> root = DummyObject()


    Let's construct a hierarchy similar to the way portal factory is used::

        root --> folder -------|
          |------------> PortalFactory --> TempFolder --> NewObject 

        >>> fold = DummyObject().__of__(root)
        >>> factory = DummyObject().__of__(root)
        >>> wrapped_factory = factory.__of__(fold)
        >>> temp = DummyObject().__of__(wrapped_factory)
        >>> newob = DummyObject().__of__(temp)

        >>> from plone.app.relations.tests import SimpleLocalRoleProvider
        >>> from plone.app.relations.tests import DummyUser
        >>> user1 = DummyUser('bogus_user1')


    To test our adapter we need an acl_users, and our user needs a
    getRolesInContext method::

        >>> class FakeUF(object):
        ...     def getUserById(self, userid, default=None):
        ...         if userid == user1.getId():
        ...             return user1
        ...         return None
        >>> root.acl_users = FakeUF()

        >>> def getRolesInContext(user, context):
        ...     return rm.getRolesInContext(user, context)
        >>> from new import instancemethod
        >>> user1.getRolesInContext = instancemethod(getRolesInContext, user1,
        ...                                          DummyUser)


    We add special interface to our Folder which allows us to provide
    some local roles, these roles will be inherited by any contained
    objects but not by our 'newob' because though the folder is its
    acquisition chain it is not contained by it::

        >>> class ISpecialInterface(Interface):
        ...     pass
        >>> directlyProvides(fold, ISpecialInterface)
        >>> provideAdapter(SimpleLocalRoleProvider, adapts=(ISpecialInterface,))
        >>> rm.getRolesInContext(user1, fold)
        ['Foo']
        >>> contained = DummyObject().__of__(fold)
        >>> rm.getRolesInContext(user1, contained)
        ['Foo']
        >>> rm.getRolesInContext(user1, newob)
        []

    Now we mark our TempFolder, and check that roles are now inherited
    from the intended location ('fold')::

        >>> directlyProvides(temp, IFactoryTempFolder)
        >>> provideAdapter(FactoryTempFolderProvider)
        >>> rm.getRolesInContext(user1, newob)
        ['Foo']

    The getAllRoles method always returns an empty dict, becuas it is
    only used for thing which are irrelevant for temporary objects::

        >>> rm.getAllLocalRolesInContext(newob)
        {}


        >>> placelesssetup.tearDown()

    """
    adapts(IFactoryTempFolder)
    implements(ILocalRoleProvider)

    def __init__(self, obj):
        self.folder = obj

    def getRoles(self, principal_id):
        uf = aq_inner(getToolByName(self.folder, 'acl_users'))
        user = aq_inner(uf.getUserById(principal_id, default=None))
        # use the folder we are creating in as role generating context
        source = aq_parent(aq_parent(self.folder))
        if user is not None:
            return user.getRolesInContext(source)
        else:
            return []

    def getAllRoles(self):
        # This should not be used in any meaningful way, so we'll make it cheap
        return {}
