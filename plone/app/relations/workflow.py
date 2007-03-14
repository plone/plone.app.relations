import sys
from Acquisition import aq_parent, aq_get
from zope.interface import implements
from zope.component import adapts
from zope.event import notify
from plone.app.relations import interfaces
from plone.app.relations.annotations import ANNOTATIONS_KEY
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
from Products.DCWorkflow.Transitions import TRIGGER_USER_ACTION
from zope.app.annotation.interfaces import IAnnotations
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

        >>> from plone.app.relations import interfaces
        >>> from zope.app.annotation.interfaces import IAttributeAnnotatable
        >>> ob1 = portal['ob1']
        >>> ob2 = portal['ob2']
        >>> ob3 = portal['ob3']
        >>> source = interfaces.IRelationshipSource(ob1)
        >>> rel = source.createRelationship(ob2, relation=u'relation 1',
        ...             interfaces=(interfaces.IDCWorkflowableRelationship,
        ...                         IAttributeAnnotatable))

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

    We can now see what transitions are available for the
    relationship's state, and of course execute them::

        >>> transitions = stateful.listActions()
        >>> len(transitions)
        2
        >>> transitions[0]['id']
        'hide'
        >>> transitions[1]['id']
        'submit'
        >>> stateful.doAction('submit')
        >>> stateful.state
        'pending'

    We should now be able to find our relationship using the new
    ``pending`` state::

        >>> list(source.getRelationships(state='visible'))
        []
        >>> list(source.getRelationships(state='pending'))
        [<Relationship u'relation 1' from (<Demo ob1>,) to (<Demo ob2>,)>]


    """

    implements(interfaces.IDCWorkflowRelationship)
    adapts(interfaces.IDCWorkflowableRelationship)

    def __init__(self, rel):
        self.rel = rel
        self.annotations = IAnnotations(rel).setdefault(ANNOTATIONS_KEY,
                                                        PersistentMapping())
        if aq_parent(rel) is None:
            rel = rel.__of__(rel.__parent__)
        self.wf_tool = getToolByName(rel, 'portal_workflow')

    @apply
    def state_var():
        def get(self):
            return self.annotations.get('wf_state_var', 'review_state')
        def set(self, value):
            self.annotations['wf_state_var'] = value
            # XXX: Should we reindex here?
        return property(get, set)

    @apply
    def workflow_id():
        def get(self):
            return self.annotations.get('dcworkflow_id', None)
        def set(self, value):
            self.annotations['dcworkflow_id'] = value
            wf = self._get_workflow()
            # reset workflow state to intial state of new workflow
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
        return wf.isWorkflowMethodSupported(self.rel, action)

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
        # get the url using a method available on the REQUEST
        getURL = aq_get(self.wf_tool, 'REQUEST').physicalPathToURL
        obj_url = getURL(self.rel.getPhysicalPath())
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
