import unittest
from zope.app.testing import placelesssetup
from zope.interface import implements
from zope.testing.doctest import DocTestSuite
from Testing import ZopeTestCase as ztc
from Products.PloneTestCase import PloneTestCase as ptc
from OFS.SimpleItem import SimpleItem

from five.intid.lsm import USE_LSM
from five.intid.site import add_intids
from plone.app.relations.utils import add_relations
from plone.app.relations.interfaces import ILocalRoleProvider

from Products.Five import zcml


class Demo(SimpleItem):
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id)

def contentSetUp(app):
    for i in range(30):
        oid = 'ob%d' % i
        app._setObject(oid, Demo(oid))


class SimpleLocalRoleProvider(object):
    implements(ILocalRoleProvider)
    def __init__(self, context):
        self.context = context

    def getRoles(self, user):
        """Grant everyone the 'Foo' role"""
        return ('Foo',)

    def getAllRoles(self):
        """In the real world we would enumerate all users and
        grant the 'Foo' role to each, but we won't"""
        yield ('bogus_user', ('Foo',))


class DummyUser(object):
    def __init__(self, uid, group_ids=()):
        self.id = uid
        self._groups = group_ids

    def getId(self):
        return self.id

    def _check_context(self, obj):
        return True

    def getGroups(self):
        return self._groups


def base_setup(app):
    """Setup without basic CA stuff because PTC already provides this"""
    from plone.app import relations
    try:
        zcml.load_config('configure.zcml', relations)
    except:
        # XXX: When ptc has setup plone, then the zcml product
        # registration causes errors when run twice :-(
        pass
    if not USE_LSM:
        # monkey in our hooks
        from Products.Five.site.metaconfigure import classSiteHook
        from Products.Five.site.localsite import FiveSite
        from zope.interface import classImplements
        from zope.site.interfaces import IPossibleSite
        klass = app.__class__
        classSiteHook(klass, FiveSite)
        classImplements(klass, IPossibleSite)
    add_intids(app)
    add_relations(app)
    contentSetUp(app)

def setUp(app):
    """A setup that includes the basic CA setup"""
    placelesssetup.setUp()
    import Products.Five
    zcml.load_config('meta.zcml', Products.Five)
    zcml.load_config('permissions.zcml', Products.Five)
    zcml.load_config('configure.zcml', Products.Five)
    base_setup(app)


def tearDown():
    placelesssetup.tearDown()

# XXX: This messes things up, where else could we call it, it's only needed
# for workflow
ptc.setupPloneSite()

def test_suite():
    from plone.app.relations import local_role
    pas = DocTestSuite(local_role, setUp=placelesssetup.setUp(),
                       tearDown=placelesssetup.tearDown())

    readme = ztc.FunctionalDocFileSuite('README.txt',
                                        package='plone.app.relations')

    workflow = ztc.ZopeDocTestSuite('plone.app.relations.workflow',
                                    test_class=ptc.FunctionalTestCase,)

    userrelations = ztc.ZopeDocFileSuite('userrelations.txt',
                                         package='plone.app.relations', 
                                         test_class=ptc.FunctionalTestCase,)


    return unittest.TestSuite([workflow, readme, pas, userrelations])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
