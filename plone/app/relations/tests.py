import unittest
from zope.app.testing import placelesssetup
from zope.testing.doctest import DocTestSuite
from Testing import ZopeTestCase as ztc
from Products.PloneTestCase import PloneTestCase as ptc
from collective.testing.layer import ZCMLLayer
from OFS.SimpleItem import SimpleItem

from Products.Five import zcml


class Demo(SimpleItem):
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id)

class FuncLayer(ZCMLLayer):
    @classmethod
    def setUp(cls):
        from plone.app import relations
        try:
            zcml.load_config('configure.zcml', relations)
        except:
            # XXX: When ptc has setup plone, then the zcml product
            # registration causes errors when run twice :-(
            pass

def contentSetUp(app):
    for i in range(30):
        oid = 'ob%d' % i
        app._setObject(oid, Demo(oid))

def setUp(test):
    from collective.testing.utils import monkeyAppAsSite
    monkeyAppAsSite()
    from plone.app.relations.utils import add_relations, add_intids
    from zope.app.component.hooks import setSite, setHooks
    add_intids(test.app)
    add_relations(test.app)
    setSite(test.app)
    setHooks()
    contentSetUp(test.app)

class RelationsPortalTestCase(ptc.FunctionalTestCase):

    def afterSetUp(self):
        from plone.app import relations
        zcml.load_config('configure.zcml', relations)
        from Products.CMFPlone.Portal import PloneSite
        from plone.app.relations.utils import add_relations, add_intids
        from Products.Five.site.metaconfigure import classSiteHook
        from Products.Five.site.localsite import FiveSite
        from zope.interface import classImplements
        from zope.app.component.interfaces import IPossibleSite

        classSiteHook(PloneSite, FiveSite)
        classImplements(PloneSite, IPossibleSite)
        from zope.app.component.hooks import setSite, setHooks
        # Add the intids and the relations to the portal
        add_intids(self.portal)
        add_relations(self.portal)
        contentSetUp(self.portal)
        setHooks()
        setSite(self.portal)

# XXX: This messes things up, where else could we call it, it's only needed
# for workflow
ptc.setupPloneSite()

def test_suite():
    readme = ztc.FunctionalDocFileSuite('README.txt',
                                        package='plone.app.relations',
                                        setUp=setUp)
    readme.layer = FuncLayer

    workflow = ztc.ZopeDocTestSuite('plone.app.relations.workflow',
                                    test_class=RelationsPortalTestCase,)

    from plone.app.relations import local_role
    pas = DocTestSuite(local_role, setUp=placelesssetup.setUp(),
                       tearDown=placelesssetup.tearDown())

    return unittest.TestSuite([readme, workflow, pas])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
