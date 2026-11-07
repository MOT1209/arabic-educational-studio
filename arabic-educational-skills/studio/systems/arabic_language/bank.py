"""بنك مفردات الأطفال: لكل حرف أمثلة في أول/وسط/آخر الكلمة.

كل مدخل: كلمة مشكولة | المفهوم بالإنجليزية (لتوليد/اختيار الصور) | الفئة.
الحالة الافتراضية لكل مدخل: reviewed=False. المدقق الحتمي يفحص الإملاء والموضع، أما صحة المعنى
والنطق فلا يُعدّ المدخل «معتمداً» إلا بتوقيع مراجع بشري في سجل المراجعة (review.py).
الكلمات المكتوبة بالشدة تُحتسب حرفاً واحداً (بَطَّة = ب ط ة).
"""
_RAW = {
"ا": ("أَسَد|lion|animal أَرْنَب|rabbit|animal أُمّ|mother|person",
      "بَاب|door|object كِتَاب|book|object سَمَاء|sky|nature",
      "عَصَا|walking stick|object دُنْيَا|world globe|nature رُؤْيَا|dream|abstract"),
"ب": ("بَطَّة|duck|animal بَيْت|house|place بَقَرَة|cow|animal",
      "حَبْل|rope|object سَبُّورَة|blackboard|object قُبَّعَة|hat|object عُلْبَة|box|object ثُعْبَان|snake|animal",
      "كَلْب|dog|animal عِنَب|grapes|food أَرْنَب|rabbit|animal"),
"ت": ("تُفَّاحَة|apple|food تِمْسَاح|crocodile|animal تَمْر|dates|food",
      "كِتَاب|book|object مَكْتَب|desk|object زَيْتُون|olives|food",
      "بَيْت|house|place زَيْت|oil|food حُوت|whale|animal"),
"ث": ("ثَعْلَب|fox|animal ثَوْر|bull|animal ثُعْبَان|snake|animal",
      "مُثَلَّث|triangle|shape أَثَاث|furniture|object أَثَر|footprint|nature",
      "غَيْث|rain|nature أَثَاث|furniture|object مُثَلَّث|triangle|shape"),
"ج": ("جَمَل|camel|animal جَبَل|mountain|nature جَزَرَة|carrot|food",
      "نَجْمَة|star|nature رَجُل|man|person مِجْهَر|microscope|object",
      "تَاج|crown|object بُرْج|tower|place ثَلْج|snow|nature"),
"ح": ("حِصَان|horse|animal حُوت|whale|animal حَلِيب|milk|food",
      "تُفَّاحَة|apple|food سَحَابَة|cloud|nature نَحْلَة|bee|animal",
      "مِفْتَاح|key|object مِصْبَاح|lamp|object تُفَّاح|apples|food"),
"خ": ("خَرُوف|sheep|animal خُبْز|bread|food خَيْمَة|tent|place",
      "نَخْلَة|palm tree|nature صَخْرَة|rock|nature",
      "مَطْبَخ|kitchen|place فَرْخ|chick|animal شَيْخ|old man|person"),
"د": ("دُبّ|bear|animal دَجَاجَة|hen|animal دَرَّاجَة|bicycle|object دَفْتَر|notebook|object",
      "مَدْرَسَة|school|place وَرْدَة|rose|nature حَدِيقَة|garden|place",
      "وَلَد|boy|person أَسَد|lion|animal يَد|hand|body"),
"ذ": ("ذُرَة|corn|food ذِئْب|wolf|animal ذَيْل|tail|body",
      "حِذَاء|shoe|object أُذُن|ear|body نَافِذَة|window|object",
      "أُسْتَاذ|teacher|person تِلْمِيذ|student|person"),
"ر": ("رُمَّان|pomegranate|food رَجُل|man|person رَأْس|head|body",
      "شَجَرَة|tree|nature فَرَاشَة|butterfly|animal سَيَّارَة|car|object",
      "قَمَر|moon|nature بَحْر|sea|nature حِمَار|donkey|animal"),
"ز": ("زَرَافَة|giraffe|animal زَهْرَة|flower|nature زَيْتُون|olives|food",
      "مِيزَان|scale|object مَزْرَعَة|farm|place",
      "مَوْز|banana|food خُبْز|bread|food كَنْز|treasure|object"),
"س": ("سَمَكَة|fish|animal سَاعَة|clock|object سَيَّارَة|car|object",
      "مَسْجِد|mosque|place بُسْتَان|orchard|place مِسْطَرَة|ruler|object",
      "فَرَس|mare|animal جَرَس|bell|object طَاوُوس|peacock|animal"),
"ش": ("شَمْس|sun|nature شَجَرَة|tree|nature شَمْعَة|candle|object",
      "فَرَاشَة|butterfly|animal رِيشَة|feather|object عَشَرَة|ten|number",
      "عُشّ|nest|animal فِرَاش|bed|object مِشْمِش|apricot|food"),
"ص": ("صَقْر|falcon|animal صَابُون|soap|object صُنْدُوق|box|object",
      "عُصْفُور|bird|animal مِصْبَاح|lamp|object بَصَل|onion|food",
      "قَفَص|cage|object حِمَّص|chickpeas|food قَمِيص|shirt|object"),
"ض": ("ضِفْدَع|frog|animal ضَوْء|light|nature ضَيْف|guest|person",
      "بَيْضَة|egg|food مِضْرَب|racket|object رِيَاضَة|sport|abstract",
      "أَرْض|ground|nature مَرِيض|sick person|person حَامِض|sour lemon|food"),
"ط": ("طَائِرَة|airplane|object طِفْل|child|person طَبْل|drum|object",
      "بَطَّة|duck|animal مِطْرَقَة|hammer|object سَطْل|bucket|object",
      "حَائِط|wall|place قِطّ|cat|animal بِسَاط|carpet|object"),
"ظ": ("ظَرْف|envelope|object ظِلّ|shadow|nature ظُفْر|fingernail|body",
      "نَظَّارَة|glasses|object عَظْم|bone|body مِظَلَّة|umbrella|object حَظِيرَة|barn|place",
      "لَفْظ|word|abstract حَافِظ|keeper|abstract غَلِيظ|thick|abstract"),
"ع": ("عُصْفُور|bird|animal عَيْن|eye|body عِنَب|grapes|food",
      "بَعُوضَة|mosquito|animal شَعْر|hair|body سَاعَة|clock|object",
      "إِصْبَع|finger|body ضِفْدَع|frog|animal رَبِيع|spring|nature"),
"غ": ("غَيْمَة|cloud|nature غُرَاب|crow|animal غَزَال|gazelle|animal",
      "مِغْرَفَة|ladle|object صَغِير|small|abstract مِغْنَاطِيس|magnet|object",
      "دِمَاغ|brain|body فَرَاغ|empty|abstract"),
"ف": ("فِيل|elephant|animal فَأْر|mouse|animal فُسْتَان|dress|object",
      "مِفْتَاح|key|object عُصْفُور|bird|animal سُلَحْفَاة|turtle|animal",
      "كَهْف|cave|place خَرُوف|sheep|animal سَيْف|sword|object"),
"ق": ("قَلَم|pen|object قِطَّة|cat|animal قِرْد|monkey|animal",
      "بَقَرَة|cow|animal مِقَصّ|scissors|object حَدِيقَة|garden|place",
      "طَرِيق|road|place وَرَق|paper|object بَرْق|lightning|nature"),
"ك": ("كَلْب|dog|animal كُرَة|ball|object كُرْسِيّ|chair|object",
      "مَكْتَب|desk|object سِكِّين|knife|object مِكْنَسَة|broom|object",
      "سَمَك|fish|animal دِيك|rooster|animal مَلِك|king|person"),
"ل": ("لَيْمُون|lemon|food لُعْبَة|toy|object لَبَن|milk|food",
      "قَلَم|pen|object سُلَّم|ladder|object بُلْبُل|nightingale|animal",
      "جَمَل|camel|animal هِلَال|crescent moon|nature بُرْتُقَال|orange|food"),
"م": ("مَطَر|rain|nature مِفْتَاح|key|object مَدْرَسَة|school|place",
      "سَمَكَة|fish|animal نَمْلَة|ant|animal قَمَر|moon|nature",
      "قَلَم|pen|object فَحْم|coal|object يَوْم|day|abstract"),
"ن": ("نَمِر|tiger|animal نَحْلَة|bee|animal نَجْمَة|star|nature",
      "عِنَب|grapes|food جَنَاح|wing|animal مِنْقَار|beak|animal",
      "عَيْن|eye|body غُصْن|branch|nature لِسَان|tongue|body"),
"ه": ("هِلَال|crescent moon|nature هَاتِف|phone|object هَرَم|pyramid|place",
      "زَهْرَة|flower|nature نَهْر|river|nature جِهَاز|device|object",
      "وَجْه|face|body نَزِيه|honest|abstract شَبِيه|similar|abstract"),
"و": ("وَرْدَة|rose|nature وَلَد|boy|person وَطَن|homeland|place",
      "كُوب|cup|object لَوْن|color|abstract جَوْرَب|sock|object",
      "دَلْو|bucket|object جَرْو|puppy|animal حَلْو|sweet|food"),
"ي": ("يَد|hand|body يَمَامَة|pigeon|animal يَاسَمِين|jasmine|nature",
      "بَيْت|house|place عَيْن|eye|body فِيل|elephant|animal",
      "كُرْسِيّ|chair|object شَاي|tea|food ظَبْي|gazelle|animal"),
}
# أمثلة على الألف المقصورة للمقارنة فقط (ليست أمثلة للألف)
_MAKSURA = "فَتَى|young man|person مُسْتَشْفَى|hospital|place هُدَى|guidance|abstract مَرْعَى|pasture|nature"
import re

_POS = ("initial", "medial", "final")
_ILLUSTRABLE_NOT = {"abstract", "number"}


def _entries(blob):
    # العناصر مفصولة بمسافة، لكن «المفهوم» قد يحوي مسافة؛ لذلك نفصل على نمط word|concept|cat
    res = []
    for m in re.finditer(r"([^|\s]+)\|([^|]+?)\|(\w+)(?=\s|$)", blob):
        res.append((m.group(1), m.group(2).strip(), m.group(3)))
    return res


def build_bank():
    bank = {}
    for letter, blobs in _RAW.items():
        bank[letter] = {}
        for pos, blob in zip(_POS, blobs):
            bank[letter][pos] = [{"word": w, "concept_en": c, "category": cat, "illustrable": cat not in _ILLUSTRABLE_NOT,
                                  "letter": letter, "position": pos} for w, c, cat in _entries(blob)]
    return bank


BANK = build_bank()
MAKSURA_CONTRAST = [{"word": w, "concept_en": c, "category": cat, "illustrable": cat not in _ILLUSTRABLE_NOT}
                    for w, c, cat in _entries(_MAKSURA)]


def words_for(letter, position=None):
    b = BANK.get(letter, {})
    return list(b.get(position, [])) if position else [e for p in _POS for e in b.get(p, [])]


def all_entries():
    return [e for l in BANK for p in _POS for e in BANK[l][p]]
