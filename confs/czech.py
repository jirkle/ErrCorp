# coding=UTF-8
import re
import string
from UnicodeHack import hack_regexp

#Abbreviations from wiki https://cs.wiktionary.org/wiki/Kategorie:%C4%8Cesk%C3%A9_zkratky
abbrs = r"""\s+(a|abl|absol|abstr|adj|adm|adv|aj|ak|ak|akc|akt|et\sal|
alch|amer|anat|angl|anglosas|ap|apod|arab|arch|archit|arg|arm|astr|
astrol|atd|atp|att|bás|[Bb]c|[Bb]cA|belg|bibl|biol|bl|brig|brit|bulh|
býv|c|č|cca|čce|čes|čet|chem|chil|čín|cír|círk|čís|čj|ck|čp|csc|
csl|d|D|dán|dat|děj|dep|des|detto|dět|dial|[Dd][Ii][Čč]|DiS|dl|doc|
dol|dop|dopr|dór|dosl|dra|Dr|DrSc|dto|dtto|ekon|epic|Et|etnonym|eufem|
ev|event|f|fa|fam|fce|fě|fem|fil|film|fin|form|fot|fr|fut|fy|
fyz|gen|genmjr|genplk|genpor|geogr|geol|geom|germ|gram|gšt|hebr|herald|
hist|hl|hod|hor|horn|hovor|hud|hut|i|[Ii][Čč][Oo]|ie|imp|impf|ind|
indoevr|inf|Ing|instr|inter|interj|ión|iron|it|j|jap|jm|JuDr|k|
kanad|katalán|kce|kk|klas|km|kniž|ko|komp|konj|konkr|kpt|kr|Kr|kř|
ks|kuch|kupř|l|lat|lék|les|lid|lit|liturg|log|lok|m|mat|max|
meteor|metr|MgA|Mgr|mil|min|mj|mjr|ml|mld|mod|[Mm]ons|ms|MUDr|mysl|
n|náb|nám|námoř|např|neklas|něm|nesklon|než|niz|nom|nor|npor|nprap|
nrtm|nstržm|o|ob|obch|obyč|odd|odp|ojed|opt|p|part|pas|pejor|pers|
pf|Ph|Pha|pí|pl|plk|plpf|pol|pomn|popř|por|pplk|ppor|pprap|př|
prap|prav|práv|předl|prep|příp|přívl|přn|prof|ps|psč|r|R|rak|rcsl|refl|
reg|resp|rkp|RNDr|roč|RSDr|rtm|rtn|rum|rus|ř|řec|řeckokat|říj|římskokat|
řn|s|S|samohl|sg|škpt|sl|slang|slov|soudr|souhl|špan|spec|spol|
sport|šprap|srov|st|št|stfr|stol|str|střfr|střv|stržm|stsl|subj|subs|
superl|sv|svob|švýc|sz|š|t|táz|tech|telev|teol|Th|ThDr|tis|tj|
trans|tur|tv|typogr|tzn|tzv|úř|v|V|var|vč|vedl|veř|verb|vl|voj|
vok|vs|vůb|vulg|výtv|vz|vztaž|www|z|zahr|zajm|zast|zejm|zeměd|žert|zkr|
zn|zř|zvl)[.]"""

#Website domains
websites = r"""[.](?:cancerresearch|international|construction|versicherung|accountants|blackfriday|
contractors|engineering|enterprises|investments|motorcycles|photography|productions|williamhill|
associates|bnpparibas|consulting|creditcard|cuisinella|foundation|healthcare|immobilien|industries|
management|properties|republican|restaurant|technology|university|vlaanderen|allfinanz|bloomberg|
christmas|community|directory|education|equipment|financial|furniture|institute|marketing|melbourne|
solutions|vacations|airforce|attorney|bargains|boutique|brussels|budapest|builders|business|
capetown|catering|cleaning|clothing|computer|delivery|democrat|diamonds|discount|engineer|exchange|
feedback|firmdale|flsmidth|graphics|holdings|lighting|mortgage|partners|pharmacy|pictures|plumbing|
property|saarland|services|software|supplies|training|ventures|yokohama|abogado|academy|android|
auction|capital|caravan|careers|channel|college|cologne|company|cooking|country|cricket|cruises|
dentist|digital|domains|exposed|finance|fishing|fitness|flights|florist|forsale|frogans|gallery|
guitars|hamburg|holiday|hosting|kitchen|lacaixa|limited|network|neustar|okinawa|organic|realtor|
recipes|rentals|reviews|schmidt|science|shiksha|singles|spiegel|support|surgery|systems|website|
wedding|whoswho|youtube|active|agency|alsace|bayern|berlin|camera|career|center|chrome|church|
claims|clinic|coffee|condos|credit|dating|degree|dental|direct|durban|emerck|energy|estate|
events|expert|futbol|global|google|gratis|hiphop|insure|joburg|juegos|kaufen|lawyer|london|luxury|
madrid|maison|market|monash|mormon|moscow|museum|nagoya|otsuka|photos|physio|quebec|reisen|repair|
report|ryukyu|schule|social|supply|suzuki|sydney|taipei|tattoo|tienda|travel|viajes|villas|vision|
voting|voyage|webcam|yachts|yandex|actor|archi|audio|autos|black|build|cards|cheap|citic|click|
codes|cymru|dance|deals|email|gifts|gives|glass|globo|gmail|green|gripe|guide|homes|horse|house|
jetzt|koeln|lease|loans|lotto|mango|media|miami|nexus|ninja|paris|parts|party|photo|pizza|place|
poker|praxi|press|rehab|reise|rocks|rodeo|shoes|solar|space|tatar|tirol|today|tokyo|tools|trade|
vegas|vodka|wales|watch|works|world|aero|army|arpa|asia|band|beer|best|bike|blue|buzz|camp|care|
casa|cash|cern|city|club|cool|coop|desi|diet|dvag|fail|farm|fish|fund|gbiz|gent|gift|guru|haus|
help|here|host|immo|info|jobs|kiwi|kred|land|lgbt|life|limo|link|ltda|luxe|meet|meme|menu|mini|
mobi|moda|name|navy|pics|pink|pohl|post|prod|prof|qpon|reit|rest|rich|rsvp|ruhr|sarl|scot|sexy|
sohu|surf|tips|town|toys|vote|voto|wang|wien|wiki|work|yoga|zone|axa|bar|bid|bio|biz|bmw|boo|bzh|
cab|cal|cat|ceo|com|crs|dad|day|dnp|eat|edu|esq|eus|fly|foo|frl|gal|gle|gmo|gmx|gop|gov|hiv|how|
ibm|ing|ink|int|kim|krd|lds|mil|moe|mov|net|new|ngo|nhk|nra|nrw|nyc|ong|onl|ooo|org|ovh|pro|pub|
red|ren|rio|rip|sca|scb|soy|tax|tel|top|tui|uno|uol|vet|wed|wme|wtc|wtf|xxx|xyz|zip|ac|ad|ae|af|
ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|
bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|de|dj|dk|dm|do|dz|ec|ee|eg|er|es|et|
eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|
id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|
lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|
nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|
sg|sh|si|sj|sk|sl|sm|sn|so|sr|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|
tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|za|zm|zw)\s"""

#Sentence endings with digits (e.g.: ...in year 1999.)
digitsSentenceEndings = r"((roce|(z\slet)|(z\sroků))\s*[0-9\-\s]+)[.]"

#Punctuation
punctuation = '[%s]' % re.escape(string.punctuation)

#Compiled regexes
reList = {
    "abbrs": re.compile(abbrs, re.U | re.X),
    "websites": re.compile(websites, re.U | re.X),
    "digitsSentenceEndings": re.compile(digitsSentenceEndings, re.U | re.X),
    "punctuation": re.compile(punctuation, re.U | re.X)
}

#Capitals
caps = hack_regexp(r"(\\p{Lu})")

#Low letters
lows = hack_regexp(r"(\\p{Ll})")

#Digits
digits = r"([0-9])"

#Language specific decimal point
decimalPoint = r"[.|,]"

#Excluded pages
excludeFilter = re.compile(r""".*(Hlavní\sstrana|Rozcestník|Nápověda:|Wikipedista:|
Wikipedie:|Diskuse:|MediaWiki:|Portál:|Šablona:|Kategorie:|Soubor:).*""", re.U | re.X)

#Typo classification filter
typoFilter = re.compile(r""".*([Tt]ypo|[Cc]l[\s\:]|[Cc]leanup|[Cc]u[\s\:]|[Pp]řeklep|
[Pp]ravopis|[Kk]osmetické|[Dd]robnost|[Oo]prav|[Oo]pr[\s\:]|\-\>).*""", re.U | re.X)

#Edit classification filter
editFilter = re.compile(r""".*([Cc]opyedit|[Cc]pyed|[Ee]dit|[Pp]řepsání|[Tt]ypografie|
[Rr]evize|[Úú]prav).*""", re.U | re.X)

#Revert classification filter
revertFilter = re.compile(r"""(.*([Rr]evert|[Rr]vrt|[Rr]v[\s\:]|rvv|vrácen|zrušen|
vandal|[Ee]ditace\s(?:[0-9]\s)*uživatele|[Vv]erze\s(?:[0-9]\s)*uživatele).*)|rv""", re.U | re.X)

#Bot classification filter
botFilter = re.compile(r"""(.*([Rr]obot|[Bb]ot[\s\:]|[Bb]otCS|WPCleaner).*)""", re.U | re.X)