from plone.relations.interfaces import IComplexRelationshipContainer, _marker
from plone.relations.relationships import Z2Relationship
from plone.relations.lazylist import lazyresolver
from plone.app.relations import interfaces as pa_interfaces
from zope.component import adapts, getUtility
from zope.interface import implements, alsoProvides, Interface

class RelationshipSource(object):
    """A basic implementation of IRelationshipSource based on the container
    from plone.relations, this package registers it as a named utility
    called ``relations``"""
    implements(pa_interfaces.IRelationshipSource)
    adapts(Interface)
    _name = 'relations'

    def __init__(self, source):
        self.source = source
        # always use the context of the source object for utility lookup
        self.util = getUtility(IComplexRelationshipContainer, name=self._name)
        self._resolver = self.util.relationIndex.resolveValueTokens

    def _source_resolver(self, value):
        return self._resolver((value,), 'source').next()

    def createRelationship(self, targets, relation=None, interfaces=(),
                           rel_factory=None, default_deletion=True):
        """See interface"""
        if rel_factory is None:
            rel_factory = Z2Relationship
        if not isinstance(targets, (list, tuple)):
            targets = (targets,)
        rel = rel_factory((self.source,), targets, relation=relation)
        alsoProvides(rel, *interfaces)
        if default_deletion:
            alsoProvides(rel, pa_interfaces.IDefaultDeletion)
        self.util.add(rel)
        # retrieve the object from the container
        return self.util[rel.__name__]

    def getRelationships(self, target=None, relation=_marker, state=_marker,
                         context=_marker, rel_filter=None):
        """See interface"""
        rels = self.util.findRelationships(self.source, target, relation,
                                           state, context, filter=rel_filter)
        for chain in rels:
            yield chain[0]

    def deleteRelationship(self, target=None, relation=_marker, state=_marker,
                           context=_marker, rel_filter=None, multiple=False,
                           remove_all_targets=False, ignore_missing=False):
        """See interface"""
        if target is None:
            # No target specified implies that all targets should be affected
            remove_all_targets = True
        rels = self.getRelationships(target, relation, state, context,
                                     rel_filter)
        # Resolve the relationships to check their length.
        rels = list(rels)
        if not rels and not ignore_missing:
            raise pa_interfaces.NoResultsError
        if len(rels) > 1 and not multiple:
            raise pa_interfaces.TooManyResultsError
        for rel in rels:
            if target is not None:
                # Sanity check
                assert(target in rel.targets)
            # If there are multiple sources delete ourself from the list of
            # sources if remove_all_targets is set. Otherwise, raise an error.
            if len(rel.sources) > 1:
                if remove_all_targets or len(rel.targets) == 1:
                    rel.sources.remove(self.source)
                    self.util.reindex(rel)
                else:
                    raise pa_interfaces.TooManyResultsError, "One of the "\
                          "relationships to be deleted has multiple sources "\
                          "and targets."
            # If there are multiple targets and remove_all_targets is
            # set, remove them all.  Otherwise, remove only the
            # specified target.
            elif len(rel.targets) > 1 and not remove_all_targets:
                rel.targets.remove(target)
                self.util.reindex(rel)
            else:
                self.util.remove(rel)


    def isLinked(self, target=None, relation=_marker, state=_marker,
                 context=_marker, rel_filter=None, maxDepth=1,
                 minDepth=None, transitivity=None):
        """See interface"""
        return self.util.isLinked(self.source, target, relation, state,
                                  context, maxDepth=maxDepth,
                                  minDepth=minDepth,
                                  filter=rel_filter, transitivity=transitivity)

    def getRelationshipChains(self, target=None, relation=_marker,
                               state=_marker, context=_marker, rel_filter=None,
                               maxDepth=1, minDepth=None, transitivity=None):
        """See interface"""
        return self.util.findRelationships(self.source, target, relation,
                                           state, context, maxDepth=maxDepth,
                                           minDepth=minDepth,
                                           filter=rel_filter,
                                           transitivity=transitivity)

    @lazyresolver(resolver_name='_source_resolver')
    def getTargets(self, relation=_marker, state=_marker, context=_marker,
                    rel_filter=None, maxDepth=1, minDepth=None,
                    transitivity=None):
        """See interface"""
        return self.util.findTargetTokens(self.source, relation, state,
                                          context, maxDepth=maxDepth,
                                          minDepth=minDepth,
                                          filter=rel_filter,
                                          transitivity=transitivity)

