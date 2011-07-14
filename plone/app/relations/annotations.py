from zope.interface import implements
from zope.component import adapts
from plone.relations import interfaces as pr_interfaces
from plone.app.relations import interfaces
from zope.annotation.interfaces import IAnnotations
from persistent.mapping import PersistentMapping
from zc.relationship.interfaces import IBidirectionalRelationshipIndex

ANNOTATIONS_KEY = 'plone.app.relationship.relation_annotations'

class StateAnnotationsAdapter(object):
    implements(pr_interfaces.IStatefulRelationship)
    adapts(interfaces.IAnnotationsState)
    def __init__(self, rel):
        self.rel = rel
        self.annotations = IAnnotations(rel).setdefault(ANNOTATIONS_KEY,
                                                        PersistentMapping())
    @apply
    def state():
        def get(self):
            return self.annotations.get('state', None)
        def set(self, value):
            self.annotations['state'] = value
            if IBidirectionalRelationshipIndex.providedBy(self.rel.__parent__):
                self.rel.__parent__.reindex(self.rel)
        return property(get, set)

class ContextAnnotationsAdapter(object):
    implements(pr_interfaces.IContextAwareRelationship)
    adapts(interfaces.IAnnotationsContext)
    def __init__(self, rel):
        self.rel = rel
        self.annotations = IAnnotations(rel).setdefault(ANNOTATIONS_KEY,
                                                        PersistentMapping())
    def getContext(self):
        return self.annotations.get('context', None)

    def setContext(self, value):
        self.annotations['context'] = value
        if IBidirectionalRelationshipIndex.providedBy(self.rel.__parent__):
            self.rel.__parent__.reindex(self.rel)
