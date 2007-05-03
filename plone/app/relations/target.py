from plone.relations.interfaces import IComplexRelationshipContainer, _marker
from plone.app.relations import interfaces
from zope.component import adapts, getUtility
from zope.interface import implements
from persistent import IPersistent

class RelationshipTarget(object):
    """A basic implementation of IRelationshipSource based on the container
    from plone.relations, this package registers it as a named utility
    called ``relations``"""
    implements(interfaces.IRelationshipTarget)
    adapts(IPersistent)

    def __init__(self, target):
        self.target = target
        # always use the context of the target object for utility lookup
        self.util = getUtility(IComplexRelationshipContainer, name='relations',
                               context=target)

    def getRelationships(self, source=None, relation=_marker, state=_marker,
                         context=_marker, rel_filter=None):
        """See interface"""
        rels = self.util.findRelationships(source, self.target, relation,
                                           state, context, filter=rel_filter)
        for chain in rels:
            yield chain[0]

    def isLinked(self, source=None, relation=_marker, state=_marker,
                 context=_marker, rel_filter=None, maxDepth=1,
                 minDepth=None, transitivity=None):
        """See interface"""
        return self.util.isLinked(source, self.target, relation, state,
                                  context, maxDepth, minDepth,
                                  filter=rel_filter, transitivity=transitivity)

    def getRelationshipChains(self, source=None, relation=_marker,
                               state=_marker, context=_marker, rel_filter=None,
                               maxDepth=1, minDepth=None, transitivity=None):
        """See interface"""
        return self.util.findRelationships(source, self.target, relation,
                                           state, context, maxDepth, minDepth,
                                           filter=rel_filter,
                                           transitivity=transitivity)

    def getSources(self, relation=_marker, state=_marker, context=_marker,
                    rel_filter=None, maxDepth=1, minDepth=None,
                    transitivity=None):
        """See interface"""
        return self.util.findSources(self.target, relation, state,
                                     context, maxDepth, minDepth,
                                     filter=rel_filter,
                                     transitivity=transitivity)

    def countSources(self, relation=_marker,
                     state=_marker, context=_marker, rel_filter=None,
                     maxDepth=1, minDepth=None, transitivity=None):
        """See interface"""
        return len(list(self.util.findSourceTokens(self.target, relation,
                                             state, context, maxDepth,
                                             minDepth, filter=rel_filter,
                                             transitivity=transitivity)))


class SymmetricRelation(object):
    implements(interfaces.ISymmetricRelation)
    adapts(IPersistent)

    def __init__(self, obj):
        self.obj = obj
        # always use the context of the object for utility lookup
        self.util = getUtility(IComplexRelationshipContainer, name='relations',
                               context=obj)

    def _getRelationshipTokens(self, partner=None, relation=_marker,
                               state=_marker, context=_marker, rel_filter=None):
        """See interface"""
        rels1 = self.util.findRelationshipTokens(self.obj, partner, relation,
                                                 state, context,
                                                 filter=rel_filter)
        rels2 = self.util.findRelationshipTokens(partner, self.obj, relation,
                                                 state, context,
                                                 filter=rel_filter)
        seen = []
        for chain in rels1:
            token = chain[0]
            seen.append(token)
            yield token
        for chain in rels2:
            token = chain[0]
            if token not in seen:
                yield token

    def getRelationships(self, partner=None, relation=_marker, state=_marker,
                        context=_marker, rel_filter=None):
        rels = self._getRelationshipTokens(partner, relation, state, context,
                                           rel_filter)
        for rel in rels:
            vals = self.util.relationIndex.resolveRelationshipTokens((rel,))
            yield vals.next()

    def countRelationships(self, partner=None, relation=_marker, state=_marker,
                           context=_marker, rel_filter=None):
        """see interface"""
        rels = self._getRelationshipTokens(partner, relation, state, context,
                                           rel_filter)
        return len(list(rels))

    def _getRelationTokens(self, relation=_marker, state=_marker,
                           context=_marker, rel_filter=None):
        """See interface"""
        targets = self.util.findTargetTokens(self.obj, relation, state, context,
                                             filter=rel_filter)
        sources = self.util.findSourceTokens(self.obj, relation, state, context,
                                             filter=rel_filter)
        seen = []
        for t in targets:
            seen.append(t)
            yield t, 'target'
        for t in sources:
            if t not in seen:
                yield t, 'source'

    def getRelations(self, relation=_marker, state=_marker,
                     context=_marker, rel_filter=None):
        rels = self._getRelationTokens(relation, state, context, rel_filter)
        for rel, rtype in rels:
            vals = self.util.relationIndex.resolveValueTokens((rel,), rtype)
            yield vals.next()

    def countRelations(self, relation=_marker, state=_marker,
                     context=_marker, rel_filter=None):
        rels = self._getRelationTokens(relation, state, context, rel_filter)
        return len(list(rels))

    def isLinked(self, partner=None, relation=_marker, state=_marker,
                 context=_marker, rel_filter=None):
        as_source = self.util.isLinked(self.obj, partner, relation, state,
                                       context, filter=rel_filter)
        return as_source or self.util.isLinked(partner, self.obj, relation,
                                               state, context,
                                               filter=rel_filter)


