from Acquisition import aq_base
from zope.interface import alsoProvides, directlyProvides, directlyProvidedBy
from zope.event import notify
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
from zope.location.pickling import locationCopy
from plone.relations.interfaces import IComplexRelationshipContainer
from plone.app.relations.interfaces import IRetainOnCopy
from plone.app.relations.interfaces import ICopyPendingAdd
from plone.app.relations.interfaces import IRelationshipSource
from plone.app.relations.interfaces import IRelationshipTarget
from plone.app.relations.interfaces import RelationSourceDeleted
from plone.app.relations.interfaces import RelationTargetDeleted
from plone.app.relations.interfaces import HoldingRelationError
from zc.relationship.interfaces import IBidirectionalRelationshipIndex


def handleSourceTargetDelete(ob, event):
    """Fires relevant events for all references related to the object"""
    try:
        source = IRelationshipSource(ob)
        target = IRelationshipTarget(ob)
    except (ComponentLookupError, TypeError):
        return
    # we tuplify the generator to prevent errors if we need to delete elements
    rels = tuple(source.getRelationships())
    for rel in rels:
        notify(RelationSourceDeleted(rel, ob))
    rels = tuple(target.getRelationships())
    for rel in rels:
        notify(RelationTargetDeleted(rel, ob))

def deleteReferenceOnSourceDelete(rel, event):
    """deleted references related to the object"""
    if IBidirectionalRelationshipIndex.providedBy(rel.__parent__):
        index = rel.__parent__
    else:
        index = None
    if len(rel.sources) > 1:
        rel.sources.remove(event.source)
        if index is not None:
            index.reindex(rel)
    elif event.source in rel.sources and index is not None:
        index.remove(rel)

def deleteReferenceOnTargetDelete(rel, event):
    """deleted references related to the object"""
    if IBidirectionalRelationshipIndex.providedBy(rel.__parent__):
        index = rel.__parent__
    else:
        index = None
    if len(rel.targets) > 1:
        rel.targets.remove(event.target)
        if index is not None:
            index.reindex(rel)
    elif event.target in rel.targets and index is not None:
        index.remove(rel)

def raiseHoldingExceptionOnTargetDelete(rel, event):
    """raises an exception when the target of an existing IHoldingRelation
    is deleted"""
    raise HoldingRelationError(event.target, rel)

def markCopyOnCopy(obj, event):
    obj.__orig_object__ = event.original
    alsoProvides(obj, ICopyPendingAdd)

def copyRelationsOnSourceCopy(obj, event):
    """Copies all source relaitonships marked with IRetainOnCopy
    when the source object is copied"""
    orig_obj = obj.__orig_object__.aq_inner
    source = IRelationshipSource(orig_obj)
    cur_ifaces = directlyProvidedBy(obj)
    directlyProvides(obj, *[i for i in cur_ifaces if i is not ICopyPendingAdd])
    delattr(obj, '__orig_object__')
    copy_filter = IRetainOnCopy.providedBy
    # this is not efficient to source objects with a huge number of
    # relations
    rels = source.getRelationships(rel_filter=copy_filter)
    container = getUtility(IComplexRelationshipContainer, name='relations')
    unwrapped_obj = aq_base(obj)
    for rel in rels:
        # copy the relationship
        rel_copy = locationCopy(aq_base(rel))
        # The references on the copy becames copies themselves we need
        # to make sure all such references point to the originals:
        rel_copy.__dict__ = rel.__dict__
        # We should also remove existing ILocation pointers
        rel_copy.__parent__ = rel_copy.__name__ = None
        # Now we add the relationship (with wrong sources for now) to
        # give it a context.
        container.add(rel_copy)
        # replace the old sources with just the copy
        rel_copy.sources = (obj,)

