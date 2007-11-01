from zope.interface import Interface, Attribute, implements
from zope.annotation.interfaces import IAnnotatable
from zope.component.interfaces import ObjectEvent
from zope.component.interfaces import IObjectEvent
from plone.relations.interfaces import _marker, IStatefulRelationship

class TooManyResultsError(Exception):
    """Indicates that a query which was expected to generate a single result
    returned multiple."""

class NoResultsError(Exception):
    """Indicates that a query which was expected to generate results did not."""

class IRelationshipSource(Interface):
    """A content-centric API for a plone.relations based utility"""

    def createRelationship(targets, relation=None, interfaces=(),
                           rel_factory=None):
        """Creates a relationship between the current object (the
        source) and any number of target objects.  Detects if targets
        is a single object or a sequence.  The relation is an optional
        string to describe the type of relationship involved.

        The ``interfaces`` argument allows passing in a sequence of
        marker interfaces to be applied directly to the created
        relationship instance.  This is the preferred mechanism for
        applying custom behavior to a particular relationship.

        The rel_factory allows passing in an optional factory to be
        used for creating the relationship instances.  A sane default
        relationship class will be provided.  This mechanism is
        discouraged for all situations in which ``interfaces`` is a
        viable option, and should only be used when custom behavior
        is essential to have directly in the instance (e.g. required
        Zope 2 mixins like Role Manager when a relationship needs
        per instance security configuration).

        This method returns the relationship object in case further
        configuration is needed.  Such configuration should generally
        be done via adaptation."""

    def getRelationships(target=None, relation=_marker, state=_marker,
                           context=_marker, rel_filter=None):
        """Finds relationships to the object matching the specified
        parameters, targets, relation, state, context.  If no
        parameters are provided, then all relations to the adapted
        object will be found.  Optionally only returns relationships
        for which pass the rel_filter returns True."""

    def deleteRelationship(target=None, relation=_marker, state=_marker,
                           context=_marker, rel_filter=None, multiple=False,
                           remove_all_targets=False, ignore_missing=False):
        """Removes a relationship matching the specified parameters,
        ``target``, ``relation``, ``state``, ``context``.  Optionally
        only returns relationships which pass the ``rel_filter``
        (e.g. IMyInterface.providedBy).  If the query returns more
        than one relationship then ``TooManyResultsError`` will be
        raised unless the parameter ``multiple`` is set.  If the found
        relationship(s) have multiple targets, then the specified
        target is removed from the relationship unless
        ``remove_all_targets`` is set, in which case the matching
        relation will be removed entirely.  If no query parameters are
        specified and ``multiple`` is True, then all relationships to
        the object will be removed.  Not specifying a ``target`` is
        equivalent to turning on ``remove_all_targets``.

        Note: ``remove_all_targets`` is potentially quite dangerous.
        It is important that the method sanely handles the case where
        the retrieved relationship has multiple sources.  In this
        case, if there is only one target or if ``remove_all_targets``
        is True, the specified source should be removed from the
        relationship.  Otherwise, a ``TooManyResultsError`` may be
        raised, with a message indicating the problem.

        Will raise ``NoResultsError`` if no matching relationships are
        found unless ``ignore_missing`` is specified.
        """

    def isLinked(target=None, relation=_marker, state=_marker,
                 context=_marker, rel_filter=None, maxDepth=1,
                 minDepth=None, transitivity=None):
        """Returns True if a relationship exists matching the given
        parameters.  You can pass an optional maxDepth (None => no
        limit) and minDepth so that relationships are transitively
        determined.  A custom transitivity factory can be passed in,
        see the zc.relationship docs for more information."""

    def getRelationshipChains(target=None, relation=_marker,
                               state=_marker, context=_marker, rel_filter=None,
                               maxDepth=1, minDepth=None, transitivity=None):
        """Returns a sequence of tuples of relationships each
        representing a chain of relationships which match the given
        parameters and lead to the specified target.  Depth and means of
        transitivity can be specified as with isLinked."""

    def getTargets(relation=_marker, state=_marker, context=_marker,
                    rel_filter=None, maxDepth=1, minDepth=None,
                    transitivity=None):
        """Returns a list of all target objects whose relationships
        match the specified parameters.  Depth and means of
        transitivity can be specified as with isLinked."""


class IRelationshipTarget(Interface):
    """A content-centric api for looking at back references"""

    def getRelationships(source=None, relation=_marker, state=_marker,
                           context=_marker, rel_filter=None):
        """Finds relationships from the object matching the specified
        parameters.  See IRelationshipSource for more details."""

    def isLinked(source=None, relation=_marker, state=_marker,
                 context=_marker, rel_filter=None, maxDepth=1,
                 minDepth=None, transitivity=None):
        """Returns True if a relationship exists matching the given
        parameters.  See IRelationshipSource for more details."""

    def getRelationshipChains(source=None, relation=_marker,
                               state=_marker, context=_marker, rel_filter=None,
                               maxDepth=1, minDepth=None, transitivity=None):
        """Returns a sequence of tuples of relationships each
        representing a chain of relationships which match the given
        parameters and lead to the specified target.  Depth and means of
        transitivity can be specified as with isLinked."""

    def getSources(relation=_marker, state=_marker, context=_marker,
                    rel_filter=None, maxDepth=1, minDepth=None,
                    transitivity=None):
        """Returns a list of all related source objects whose
        relatioships match the specified parameters.  Depth and means
        of transitivity can be specified as with isLinked."""


class ISymmetricRelation(Interface):
    """Allows searching for relationships and related objects
    regardless of whether the current object is the source or the
    target of the relationship."""

    def getRelationships(partner=None, relation=_marker, state=_marker,
                         context=_marker, rel_filter=None):
        """Returns all relationships pointing to or from the current object,
        matching the given parameters.  You may optionally specify a
        partner which is another object involved in the relationship."""

    def getRelations(relation=_marker, state=_marker, context=_marker,
                     rel_filter=None):
        """Returns all relationships pointing to or from the current object,
        matching the given parameters.  You may optionally specify a
        partner which is another object involved in the relationship."""

    def isLinked(partner=None, relation=_marker, state=_marker,
                           context=_marker, rel_filter=None):
        """Returns true if the current object is linked
        (non-transitively) to the partner object as source or target
        (with restrictions provided by the other parameters).  If no
        partner is specified, returns true if there are any links to
        or from the object matching the given parameters."""


# Marker interfaces for determinig application of custom behavior

class IAnnotationsState(IAnnotatable):
    """Implies that the relationship state should be stored in an annotation"""

class IAnnotationsContext(IAnnotatable):
    """Implies that the relationship context should be stored in an
    annotation"""

class IDCWorkflowableRelationship(IAnnotatable):
    """A marker that indicates that state information on the object
    will be managed using DCWorkflow"""

class IDCWorkflowRelationship(IStatefulRelationship):
    """An interface describing a stateful relationship whose state is
    manipulated using a DCWorkflow (from CMF)"""

    workflow_id = Attribute('The name of a DC workflow to be used for this '
                               'object')
    state_var = Attribute('The name of the wf variable in which the workflow '
                          'state is stored.')

    def doAction(action, comment='', **kw):
        """Requests a workflow action on the object"""

    def isActionAllowed(action):
        """Returns True if the given action is currently allowed"""

    def getInfo(name, default=_marker):
        """Returns the named workflow variable after checking if the current
        user is allowed to access it"""

    def listActions():
        """List available user triggered transitions"""

class IRelationSourceDeleted(IObjectEvent):
    """An event which indicates that the source of a relationship has
    been deleted"""
    source = Attribute("The object that was deleted")

class IRelationTargetDeleted(IObjectEvent):
    """An event which indicates that the target of a relationship has
    been deleted"""
    target = Attribute("The object that was deleted")

class RelationSourceDeleted(ObjectEvent):
    implements(IRelationSourceDeleted)

    def __init__(self, object, source):
        ObjectEvent.__init__(self, object)
        self.source = source

class RelationTargetDeleted(ObjectEvent):
    implements(IRelationTargetDeleted)

    def __init__(self, object, target):
        ObjectEvent.__init__(self, object)
        self.target = target

class IDefaultDeletion(Interface):
    """A marker interface indicating that the relationship should be
    deleted/updated when it's sources or targets are deleted"""

class IHoldingRelation(Interface):
    """A marker interface to demonstrate the use of a marker interface
    to change behavior on target deletion"""

class HoldingRelationError(Exception):
    """An exception raised when the target of a HoldingRelation is deleted"""
    def __init__(self, obj, relation):
        self.args =  "%s cannot be deleted, it is the target of a "\
                    "relationship to %s"%(obj, tuple(relation.sources))

class IRetainOnCopy(Interface):
    """A marker interface to indicate that a relationship should be copied
    when it's source object is copied (with the sources changed on the copy)."""

class ICopyPendingAdd(Interface):
    """An interface indicating that an object is a copy that hasn't been added
    yet.  This is used to filter for add events that result from a copy.
    The interface promises an attribute pointing to the original object"""

    __orig_object__ = Attribute("The original object before copy")

class ILocalRoleProvider(Interface):
    """An interface which allows querying the local roles on an object"""

    def getRoles(principal_id):
        """Returns an iterable of roles granted to the specified user object"""

    def getAllRoles():
        """Returns an iterable consisting of tuples of the form:
                    (principal_id, sequence_of_roles)
        """
class IFactoryTempFolder(Interface):
    """A marker indicating the portal_factory temp folder"""
