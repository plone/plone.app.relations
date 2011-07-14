import sys
from Acquisition import aq_base
from zope.interface import implements
from zope.component import adapts
from zope.site.hooks import getSite
from plone.app.relations import interfaces
from plone.app.relations.annotations import ANNOTATIONS_KEY
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.CMFCore.WorkflowCore import ObjectDeleted
from Products.DCWorkflow.Transitions import TRIGGER_USER_ACTION
from zope.annotation.interfaces import IAnnotations
from persistent.mapping import PersistentMapping
from zc.relationship.interfaces import IBidirectionalRelationshipIndex

_marker = []

class DCWorkflowAdapter(object):

    """ This adapter provides the IStatefulRelationship interface
    using the DCWorkflow engine from the CMF. As a result it requires
    a fair amount of existing infrastructure, including a workflow
    tool with a relevant workflow.  Our testing infrastructure has set
    up a fully functioning plone site for us.

    To demonstrate how to use this adapter, we build some stateful
    relationships between our site content:

        >>> from plone.app.relations import tests
        >>> tests.base_setup(portal)
        >>> from plone.app.relations import interfaces
        >>> from zope.annotation.interfaces import IAttributeAnnotatable
        >>> ob1 = portal['ob1']
        >>> ob2 = portal['ob2']
        >>> ob3 = portal['ob3']
        >>> source = interfaces.IRelationshipSource(ob1)
        >>> rel = source.createRelationship(ob2, relation=u'relation 1',
        ...             interfaces=(interfaces.IDCWorkflowableRelationship,
        ...                         IAttributeAnnotatable))


    Let's ghost this object before retrieving it again::

        >>> import transaction
        >>> sp = transaction.savepoint()
        >>> rel._p_deactivate()
        >>> rel.targets._p_deactivate()
        >>> rel.sources._p_deactivate()
        >>> rel = list(source.getRelationships())[0]

    We can see that this relationship currently has no state::

        >>> list(source.getRelationships(state=None))
        [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]
        >>> list(source.getRelationships(state='visible'))
        []

    Now we have our workflowable relationship, let's specify a workflow for it.
    We'll use the ``plone_workflow`` for convenience, though it is not
    necessarily a sensible workflow for a relationship.

        >>> stateful = interfaces.IStatefulRelationship(rel)
        >>> stateful.workflow_id = 'plone_workflow'

    Now our relationship should be in the default state of this
    workflow ``visible``, ad should be searchable based on this state::

        >>> stateful.state
        'visible'
        >>> list(source.getRelationships(state=None))
        []
        >>> list(source.getRelationships(state='visible'))
        [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]

    We can now see what transitions are available for the Owner in this
    relationship's state, and of course execute them::

        >>> self.setRoles(['Owner', 'Member'])
        >>> transitions = stateful.listActions()
        >>> len(transitions)
        2
        >>> transitions[0]['id']
        'hide'
        >>> transitions[1]['id']
        'submit'
        >>> stateful.doAction('submit', 'A comment for my submission')
        >>> stateful.state
        'pending'

    We should now be able to find our relationship using the new
    ``pending`` state::

        >>> list(source.getRelationships(state='visible'))
        []
        >>> list(source.getRelationships(state='pending'))
        [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]

    We should also be able to query our relationship for workflow variables
    besides state::

        >>> stateful.getInfo('review_history')
        [{'action': None, 'review_state': 'visible', 'actor': 'test_user_1_', 'comments': '', 'time': DateTime(...)}, {'action': 'submit', 'review_state': 'pending', 'actor': 'test_user_1_', 'comments': 'A comment for my submission', 'time': DateTime(...)}]

    We can also check if a particular action is allowed at the moment:

        >>> stateful.isActionAllowed('retract')
        True
        >>> stateful.isActionAllowed('publish')
        False

    If we change the workflow used, we get shifted to the default
    state of that workflow, and the relationship is reindexed::

        >>> stateful.workflow_id = 'folder_workflow'
        >>> stateful.state
        'visible'
        >>> list(source.getRelationships(state='visible'))
        [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]
        >>> stateful.workflow_id = 'plone_workflow'
        >>> stateful.state
        'visible'
        >>> list(source.getRelationships(state='visible'))
        [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]

    We can also set the name of the state variable for the workflow, which
    is helpful when using custom workflows that don't use the standard
    ``review_state``.  Here we set it to ``actor`` to demonstrate::

        >>> stateful.state_var = 'actor'
        >>> stateful.state
        'test_user_1_'
        >>> list(source.getRelationships(state='test_user_1_'))
        [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]

    We should also test the behavior for some pathological cases, which
    we expect to raise WorkflowException, though ``state`` should always
    return something sane::

        >>> stateful.doAction('bogus_action')
        Traceback (most recent call last):
        ...
        WorkflowException: No workflow provides the "bogus_action" action.
        >>> stateful.workflow_id = None
        >>> stateful.getInfo('review_state')
        Traceback (most recent call last):
        ...
        WorkflowException: Workflow definition not yet set.
        >>> stateful.workflow_id = 'bogus_workflow'
        Traceback (most recent call last):
        ...
        WorkflowException: Reqested workflow definition not found.
        >>> stateful.state is None
        True
    """

    implements(interfaces.IDCWorkflowRelationship)
    adapts(interfaces.IDCWorkflowableRelationship)

    def __init__(self, rel):
        # XXX: wrap our relationship in the current Site
        site_chain = getSite().aq_chain
        site_chain.insert(0, rel)
        rel = site_chain.pop(-1)
        for item in reversed(site_chain):
            rel = aq_base(site_chain.pop(-1)).__of__(rel)
        self.rel = rel
        # Use annotations for storing state
        self.annotations = IAnnotations(rel).setdefault(ANNOTATIONS_KEY,
                                                        PersistentMapping())
        # use the current Site for the tool lookup
        self.wf_tool = getToolByName(getSite(), 'portal_workflow')

    @apply
    def state_var():
        def get(self):
            return self.annotations.get('wf_state_var', 'review_state')
        def set(self, value):
            self.annotations['wf_state_var'] = value
            # reindex for new state
            if IBidirectionalRelationshipIndex.providedBy(self.rel.__parent__):
                self.rel.__parent__.reindex(self.rel)
        return property(get, set)

    @apply
    def workflow_id():
        def get(self):
            return self.annotations.get('dcworkflow_id', None)
        def set(self, value):
            self.annotations['dcworkflow_id'] = value
            if value is not None:
                wf = self._get_workflow()
                # reset workflow state to intial state of new workflow
                # XXX: Should we try to use an existing state when we switch back
                # to a workflow we had before?
                wf.notifyCreated(self.rel)
            # reindex for new state
            if IBidirectionalRelationshipIndex.providedBy(self.rel.__parent__):
                self.rel.__parent__.reindex(self.rel)
        return property(get, set)

    @property
    def state(self):
        # XXX: No acquisition path here
        try:
            return self.getInfo(self.state_var, None)
        except WorkflowException:
            return None

    def doAction(self, action, comment='', **kw):
        wf = self._get_workflow()
        if not wf.isActionSupported(self.rel, action, **kw):
            raise WorkflowException(
                'No workflow provides the "%s" action.' % action)
        wf.notifyBefore(self.rel, action)
        # notify(Blah)

        # XXX: no support for moving relationships during workflow for now
        try:
            res = wf.doActionFor(self.rel, action, comment, **kw)
        except ObjectDeleted, ex:
            res = ex.getResult()
        except:
            exc = sys.exc_info()
            wf.notifyException(self.rel, action, exc)
            #notify(Blah)
            raise
        wf.notifySuccess(self.rel, action, res)
        # Reindex (this should probably be triggered by an event)
        if IBidirectionalRelationshipIndex.providedBy(self.rel.__parent__):
            self.rel.__parent__.reindex(self.rel)
        #notify(Blah)
        return res

    def isActionAllowed(self, action):
        wf = self._get_workflow()
        return bool(wf.isActionSupported(self.rel, action))

    def getInfo(self, name, default=_marker, *args, **kw):
        wf = self._get_workflow()
        res = wf.getInfoFor(self.rel, name, default, *args, **kw)
        if res is _marker:
            raise WorkflowException('Could not get info: %s' % name)
        return res

    def listActions(self):
        result = {}
        wf = self._get_workflow()
        sdef = wf._getWorkflowStateOf(self.rel)
        # The url to the relationship should never be used we just use a name
        obj_url = '/'.join(self.rel.__name__)
        if sdef is not None:
            for tid in sdef.transitions:
                tdef = wf.transitions.get(tid, None)
                if tdef is not None and \
                   tdef.trigger_type == TRIGGER_USER_ACTION and \
                   wf._checkTransitionGuard(tdef, self.rel) and \
                   not result.has_key(tdef.id):
                    result[tdef.id] = {
                        'id': tdef.id,
                        'title': tdef.title,
                        'title_or_id': tdef.title_or_id(),
                        'description': tdef.description,
                        'name': tdef.actbox_name or tdef.title_or_id(),
                        'url': tdef.actbox_url %
                        {'content_url': obj_url,
                         'portal_url' : '',
                         'folder_url' : ''}}
        return tuple(result.values())

    def _get_workflow(self):
        if not self.workflow_id:
            raise WorkflowException('Workflow definition not yet set.')
        # XXX: Add Plone 3.0 compat
        wf = self.wf_tool.getWorkflowById(self.workflow_id)
        if wf is None:
            raise WorkflowException(
                'Reqested workflow definition not found.')
        return wf
