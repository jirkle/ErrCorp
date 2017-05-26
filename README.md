## ErrCorp
ErrCorp is a tool for automated generation of error-annotated corpora from Wikipedia sites. Such corpus contains the newest versions of articles with marked errors obtained from their editing history.

The script itself operates in situ, no additional files are created during processing (except the situation when the dump is located online and needs to be downloaded first). It is also unpretentious to memory as it processes input page by page.

### Install

	pip install mwclient
	pip install intervaltree
	pip install python-Levenshtein


### Usage

* Download and process pages through MediaWiki action API:

-a "Astronomie; Biologie; Fyzika;" -l "cs" -f "se" -r

* Process pages from local dump:

-p ../cswiki.xml.bz2 -l "cs" -f "txt" -r -m

For more info check [wiki](https://github.com/jirkle/ErrCorp/wiki)
