import unittest

from zope.testing import doctestunit
from zope.component import testing
from Testing import ZopeTestCase as ztc
from Products.PloneTestCase import PloneTestCase as ptc
from collective.testing.layer import ZCMLLayer
from OFS.SimpleItem import SimpleItem

from Products.Five import zcml

ptc.setupPloneSite()

class Demo(SimpleItem):
    def __init__(self, id):
        self.id = id
    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id)

class FuncLayer(ZCMLLayer):
    @classmethod
    def setUp(cls):
        from plone.app import relations
        zcml.load_config('configure.zcml', relations)

def contentSetUp(app):
    for i in range(30):
        id = 'ob%d' % i
        app._setObject(id, Demo(id))

def setUp(test):
    from collective.testing.utils import monkeyAppAsSite
    monkeyAppAsSite()
    from plone.app.relations.utils import add_relations, add_intids
    from zope.app.component.hooks import setSite, setHooks
    add_intids(test.app)
    add_relations(test.app)
    contentSetUp(test.app)
    setHooks()

class RelationsPortalTestCase(ptc.FunctionalTestCase):
    def afterSetUp(self):
        from collective.testing.utils import monkeyAppAsSite
        monkeyAppAsSite()
        from plone.app import relations
        zcml.load_config('configure.zcml', relations)
        from plone.app.relations.utils import add_relations, add_intids
        from zope.app.component.hooks import setSite, setHooks
        # Add the intids to zope and add the relations to the portal
        add_intids(self.app)
        add_relations(self.portal)
        contentSetUp(self.portal)
        setHooks()


def test_suite():
    readme = ztc.FunctionalDocFileSuite('README.txt',
                                        package='plone.app.relations',
                                        setUp=setUp)
    workflow = ztc.ZopeDocTestSuite('plone.app.relations.workflow',
                                    test_class=RelationsPortalTestCase)
    readme.layer = FuncLayer
    return unittest.TestSuite([readme, workflow])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
