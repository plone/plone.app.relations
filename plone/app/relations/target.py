from plone.relations.interfaces import IComplexRelationshipContainer, _marker
from plone.relations.lazylist import lazyresolver
from plone.app.relations import interfaces
from zope.component import adapts, getUtility
from zope.interface import implements, Interface

class RelationshipTarget(object):
    """A basic implementation of IRelationshipSource based on the container
    from plone.relations, this package registers it as a named utility
    called ``relations``"""
    implements(interfaces.IRelationshipTarget)
    adapts(Interface)
    _name = 'relations'

    def __init__(self, target):
        self.target = target
        # always use the context of the target object for utility lookup
        self.util = getUtility(IComplexRelationshipContainer, name=self._name)
        self._resolver = self.util.relationIndex.resolveValueTokens

    def _target_resolver(self, value):
        return self._resolver((value,), 'target').next()

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

    @lazyresolver(resolver_name='_target_resolver')
    def getSources(self, relation=_marker, state=_marker, context=_marker,
                    rel_filter=None, maxDepth=1, minDepth=None,
                    transitivity=None):
        """See interface"""
        return self.util.findSourceTokens(self.target, relation, state,
                                     context, maxDepth, minDepth,
                                     filter=rel_filter,
                                     transitivity=transitivity)


class SymmetricRelation(object):
    implements(interfaces.ISymmetricRelation)
    adapts(Interface)
    _name = 'relations'

    def __init__(self, obj):
        self.obj = obj
        # always use the context of the object for utility lookup
        self.util = getUtility(IComplexRelationshipContainer, name=self._name)
        self._resolver = self.util.relationIndex.resolveValueTokens
        self._rel_resolver = self.util.relationIndex.resolveRelationshipTokens

    def _relation_resolver(self, entry):
        value, t_type = entry
        return self._resolver((value,), t_type).next()

    def _relationship_resolver(self, value):
        return self._rel_resolver((value,)).next()

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

    @lazyresolver(resolver_name='_relationship_resolver')
    def getRelationships(self, partner=None, relation=_marker, state=_marker,
                        context=_marker, rel_filter=None):
        rels = self._getRelationshipTokens(partner, relation, state, context,
                                           rel_filter)
        return rels

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

    @lazyresolver(resolver_name='_relation_resolver')
    def getRelations(self, relation=_marker, state=_marker,
                     context=_marker, rel_filter=None):
        rels = self._getRelationTokens(relation, state, context, rel_filter)
        return rels

    def isLinked(self, partner=None, relation=_marker, state=_marker,
                 context=_marker, rel_filter=None):
        as_source = self.util.isLinked(self.obj, partner, relation, state,
                                       context, filter=rel_filter)
        return as_source or self.util.isLinked(partner, self.obj, relation,
                                               state, context,
                                               filter=rel_filter)


