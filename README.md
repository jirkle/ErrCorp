##ErrCorp
ErrCorp is tool for automated generation of error corpora from wikipedia dump. It takes bz2 wiki dump with history and processes it page by page. During processing it splits pages content into sentences and looks for corresponding matches in two neighbour's revisions. Then for each match it looks for 4 types of errors:
* **Word order** - old &amp; new sentence have the same bag of words
* **Typo** - comment of rev contains predefined set of words (regex - typoFilter), typos are further extracted
* **Edit** - comment of rev contains predefined set of words (regex - editFilter)
* **Other** - all not classified errors

For more info check [wiki](https://github.com/jirkle/ErrCorp/wiki)
