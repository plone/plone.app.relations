# Helpers for installing the utility in Zope < 2.10
from zope.site.hooks import setSite, setHooks
from zope.component.interfaces import ComponentLookupError
from zope.component import getUtility
from five.intid.site import FiveIntIdsInstall, addUtility, add_intids
from five.intid.lsm import USE_LSM
from plone.relations import interfaces
from plone.relations.container import Z2RelationshipContainer
from zope.intid.interfaces import IIntIds

class RelationsInstall(FiveIntIdsInstall):
    """A view for adding the local utility"""
    def install(self):
        # Add the intids utiity if it doesn't exist
        portal = self.context
        add_intids(portal)
        add_relations(portal)

    @property
    def installed(self):
        installed = False
        try:
            util = getUtility(interfaces.IComplexRelationshipContainer,
                                name='relations')
            if util is not None:
                if USE_LSM:
                    sm = self.context.getSiteManager()
                    if 'relations' in sm.objectIds():
                        installed = True
                else:
                    installed = True
        except ComponentLookupError, e:
            pass
        return installed

def add_relations(context):
    addUtility(context, interfaces.IComplexRelationshipContainer,
               Z2RelationshipContainer, name='relations',
               findroot=False)
    # Set __name__ to the silly name given by the old component machinery:
    util = getUtility(interfaces.IComplexRelationshipContainer,
                      name='relations',
                      context=context)
    util.__name__ = interfaces.IComplexRelationshipContainer.getName() + \
                    '-relations'
    setSite(context)
    setHooks()
    intids = getUtility(IIntIds)

def installRelations(context):
    if context.readDataFile('install_relations.txt') is None:
        return
    portal = context.getSite()
    add_intids(portal)
    add_relations(portal)
    return "Added relations and intid utilities"
