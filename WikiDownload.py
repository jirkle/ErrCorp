import mwclient
import urllib.request
from mwclient import MwClientError

#MW client site
site = None

def init(lang):
	global site
	site = mwclient.Site(lang + '.wikipedia.org')

# Takes article ID (integer)
#Returns the content of the Czech Wikipedia page with given ID, and the revision ID of the article versions which was retrieved
def get_page(article_id):
	try:
		page = site.Pages[article_id]
		revisions = page.revisions(prop='timestamp|flags|comment|user|content', expandtemplates=True, dir="newer", limit=5000)
		rev = revisions.next()
		revs = []
		try:
			while True:
				if '*' in rev:
					rev["format"] = "wikimarkup"
					revs.append(rev)
					if("comment" not in rev):
						rev["comment"] = ""
				rev = revisions.next()
		except StopIteration:
			pass
		page = { "revisions": revs, "name": page.name }
		return page
	except MwClientError as e:
		print('Unexpected mwclient error occurred: ' + e.__class__.__name__)
		print(e.args)
	except urllib.error.HTTPError as e:
		print(e.code)
		print(e.reason) 
	except urllib.error.URLError as e:
		print(e.reason)