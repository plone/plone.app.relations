# Helpers for installing the utility in Zope < 2.10
from zope.app.component.hooks import setSite, setHooks
from zope.component.interfaces import ComponentLookupError
from zope.component import getUtility
from five.intid.site import FiveIntIdsInstall, addUtility, add_intids
from plone.relations import interfaces
from plone.relations.container import Z2RelationshipContainer
from zope.app.intid.interfaces import IIntIds

class RelationsInstall(FiveIntIdsInstall):
    """A view for adding the local utility"""
    def install(self):
        # Add the intids utiity if it doesn't exist
        add_intids(self.context)
        add_relations(self.context)

    @property
    def installed(self):
        installed = False
        try:
            util = getUtility(interfaces.IComplexRelationshipContainer,
                                name='relations')
            if util is not None:
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
                      name='relations', context=context)
    util.__name__ = interfaces.IComplexRelationshipContainer.getName() + \
                    '-relations'
    setSite(context)
    setHooks()
    intids = getUtility(IIntIds)
