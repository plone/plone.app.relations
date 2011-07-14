from zope.interface import implementer
from zope.component import adapter, getUtility
from zope.intid.interfaces import IIntIds
from plone.relations.interfaces import IRelatableProxy, IRelatableUnProxy
from Products.CMFCore.utils import getToolByName
from Products.PluggableAuthService.interfaces.authservice import IBasicUser
from Products.CMFCore.interfaces import IMemberData
from zope.annotation.interfaces import IAnnotations
from zope.site.hooks import getSite

USER_ANNOTATION = "plone.app.relations.memberdata_annotation"

@implementer(IRelatableProxy)
@adapter(IBasicUser)
def getUserRelatableProxy(user):
    mtool = getToolByName(user, 'portal_membership')
    memberdata = mtool.getMemberById(user.getId())
    intids = getUtility(IIntIds)
    intids.register(memberdata)
    annotation = IAnnotations(memberdata)
    annotation.setdefault(USER_ANNOTATION, user.getId())
    return memberdata

@implementer(IRelatableUnProxy)
@adapter(IMemberData)
def getUserFromProxy(proxy):
    acl_user = getToolByName(getSite(), 'acl_users')
    annotation = IAnnotations(proxy)
    userid = annotation.get(USER_ANNOTATION)
    user = acl_user.getUserById(userid)
    return user
