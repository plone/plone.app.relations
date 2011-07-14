===================
plone.app.relations
===================

This package utilizes plone.relations and zc.relationship to build a
hopefully content-centric API for creating and introspecting rich
relationships between content types.  This product allows you to
install a local utility into your site for managing relationships, and
provides a set of adapters to allow persistent objects in the ZODB to
build relationships with each other.

You may install the utility either with the included GenericSetup
profile (Zope 2.10 + Plone 3.0/CMF 2.1 only) or by using the included
``@@install-relations.html`` view on any folder.  The convenience API
for managing and querying references is IReferenceSource, which we
will explore below.  Keep in mind that the utility may be used
directly and offers more flexibility at the expense of convenience.
See the plone.relations documentation for details.


    >>> from plone.app.relations import tests
    >>> tests.setUp(app)

Reference Sources
==================

Getting Started
----------------

Our test setup has already installed the utility into a Zope instance
and some put in some ``Demo`` objects named ob0-ob29.  Let's adapt one
of these objects to IReferenceSource and use that interface to add a
simple reference to another object.  We'll also verify that the
adpated object conforms to our interface, and that the generated
relationship conforms to the IRelationship interface::

    >>> from plone.app.relations import interfaces
    >>> from plone.relations import interfaces as pr_interfaces
    >>> from zope.interface.verify import verifyObject
    >>> ob1 = app['ob1']
    >>> ob2 = app['ob2']
    >>> ob3 = app['ob3']
    >>> ob4 = app['ob4']
    >>> ob5 = app['ob5']
    >>> source = interfaces.IRelationshipSource(ob1)
    >>> verifyObject(interfaces.IRelationshipSource, source)
    True
    >>> rel1 = source.createRelationship(ob2)
    >>> verifyObject(pr_interfaces.IRelationship, rel1)
    True

Now we can query our reference source for the relationships it's involved in,
and also for the objects it's related to (the ``targets``)::

    >>> list(source.getRelationships())
    [<Relationship None from (<Demo ob1>,) to (<Demo ob2>,)>]
    >>> list(source.getRelationships(target=ob2))
    [<Relationship None from (<Demo ob1>,) to (<Demo ob2>,)>]
    >>> list(source.getRelationships(target=ob3))
    []

    >>> list(source.getTargets())
    [<Demo ob2>]
    >>> list(source.getTargets(relation=u'wrong'))
    []

Further we can check to see if our object is linked directly to any
object, or if it has any links at all::

    >>> source.isLinked(target=ob2)
    True
    >>> source.isLinked(target=ob3)
    False
    >>> source.isLinked()
    True
    >>> len(source.getTargets())
    1

In addition to adding and querying relationships, we can delete relationships::

    >>> source.deleteRelationship(target=ob2)
    >>> list(source.getRelationships())
    []


Relation Types
--------------

A relationship may optionally specify a string (or preferably a
``zope.i18n.Message``) ``relation`` which corresponds to the
relationship type::

    >>> rel2 = source.createRelationship((ob2, ob4), relation=u'relation 1')
    >>> list(source.getTargets())
    [<Demo ob2>, <Demo ob4>]
    >>> list(source.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob4>)>]

Any queries may restrict their results to a specific relationship type::

    >>> source2 = interfaces.IRelationshipSource(ob2)
    >>> rel3 = source2.createRelationship(ob3, u'relation 2')
    >>> list(source2.getTargets())
    [<Demo ob3>]
    >>> rel4 = source2.createRelationship(ob5, u'relation 1')
    >>> list(source2.getTargets())
    [<Demo ob3>, <Demo ob5>]
    >>> list(source2.getTargets(relation=u'relation 1'))
    [<Demo ob5>]
    >>> list(source2.getTargets(relation=u'relation 2'))
    [<Demo ob3>]
    >>> list(source2.getTargets())
    [<Demo ob3>, <Demo ob5>]

This ``relation`` is actually set and retireved via adaptation of the
relatinship to the ``plone.relations.interfaces.IComplexRelationship``
interface, which we will see in use later.


Relationship Chains
-------------------

We now have the following simple relationship graph where the numbers
in () are out relation types::

        ob1 [source]
        /\
    (1)/  \(1)
      /    \
     ob2   ob4
     /\
 (2)/  \(1)
   /    \
  ob3   ob5

A few of our query methods allow us to transitively search for
relationships along this graph.  For example, though ob1 is not
directly linked to ob5, it is linked indirectly via ob2.  We can
specify a maximum depth to search this tree when looking at
``isLinked``, ``getTargets``, and ``getRelationshipChains``.  We can
also filter these searches based on the relationship type so that only
paths that match a specific relationship type are found::

    >>> source.isLinked(ob5)
    False
    >>> source.isLinked(ob5, maxDepth=2)
    True
    >>> source.isLinked(ob5, relation=u'relation 1', maxDepth=2)
    True
    >>> source.isLinked(ob3, maxDepth=2)
    True
    >>> source.isLinked(ob3, relation=u'relation 1', maxDepth=2)
    False
    >>> source.isLinked(ob3, relation=u'relation 2', maxDepth=2)
    False

As you can see ob1 is linked to both ob3 and ob5, but it is linked to ob5 with the specific relationship type u'relation 1'.   We can also see how many objects our source is linked to using a ``maxDepth`` to search the tree:

    >>> len(source.getTargets())
    2
    >>> len(source.getTargets(maxDepth=2))
    4
    >>> len(source.getTargets(relation=u'relation 1'))
    2
    >>> len(source.getTargets(relation=u'relation 1', maxDepth=2))
    3

You can also examine the list of chains connecting your object to a
specific object (or to any objects). The first query below shows the
entire tree, since our source is at its root, the second shows only
those matching u'relation 1', and the third introduces the minDepth
parameter in order to show only relationship chains longer than two
relationships long::

    >>> chains = source.getRelationshipChains(maxDepth=None)
    >>> sorted([repr(r) for r in chains])
    ["(<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob4>)>, <Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>)", "(<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob4>)>, <Relationship u'relation 2' from (<Demo ob2>,) to (<Demo ob3>,)>)", "(<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob4>)>,)"]

    >>> chains = source.getRelationshipChains(relation=u'relation 1',
    ...                                       maxDepth=None)
    >>> sorted([repr(r) for r in chains])
    ["(<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob4>)>, <Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>)", "(<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob4>)>,)"]

    >>> chains = source.getRelationshipChains(relation=u'relation 1',
    ...                                       maxDepth=None, minDepth=2)
    >>> sorted([repr(r) for r in chains])
    ["(<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob4>)>, <Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>)"]



Deleting Relationships and Relationship Targets
-----------------------------------------------

Deleting existing relationships introduces a number of potential
complications.  This section indicates how relationship deletion works
under a number of circumstances.

First we create a relationship that points to multiple targets, one of
which we were already pointing to with another relationship type.  So
that ob1 points to both ob4 and ob5 with both a u'relation1' and a
u'relation 2'.  If we ask to delete the relationship to ob4, we get an
error, because there are two possible relationships that could be
deleted.  If instead we specify more parameters (in this case the
relation) we can delete the one that we want::

    >>> rel5 = source.createRelationship((ob4, ob5), relation=u'relation 2')
    >>> rel6 = source.createRelationship(ob5, relation=u'relation 1')
    >>> source.deleteRelationship(ob4)
    Traceback (most recent call last):
    ...
    TooManyResultsError
    >>> source.deleteRelationship(ob4, relation=u'relation 1')
    >>> list(source.getRelationships(ob2))
    [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]
    >>> list(source.getTargets())
    [<Demo ob2>, <Demo ob4>, <Demo ob5>]

Note that ``ob5`` only appears in the result once, despite the fact
that there are two relatiohships pointing to it.  We can choose to
delete all relationships matching a query by passing the multiple
parameter::

    >>> source.deleteRelationship(ob5)
    Traceback (most recent call last):
    ...
    TooManyResultsError
    >>> source.deleteRelationship(ob5, multiple=True)
    >>> list(source.getTargets())
    [<Demo ob2>, <Demo ob4>]

Note that because one of the relationships we deleted had both ob4 and
ob5 as targets, the target ob5 was removed, but the existing
relationship to ob4 remained intact.  There are cases where you might
want to delete an entire relationship with multiple targets.  The
``remove_all_targets`` parameter allows this.

First we'll modify an existing relationship to add a second target and
change the ``relation``.  Note we need to adapt to
IComplexRelationship in order to change the ``relation`` and the
object it is automatically reindexed when ``target``, ``source``, or
``relation`` change (when using the default relationship factory and
adapters), we verify this by looking at the u'relation 1'
relationships for our source before and after modifying the existing
relationship to change its type::

    >>> list(source.getTargets(relation=u'relation 1'))
    [<Demo ob2>]
    >>> rel = list(source.getRelationships(ob4))[0]
    >>> rel.targets = (ob4, ob5)
    >>> pr_interfaces.IComplexRelationship(rel).relation = u'relation 1'
    >>> list(source.getTargets(relation=u'relation 1'))
    [<Demo ob2>, <Demo ob4>, <Demo ob5>]
    >>> pr_interfaces.IComplexRelationship(rel).relation = u'relation 2'
    >>> list(source.getTargets(relation=u'relation 1'))
    [<Demo ob2>]

When you want to remove an entire relationship, even if it has
multiple targets, you can use ``remove_all_targets``.  In this case
the relationship pointing to both ``ob4`` and ``ob5`` will be removed
entirely::

    >>> list(source.getTargets())
    [<Demo ob2>, <Demo ob4>, <Demo ob5>]
    >>> source.deleteRelationship(ob5, remove_all_targets=True)
    >>> list(source.getTargets())
    [<Demo ob2>]
    >>> list(source.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]

If we don't specify a target object, all relationships are deleted:

    >>> source5 = interfaces.IRelationshipSource(ob5)
    >>> rel = source5.createRelationship(ob1)
    >>> rel = source5.createRelationship(ob2)
    >>> list(source5.getTargets())
    [<Demo ob1>, <Demo ob2>]
    >>> source5.deleteRelationship(multiple=True)
    >>> list(source5.getTargets())
    []

Multiple Sources
----------------

Though the ``ISourceRelationship`` API doesn't provide for creation of
relationships with multiple sources, it's nonetheless possible to
create them via other means.  For multi-source relationships, the
expected behavior when using ``deleteRelationship`` is a little more
complex: if no target is specified in the query or if the relationship
to be deleted has only one target , or ``remove_all_targets`` is
specified, then the source object will be removed from the
relationship, otherwise a ``TooManyResultsError`` error will be
raised::

    >>> rel = list(source.getRelationships(ob2))[0]
    >>> rel.sources = (ob1, ob4)
    >>> rel.targets = (ob2, ob3)
    >>> source4 = interfaces.IRelationshipSource(ob4)
    >>> list(source4.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>, <Demo ob4>) to (<Demo ob2>, <Demo ob3>)>]
    >>> list(source.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>, <Demo ob4>) to (<Demo ob2>, <Demo ob3>)>]
    >>> source4.deleteRelationship(ob2)
    Traceback (most recent call last):
    ...
    TooManyResultsError: One of the relationships to be deleted has multiple sources and targets.
    >>> source4.deleteRelationship(ob2, remove_all_targets=True)
    >>> list(source4.getRelationships())
    []
    >>> list(source.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob3>)>]

The reason for raising a ``TooManyResultsError`` is that it may not be
acceptable to break a single relationship into multiple relationships
where a given target has been removed for one of the sources.  Such a
situation probably needs to be handled manually.

If no relationships are found to delete, then a NoResultsError will be raised
unless ignore_missing is specified::

    >>> source4.deleteRelationship(ob5)
    Traceback (most recent call last):
    ...
    NoResultsError
    >>> source4.deleteRelationship(ob5, ignore_missing=True)


Relationship Targets
====================

Another API provided in this package is the IRelationshipTarget API, which
allows us to make queries on an object to find information about relationships
pointing to the object.  Right now we'll look at ob5::

    >>> target = interfaces.IRelationshipTarget(ob5)
    >>> verifyObject(interfaces.IRelationshipTarget, target)
    True
    >>> list(target.getSources())
    [<Demo ob2>]
    >>> list(target.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>]

We can filter based on relation as well:

    >>> list(target.getSources(relation=u'relation 1'))
    [<Demo ob2>]
    >>> list(target.getSources(relation=u'relation 2'))
    []

Or make queries using ``maxDepth`` and ``minDepth``:

    >>> list(target.getSources(relation=u'relation 1', maxDepth=2))
    [<Demo ob2>, <Demo ob1>]
    >>> list(target.getSources(relation=u'relation 1', maxDepth=2, minDepth=2))
    [<Demo ob1>]
    >>> target.isLinked(ob1)
    False
    >>> target.isLinked(ob1, maxDepth=2)
    True
    >>> target.isLinked(ob1)
    False
    >>> len(target.getSources(maxDepth=2))
    2
    >>> chains = target.getRelationshipChains(maxDepth=None)
    >>> sorted([repr(r) for r in chains])
    ["(<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob3>)>, <Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>)", "(<Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>,)"]


All Relationships
=================

There's another API provided by ISymmetricRelation which is intended
to be applied for relationships which are symmetric in nature
(sibling, collaborator).  It doesn't change the fact that all relationships
are implemented using sources and targets, but it allows one to
efficiently query for relationships to and from a particular object.  This
API does not support any transitivity, because there's no simple way to
follow paths in both directions without creating cycles at every point.

First we apply and verify our adapter::

    >>> relation = interfaces.ISymmetricRelation(ob2)
    >>> target2 = interfaces.IRelationshipTarget(ob2)
    >>> verifyObject(interfaces.IRelationshipTarget, target)
    True

Now we can look at ob2 as a source, target, or symmetrically::

    >>> list(source2.getTargets())
    [<Demo ob3>, <Demo ob5>]
    >>> list(target2.getSources())
    [<Demo ob1>]
    >>> list(relation.getRelations())
    [<Demo ob3>, <Demo ob5>, <Demo ob1>]
    >>> len(relation.getRelations())
    3
    >>> len(relation.getRelations(relation=u'relation 1'))
    2
    >>> relation.isLinked(ob3)
    True
    >>> relation.isLinked(relation=u'relation 1')
    True
    >>> relation.isLinked(ob3, relation=u'relation 1')
    False
    >>> len(relation.getRelationships())
    3
    >>> sorted((repr(r) for r in relation.getRelationships()))
    ["<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob3>)>", "<Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>", "<Relationship u'relation 2' from (<Demo ob2>,) to (<Demo ob3>,)>"]


Relationship State
==================

All relationships may optionally have a ``state`` which is another
unicode string like ``relation``, which can be queried in the same
manner.  The state is intended to represent an aspect of a
relationship which changes over time.  For example, you could have
a 'collaborator' relationship between two users which is intiated
by the source user, at which point it is in a 'pending' state, and
approved by the target user, at which point it transitions to an
'approved' state.  A further use would be simply as a second-level
of taxonomy for a relationship (particularly one which is likely to
be changed over time), e.g. a 'buddy' relationship in a social networking
site, which would could be additionally categorized as 'acquaintance',
'pal', 'friend', 'BFF!!!OMG!!'.

The ``state`` attribute of a relationship is defined by the
``plone.relations.interfaces.IStatefulRelationship`` interface, and is
looked up via adaptation (just like ``IComplexRelationship``).  This
package provides some convenience adapters, and all that's needed to
make use of them are a couple marker interfaces.  The state adapter
uses annotations on the relationship and is applied to any
relationship implementing ``IAnnotationsState``, which itself requires
that the object be annotatable.  In this case we'll use attribute
annotations (see ``zope.annotation``).

When we create a relationship, we can specify what marker interfaces
to apply to it in order to customize it's behavior::

    >>> from zope.annotation.interfaces import IAttributeAnnotatable
    >>> rel = source.createRelationship(ob5, relation=u'relation 1',
    ...                                 interfaces=(IAttributeAnnotatable,
    ...                                 interfaces.IAnnotationsState))
    >>> pr_interfaces.IStatefulRelationship(rel).state = u'new'

The marker interfaces we applied made an adapter available to
IStatefulRelationship.  Hopefully it is clear how the application of
these marker interfaces can help apply custom behavior to relationships.

Let's see how our state can be used for queries:

    >>> list(source.getTargets(relation=u'relation 1'))
    [<Demo ob2>, <Demo ob3>, <Demo ob5>]
    >>> list(source.getTargets(relation=u'relation 1', state=u'new'))
    [<Demo ob5>]
    >>> list(source.getTargets(relation=u'relation 1', state=None))
    [<Demo ob2>, <Demo ob3>]

Note that querying for None will find objects whose state was never set,
or whose state was explicitly set to None.

We can also add or modify the state of an existing relationship::

    >>> rel = source.getRelationships(ob2).next()
    >>> rel
    <Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob3>)>
    >>> from zope import interface
    >>> interface.alsoProvides(rel, IAttributeAnnotatable,
    ...                        interfaces.IAnnotationsState)
    >>> pr_interfaces.IStatefulRelationship(rel).state = u'old'

    >>> list(source.getTargets(state=u'old'))
    [<Demo ob2>, <Demo ob3>]


Relationship Context
====================

There's one more optional query-able aspect of relationships, the context.
This is a bit more abstract than the ``source``, ``target``,
``relation``, and ``state`` we've seen so far.  It is another object that
plays a role in the relationship different from the sources or targets.  Some
instructive examples of this are a particular project or department in which
a relationship exists, i.e. 'Frank' manages 'Edward' on the
'Hamdi v. Rumsfeld Case', where the context here would be an object describing
the case, perhaps with supporting documents.  Another example would be for
a subject area in a Teacher - Student relationship.

The interface which provides this context is
``plone.relations.interfaces.IContextAwareRelationship`` which
has a ``getContext`` method to return the object representing the
relationship context.  This package provides another annotation
based adapter for context, which is used as above, and has a
``setContext`` method which handles reindexing.  The implementation
provided here requires that the context be a persistent object in the
ZODB (because it uses the same mechanism as sources and targets)::


    >>> ob6 = app['ob6']
    >>> my_context = app['ob7']
    >>> rel = source.createRelationship(ob6, relation=u'relation 1',
    ...                                 interfaces=(IAttributeAnnotatable,
    ...                                 interfaces.IAnnotationsContext))
    >>> pr_interfaces.IContextAwareRelationship(rel).setContext(my_context)

Let's see how our context can be used for queries:

    >>> list(source.getTargets(relation=u'relation 1'))
    [<Demo ob2>, <Demo ob3>, <Demo ob5>, <Demo ob6>]
    >>> list(source.getTargets(relation=u'relation 1', context=my_context))
    [<Demo ob6>]
    >>> list(source.getTargets(relation=u'relation 1', context=None))
    [<Demo ob2>, <Demo ob3>, <Demo ob5>]

Again we can apply or modify the context of an existing relationship
if desired:

    >>> rel = source.getRelationships(ob5).next()
    >>> rel
    <Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob5>,)>
    >>> interface.alsoProvides(rel, IAttributeAnnotatable,
    ...                        interfaces.IAnnotationsContext)
    >>> pr_interfaces.IContextAwareRelationship(rel).setContext(my_context)

    >>> list(source.getTargets(context=my_context))
    [<Demo ob5>, <Demo ob6>]


Filters
=======

Though the basic scheme of ``sources``, ``targets``, ``relation``,
``state``, ``context`` allows for some very rich relationships to be
built, you may want to apply further behavior and classifications to
your relationships.  The queries using the above interfaces are highly
optimized and don't require waking up any objects other than the
actual results, it's also possible to do further filtering of results
based on custom relationship filters using the ``rel_filter`` parameter
to the various query methods.

The filter looks at a relationship which matches the given query and
returns a boolean depending on whether the relationship should be used
for the final results or not.

Let's apply a marker interface to one of our relationships and use
the interface's ``providedBy`` as our filter::

    >>> class IMyInterface(interface.Interface):
    ...     pass
    >>> my_filter = IMyInterface.providedBy
    >>> rel = source.createRelationship(ob6, relation=u'relation 2',
    ...                                 interfaces=(IMyInterface,))
    >>> list(source.getTargets())
    [<Demo ob2>, <Demo ob3>, <Demo ob5>, <Demo ob6>]
    >>> list(source.getTargets(rel_filter=my_filter))
    [<Demo ob6>]

We need to get rid of this interface now because it will break some
tests later on because it is not picklable, this bit can be safely ignored::

    >>> rel = list(source.getRelationships(rel_filter=my_filter))[0]
    >>> interface.directlyProvides(rel, interfaces.IDefaultDeletion)
    >>> my_filter(rel)
    False

Source and Target Deletion
===========================

We want our relationships cleaned up when we delete either a source or
a target of a relationship.  To this end we have registered an event
which does so.

First we add some extra relationships to fully test that relationships
with multiple sources and/or targets are managed sanely::

    >>> rel = source2.createRelationship(targets=(ob3,ob1))
    >>> rel1 = list(source2.getRelationships())[0]
    >>> rel1
    <Relationship u'relation 2' from (<Demo ob2>,) to (<Demo ob3>,)>
    >>> rel1.sources = (ob2,ob1)
    >>> rel = source.createRelationship(targets=(ob2))

Now we check the current relationships and ensure they are removed
when the object is deleted::

    >>> list(interfaces.ISymmetricRelation(ob2).getRelationships())
    [<Relationship u'relation 2' from (<Demo ob1>, <Demo ob2>) to (<Demo ob3>,)>, <Relationship u'relation 1' from (<Demo ob2>,) to (<Demo ob5>,)>, <Relationship None from (<Demo ob2>,) to (<Demo ob1>, <Demo ob3>)>, <Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>, <Demo ob3>)>, <Relationship None from (<Demo ob1>,) to (<Demo ob2>,)>]
    >>> list(interfaces.IRelationshipSource(ob1).getTargets())
    [<Demo ob2>, <Demo ob3>, <Demo ob5>, <Demo ob6>]
    >>> app.manage_delObjects(['ob2'])
    >>> list(interfaces.ISymmetricRelation(ob2).getRelationships())
    []
    >>> list(interfaces.IRelationshipSource(ob1).getTargets())
    [<Demo ob3>, <Demo ob5>, <Demo ob6>]

There you can override this default deletion behavior by replacing the
``IDefaultDeletion`` marker that gets applied automatically interface
with another one that implements it's own subscribers for handling
deletion.  We've registered some subscribers for objects marked with
IHoldingRelation which prevent the object from being deleted if there
are relationships pointing to it as a target::

    >>> source3 = interfaces.IRelationshipSource(ob3)
    >>> rel = source3.createRelationship(targets=(ob1,ob4))
    >>> list(interface.directlyProvidedBy(rel))
    [<InterfaceClass plone.app.relations.interfaces.IDefaultDeletion>]
    >>> interface.directlyProvides(rel, interfaces.IHoldingRelation)
    >>> import transaction
    >>> sp = transaction.savepoint()
    >>> app.manage_delObjects(['ob4'])
    Traceback (most recent call last):
    ...
    HoldingRelationError: <Demo ob4> cannot be deleted, it is the target of a relationship to (<Demo ob3>,)
    >>> sp.rollback()

We made a savepoint and rolled it back, becuase normally such an exception
would trigger a transaction abort, and prevent a partial delete operation from being committed.


Object Copies
-------------

For some relationships it may be considered necessary that when a
source object is copied that the existing relationship be be copied
onto the new copy.  This package registers a subscriber that allows
this for relations marked with the IRetainOnCopy interface.  First
let's look at the default behavior::

    >>> list(source.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob3>,)>, <Relationship u'relation 2' from (<Demo ob1>,) to (<Demo ob3>,)>, <Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob5>,)>, <Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob6>,)>, <Relationship u'relation 2' from (<Demo ob1>,) to (<Demo ob6>,)>]
    >>> self.setRoles(['Manager']) # Deal with explicit security checks
    >>> app['ob1'].meta_type = 'Folder' # We need a metatype to copy
    ...                                 # because zope 2 sucks
    >>> copy_data = app.manage_copyObjects(['ob1'])
    >>> ignore = self.folder.manage_pasteObjects(copy_data)
    >>> copy_source = interfaces.IRelationshipSource(self.folder.ob1)
    >>> list(copy_source.getRelationships())
    []
    >>> self.folder.manage_delObjects(['ob1'])

Now we mark one of our relations (one with multiple sources to
increase complexity a bit) as an IRetainOnCopy relationship::

    >>> rel = list(source.getRelationships())[0]
    >>> rel.sources = (ob1, ob4)
    >>> interface.alsoProvides(rel, interfaces.IRetainOnCopy)
    >>> rel
    <Relationship u'relation 1' from (<Demo ob1>, <Demo ob4>) to (<Demo ob3>,)>
    >>> list(source.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>, <Demo ob4>) to (<Demo ob3>,)>, <Relationship u'relation 2' from (<Demo ob1>,) to (<Demo ob3>,)>, <Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob5>,)>, <Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob6>,)>, <Relationship u'relation 2' from (<Demo ob1>,) to (<Demo ob6>,)>]

    # XXX: we need to ghost the original relationship to remove the aq
    # wrappers on the sources, otherwise they won't be copyable::
    >>> import transaction
    >>> sp = transaction.savepoint()
    >>> rel._p_deactivate()

Now we make the copy and see that the marked relationship has been copied,
though only the copied object is used as the source::

    >>> copy_data = app.manage_copyObjects(['ob1'])
    >>> ignore = self.folder.manage_pasteObjects(copy_data)
    >>> copy_source = interfaces.IRelationshipSource(self.folder.ob1)
    >>> list(copy_source.getRelationships())
    [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob3>,)>]

    >>> tests.tearDown()
