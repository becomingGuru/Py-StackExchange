# stackauth.py - Implements basic StackAuth support for Py-StackExchange

from stackweb import WebRequestManager
from stackcore import *
from stackexchange import Site, User, UserType
import re

class SiteState(Enumeration):
	"""Describes the state of a StackExchange site."""
	Normal, OpenBeta, ClosedBeta, LinkedMeta = range(4)

class SiteDefinition(JSONModel):
	"""Contains information about a StackExchange site, reported by StackAuth."""
	
	transfer = ('name', 'logo_url', 'api_endpoint', 'site_url', 'description', 'icon_url', 'aliases')

	def _extend(self, json, stackauth):
		fixed_state = re.sub(r'_([a-z])', lambda match: match.group(1).upper(), json.state)
		fixed_state = fixed_state[0].upper() + fixed_state[1:]

		self.state = SiteState.from_string(fixed_state)
		self.styling = DictObject(json.styling)
	
	def get_site(self, **kw):
		# A bit hackish; strips of the "http://"
		domain = site.api_endpoint[7:]
		return Site(domain, **kw)

class UserAssociation(JSONModel):
	transfer = ('display_name', 'reputation', 'email_hash')
	
	def _extend(self, json, stackauth):
		self.id = json.user_id
		self.user_type = UserType.from_string(json.user_type)
		self.on_site = SiteDefinition(json.on_site, stackauth)
	
	def get_user(self):
		return self.on_site.get_site().user(self.id)

class StackAuth(object):
	def __init__(self, **kw):
		# There's no reason to change this now, but you
		# never know.
		self.domain = kw['domain'] if 'domain' in kw else 'stackauth.com'
		self.use_gzip = kw['gzip'] if 'gzip' in kw else True
	
	# These methods are slightly more complex than they
	# could be so they retain rough compatibility with
	# their StackExchange counterparts for paginated sets

	def url(self, u):
		return 'http://' + self.domain + '/' + u

	def build(self, url, typ, collection, kw={}):
		mgr = WebRequestManager(gzip=self.use_gzip)
		json, info = mgr.json_request(url, kw)

		return JSONMangler.json_to_resultset(self, json, typ, collection, (self, url, typ, collection, kw))
	
	def sites(self):
		"""Returns information about all the StackExchanges ites currently lited on StackAuth.com"""
		return self.build(self.url('sites'), SiteDefinition, 'api_sites')
	
	def associated_from_assoc(self, assoc_id):
		"""Returns, given a user's *association ID*, all their accounts on other StackExchange sites."""
		return self.build(self.url('users/%s/associated' % assoc_id), UserAssociation, 'associated_users')
	
	def associated(self, site, user_id):
		"""Returns, given a target site object and a user ID for that site, their associated accounts on other StackExchange sites."""
		user = site.user(user_id)
		assoc = user.association_id
		return self.associated_from_assoc(assoc)
	
