##ErrCorp
ErrCorp is tool for automated generation of error corpora from wikipedia dump.

### How it works
It takes bz2 wiki dump with history and processes it page by page. During processing it compares content of every two adjacent revisions and gets unique sentences in older and newer revision. Then ErrCorp links each old sentence to best matching new sentence and finally each of these matches are resolved as one type of error:
* **Word order** - old &amp; new sentence have the same bag of words
* **Typo** - comment of rev contains predefined set of words (regex - typoFilter), typos are further extracted
* **Edit** - comment of rev contains predefined set of words (regex - editFilter)
* **Other** - all other, non classified errors

For more info check [wiki](https://github.com/jirkle/ErrCorp/wiki)
