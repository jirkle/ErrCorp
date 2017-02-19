import mwclient
import urllib.request
import sys
import re
import io
from mwclient import MwClientError
from pprint import pprint

import utils
import WikiExtractor

#MW client site
site = None

def init(lang):
	global site
	site = mwclient.Site(lang + '.wikipedia.org')

# Takes article ID (integer)
#Returns the content of the Czech Wikipedia page with given ID, and the revision ID of the article versions which was retrieved
def get_page(article_id):
	global site
	try:
		page = site.Pages[article_id]
		revisions = page.revisions(prop='timestamp|flags|comment|user|content', expandtemplates=True, dir="newer")
		rev = revisions.next()
		page.revisions = []
		try:
			while True:
				if '*' in rev:
					rev["format"] = "wikimarkup"
					page.revisions.append(rev)
				rev = revisions.next()
		except:
			pass
		page = { "revisions": page.revisions, "name": page.name }
		return page
	except MwClientError as e:
		print('Unexpected mwclient error occurred: ' + e.__class__.__name__)
		print(e.args)
	except urllib.error.HTTPError as e:
		print(e.code)
		print(e.reason) 
	except urllib.error.URLError as e:
		print(e.reason)

