"""
categorizer.py
Parses a free-text expense description and returns:
    - amount (float)
    - merchant (str)
    - category (str)
    - confidence (str: 'high' / 'low')

Works on strings like:
    "500 at McDonald's"
    "Paid 1200 for Uber ride"
    "Spent 3000 on groceries at DMart"
    "Netflix subscription 649"
"""

import re
from hindi_numbers import hindi_words_to_number, contains_devanagari

# Category -> keywords that trigger it. Order matters: first match wins,
# so more specific categories are listed before generic ones.
CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "restaurant", "cafe", "coffee", "pizza", "burger", "food", "dine",
        "lunch", "dinner", "breakfast", "swiggy", "zomato", "mcdonald", "mcd",
        "dominos", "kfc", "starbucks", "bar", "pub", "bakery", "eatery",
        "snack", "snacks", "tea", "chai", "juice", "ice cream", "dessert",
        "buffet", "canteen", "mess", "dhaba", "biryani", "sandwich",
        "chocolate", "sweets", "cake", "momos", "samosa", "thali", "roll",
        "subway", "barista", "chaayos", "haldiram", "wow momo", "faasos",
    ],
    "Groceries": [
        "grocery", "groceries", "supermarket", "vegetable", "vegetables",
        "fruits", "bigbasket", "blinkit", "zepto", "dmart", "kirana",
        "ration", "milk", "dairy", "reliance fresh", "more supermarket",
        "spencer", "nature's basket", "instamart", "grofers",
    ],
    "Transport": [
        "uber", "ola", "taxi", "cab", "fuel", "petrol", "diesel", "metro",
        "bus", "train", "toll", "parking", "rapido", "auto", "rickshaw",
        "railway", "irctc ticket", "fastag", "cng", "bike service",
        "car service", "car wash", "namma yatri",
    ],
    "Travel": [
        "hotel", "flight", "airbnb", "trip", "vacation", "booking.com",
        "makemytrip", "irctc", "resort", "goibibo", "yatra", "cleartrip",
        "indigo", "spicejet", "air india", "vistara", "oyo", "homestay",
        "visa fee", "passport", "luggage", "travel", "travelling", "traveling",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "mall", "clothes", "shoes",
        "shopping", "store", "ajio", "nykaa", "meesho", "snapdeal",
        "electronics", "gadget", "mobile phone", "laptop", "accessories",
        "decathlon", "lifestyle", "pantaloons", "shoppers stop", "westside",
        "shopped",
    ],
    "Entertainment": [
        "movie", "netflix", "spotify", "concert", "game", "pvr", "cinema",
        "subscription", "hotstar", "prime video", "bookmyshow", "inox",
        "gaming", "playstation", "xbox", "steam", "youtube premium",
        "amazon prime", "jiocinema", "sonyliv", "zee5", "party", "club",
    ],
    "Bills & Utilities": [
        "electricity", "water bill", "wifi", "internet", "recharge",
        "mobile bill", "rent", "maintenance", "dth", "broadband",
        "gas bill", "cylinder", "phone bill", "postpaid", "prepaid",
        "society maintenance", "cable bill", "jio", "airtel", "vi bill",
    ],
    "Health & Fitness": [
        "pharmacy", "medicine", "doctor", "hospital", "gym", "protein",
        "supplement", "clinic", "medical", "chemist", "dentist", "checkup",
        "lab test", "diagnostic", "physiotherapy", "yoga", "spa",
        "apollo pharmacy", "practo", "cult fit", "insurance premium",
    ],
    "Education": [
        "course", "book", "tuition", "fees", "exam", "udemy", "coursera",
        "college", "university", "school fees", "stationery", "textbook",
        "coaching", "byju's", "unacademy", "skillshare", "workshop",
    ],
}

# Hindi (Devanagari) equivalents / common terms for the same categories.
# Kept separate from CATEGORY_KEYWORDS so English matching stays unaffected.
HINDI_CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "खाना", "रेस्टोरेंट", "होटल में खाना", "नाश्ता", "दोपहर का खाना",
        "रात का खाना", "पिज़्ज़ा", "बर्गर", "चाय", "कॉफ़ी", "स्विगी", "ज़ोमैटो",
        "डॉमिनोज़", "मैकडॉनल्ड्स", "केएफसी", "बेकरी", "ढाबा", "मिठाई",
        "आइसक्रीम", "जूस", "स्नैक्स", "बिरयानी", "समोसा",
    ],
    "Groceries": [
        "किराना", "सब्ज़ी", "सब्जी", "फल", "राशन", "ग्रोसरी", "डीमार्ट",
        "बिगबास्केट", "ज़ेप्टो", "ब्लिंकिट", "दूध", "आटा", "चावल",
    ],
    "Transport": [
        "उबर", "ओला", "टैक्सी", "रिक्शा", "ऑटो", "पेट्रोल", "डीज़ल", "मेट्रो",
        "बस", "ट्रेन", "टोल", "पार्किंग", "सीएनजी", "रेलवे",
    ],
    "Travel": [
        "होटल", "फ्लाइट", "यात्रा", "टूर", "टिकट", "आईआरसीटीसी", "छुट्टी",
    ],
    "Shopping": [
        "अमेज़न", "फ्लिपकार्ट", "मॉल", "कपड़े", "जूते", "शॉपिंग", "दुकान",
        "मोबाइल", "इलेक्ट्रॉनिक्स",
    ],
    "Entertainment": [
        "मूवी", "फ़िल्म", "नेटफ्लिक्स", "स्पॉटिफ़ाई", "सिनेमा", "गाना", "गेम",
        "पार्टी",
    ],
    "Bills & Utilities": [
        "बिजली", "पानी का बिल", "वाईफाई", "इंटरनेट", "रिचार्ज", "मोबाइल बिल",
        "किराया", "मेंटेनेंस", "गैस", "सिलेंडर",
    ],
    "Health & Fitness": [
        "दवा", "दवाई", "डॉक्टर", "अस्पताल", "जिम", "फार्मेसी", "क्लिनिक",
        "इलाज",
    ],
    "Education": [
        "किताब", "ट्यूशन", "फीस", "कोर्स", "स्कूल", "कॉलेज", "स्टेशनरी",
    ],
}

# Hindi words spelled in Latin/Roman letters ("Hinglish") — this is what
# voice transcription usually returns for Hindi speech, e.g. "dudh" instead
# of "दूध". Kept separate from HINDI_CATEGORY_KEYWORDS (which is Devanagari
# only) and checked regardless of script, unlike that dict.
ROMANIZED_HINDI_CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "khana", "nashta", "dhaba", "mithai", "biryani", "samosa", "chai",
        "hotel me khana",
    ],
    "Groceries": [
        "kirana", "sabzi", "sabji", "phal", "ration", "dudh", "doodh",
        "aata", "atta", "chawal",
    ],
    "Transport": [
        "rickshaw", "petrol", "diesel", "auto", "rikshaw",
    ],
    "Travel": [
        "yatra", "chutti",
    ],
    "Shopping": [
        "kapde", "joote", "dukan",
    ],
    "Entertainment": [
        "gaana", "film",
    ],
    "Bills & Utilities": [
        "bijli", "bijli ka bill", "paani ka bill", "kiraya", "recharge",
    ],
    "Health & Fitness": [
        "dawa", "dawai", "aspatal", "ilaj",
    ],
    "Education": [
        "kitab", "fees", "tuition",
    ],
}

# Postpositions that typically follow a merchant/place name in Hindi
# (Hindi puts them AFTER the noun, unlike English "at"/"on" which come before)
_HINDI_MERCHANT_TRIGGERS = ["पर", "में", "को", "से"]

# Words to ignore when picking merchant tokens (amounts, currency, filler)
_HINDI_SKIP_WORDS = {
    "रुपये", "रुपए", "रु", "का", "की", "के", "खर्च", "किए", "किया", "हुआ",
    "लिए", "आज", "कल", "सिर्फ", "करीब", "लगभग",
}


# Words that typically precede a merchant/vendor name in casual speech/text
_MERCHANT_TRIGGERS = [" at ", " on ", " to ", " for ", " via ", " from ", " in "]

# Matches amounts like: 500, 1200, 1,200, ₹500, Rs. 500, INR 500, 500.50
_AMOUNT_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d{1,2})?")

# --- Keyword matching -------------------------------------------------------
# Keywords are matched on WORD BOUNDARIES, not as raw substrings. Plain
# `kw in text` produced silent misclassifications, because short keywords hide
# inside unrelated words: "ola" inside "chocolate", "bus" inside "business",
# "mess" inside "message", "tea" inside "instead", "atta" inside "attached".
_KEYWORD_RE_CACHE = {}


def _keyword_matches(keyword: str, haystack: str) -> bool:
    """True if `keyword` appears in `haystack` as a whole word/phrase."""
    pattern = _KEYWORD_RE_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)")
        _KEYWORD_RE_CACHE[keyword] = pattern
    return pattern.search(haystack) is not None


# --- Amount detection -------------------------------------------------------
# Not every number in a sentence is a rupee amount. Dates, times and item
# counts are numbers too, and treating them as amounts created phantom
# expenses ("fees 25000 on 15 August 2026" became three separate expenses).

MIN_AMOUNT = 1.0          # anything below this isn't a real expense
QUANTITY_CEILING = 20     # a small integer next to a word is likely a count

_MONTH_WORDS = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)

# Spans that look like dates/times rather than money. Masked out (replaced with
# spaces, preserving length so character offsets stay valid) before amount
# extraction.
_NON_AMOUNT_PATTERNS = [
    re.compile(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b"),                   # 15/08/2026
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTH_WORDS})\b\s*\d{{0,4}}", re.I),  # 15 August 2026
    re.compile(rf"\b(?:{_MONTH_WORDS})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s*\d{{0,4}}", re.I),   # August 15, 2026
    re.compile(r"\b(?:19|20)\d{2}\b(?!\s*(?:rs|rupees|rupee|/-))"),            # bare year
    re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", re.I),                  # 7 pm, 7:30am
]


def _mask_non_amounts(text: str) -> str:
    """Blank out date/time spans, keeping string length (and offsets) intact."""
    masked = text
    for pattern in _NON_AMOUNT_PATTERNS:
        masked = pattern.sub(lambda m: " " * len(m.group(0)), masked)
    return masked


def find_amount_spans(text: str) -> list:
    """
    Return [(start, end, value), ...] for every number in `text` that is
    plausibly a rupee amount. Offsets refer to the ORIGINAL string, so callers
    can use them to slice the text.
    """
    masked = _mask_non_amounts(text)
    spans = []
    for m in _AMOUNT_RE.finditer(masked):
        try:
            value = float(m.group(0).replace(",", ""))
        except ValueError:
            continue
        if value < MIN_AMOUNT:
            continue
        spans.append([m.start(), m.end(), value])

    # Quantity filter: "Bought 2 coffees for 240" — the 2 is a count, not money.
    # Only applied when a larger amount also exists, so "50 chai" keeps its 50.
    if len(spans) > 1:
        kept = []
        for start, end, value in spans:
            is_small_count = (
                value <= QUANTITY_CEILING
                and float(value).is_integer()
                and re.match(r"\s+[A-Za-z\u0900-\u097F]", text[end:end + 2] or "")
            )
            if not is_small_count:
                kept.append([start, end, value])
        if kept:
            spans = kept

    return [tuple(s) for s in spans]


def extract_amount(text: str):
    """
    Return the most plausible amount in the text, or None.
    Tries numeric digits first (works for both English and Hindi text that uses
    Arabic numerals); falls back to Hindi number-words ("पांच सौ") if no usable
    digits are found and the text is in Devanagari.
    """
    spans = find_amount_spans(text)
    if spans:
        return max(value for _, _, value in spans)

    if contains_devanagari(text):
        return hindi_words_to_number(text)

    return None


BRAND_NAME_FIXES = {
    "mcdonald's": "McDonald's", "mcdonalds": "McDonald's", "mcd": "McDonald's",
    "dmart": "DMart", "d-mart": "DMart",
    "kfc": "KFC", "pvr": "PVR", "bigbasket": "BigBasket",
    "swiggy": "Swiggy", "zomato": "Zomato", "paytm": "PayTM",
    "ola": "Ola", "uber": "Uber", "netflix": "Netflix",
    "amazon": "Amazon", "flipkart": "Flipkart", "myntra": "Myntra",
    "dominos": "Domino's", "domino's": "Domino's",
    "starbucks": "Starbucks", "irctc": "IRCTC", "ajio": "AJIO",
    "blinkit": "Blinkit", "zepto": "Zepto", "hotstar": "Hotstar",
    "spotify": "Spotify", "makemytrip": "MakeMyTrip",
    "bookmyshow": "BookMyShow", "cafe coffee day": "Cafe Coffee Day",
    "nykaa": "Nykaa", "meesho": "Meesho", "snapdeal": "Snapdeal",
    "decathlon": "Decathlon", "inox": "INOX", "oyo": "OYO",
    "goibibo": "Goibibo", "yatra": "Yatra", "cleartrip": "Cleartrip",
    "indigo": "IndiGo", "spicejet": "SpiceJet", "vistara": "Vistara",
    "instamart": "Instamart", "grofers": "Grofers", "rapido": "Rapido",
    "namma yatri": "Namma Yatri", "subway": "Subway", "barista": "Barista",
    "chaayos": "Chaayos", "haldiram": "Haldiram's", "wow momo": "Wow! Momo",
    "faasos": "Faasos", "apollo pharmacy": "Apollo Pharmacy", "practo": "Practo",
    "cult fit": "Cult.fit", "byju's": "BYJU'S", "byjus": "BYJU'S",
    "unacademy": "Unacademy", "skillshare": "Skillshare",
    "prime video": "Amazon Prime Video", "amazon prime": "Amazon Prime",
    "jiocinema": "JioCinema", "sonyliv": "SonyLIV", "zee5": "ZEE5",
    "jio": "Jio", "airtel": "Airtel",
}


def _apply_brand_fix(name: str) -> str:
    lower = name.lower().strip()
    return BRAND_NAME_FIXES.get(lower, name)


def _smart_title(text: str) -> str:
    """
    Title-cases each word without breaking on apostrophes.
    "mcdonald's" -> "McDonald's" style names aren't fully recoverable,
    but this avoids the "Mcdonald'S" bug from str.title().
    """
    words = text.split()
    result = []
    for word in words:
        if "'" in word:
            parts = word.split("'")
            capitalized = parts[0].capitalize() + "'" + "'".join(p.lower() for p in parts[1:])
            result.append(capitalized)
        else:
            result.append(word.capitalize())
    return " ".join(result)


# Filler/stopwords that should never be treated as part of a merchant name
_MERCHANT_STOPWORDS = {
    "today", "yesterday", "tomorrow", "spent", "rupees", "rupee", "rs",
    "worth", "for", "from", "of", "and", "that", "the", "a", "an", "only",
    "just", "around", "about", "approx", "approximately", "total", "bill",
    "amount", "paid", "cost", "costs", "expense", "expenses", "um", "uh",
    "like", "basically", "actually", "so", "well", "recently", "earlier",
}


def extract_merchant(text: str):
    """
    Best-effort extraction of the merchant/vendor name from the text.
    Strategy:
      1. Check for a known brand name anywhere in the text first — most
         reliable, works regardless of sentence structure.
      2. Fall back to grabbing 1-2 words after a trigger word ("at"/"on"/
         etc.), stopping at stopwords or numbers so run-on voice-style
         sentences don't produce garbage like "Pvr Spent 350".
    """
    lower = text.lower()

    # Strategy 1: known brand name lookup (longest match first)
    for brand_key in sorted(BRAND_NAME_FIXES.keys(), key=len, reverse=True):
        if _keyword_matches(brand_key, lower):
            return BRAND_NAME_FIXES[brand_key]

    # Strategy 2: positional extraction with stopword/number cutoff
    for trigger in _MERCHANT_TRIGGERS:
        if trigger in lower:
            idx = lower.rfind(trigger)
            remainder = text[idx + len(trigger):].strip()
            remainder = re.split(r"[.,!?]", remainder)[0].strip()

            words = remainder.split()
            candidate_words = []
            for w in words:
                w_clean = w.strip(".,!?")
                if w_clean.lower() in _MERCHANT_STOPWORDS:
                    break
                if re.fullmatch(r"\d+(\.\d+)?", w_clean):
                    break
                candidate_words.append(w_clean)
                if len(candidate_words) >= 2:
                    break

            if candidate_words:
                return _apply_brand_fix(_smart_title(" ".join(candidate_words)))
    return None


def extract_merchant_hindi(text: str):
    """
    Best-effort merchant extraction for Hindi text. Hindi postpositions
    (पर, में, को, से) follow the noun, so we look BEFORE the postposition,
    unlike the English version which looks after "at"/"on"/"for".
    """
    tokens = text.split()
    for i, tok in enumerate(tokens):
        clean_tok = tok.strip("।,.!?")
        if clean_tok in _HINDI_MERCHANT_TRIGGERS and i > 0:
            candidate_tokens = []
            # Walk backwards collecting non-number, non-skip-word tokens
            j = i - 1
            while j >= 0:
                t = tokens[j].strip("।,.!?")
                if t in _HINDI_SKIP_WORDS:
                    break
                if re.fullmatch(r"[\u0900-\u097F]+", t) is None and not re.fullmatch(r"\d+", t):
                    break
                if re.fullmatch(r"\d+", t):
                    break
                candidate_tokens.insert(0, t)
                j -= 1
                # Merchant names in these examples are usually 1 word
                if len(candidate_tokens) >= 2:
                    break
            if candidate_tokens:
                return " ".join(candidate_tokens)
    return None


def categorize_text(text: str):
    """
    Classify the text into one of CATEGORY_KEYWORDS based on keyword match.
    Checks English keywords first, then Hindi keywords, so mixed-language
    (Hinglish) text still gets matched correctly either way.
    """
    lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if _keyword_matches(kw, lower):
                return category, "high"

    if contains_devanagari(text):
        for category, keywords in HINDI_CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if _keyword_matches(kw, text):
                    return category, "high"
    else:
        # Not Devanagari, but could still be Hindi spoken/typed in Roman
        # letters ("Hinglish") — check the romanized keyword list too.
        for category, keywords in ROMANIZED_HINDI_CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if _keyword_matches(kw, lower):
                    return category, "high"

    return "Other", "low"


def parse_expense(text: str) -> dict:
    """
    Main entry point. Takes raw text (from typing or transcribed speech,
    English or Hindi) and returns a structured expense dict.
    """
    amount = extract_amount(text)
    category, confidence = categorize_text(text)

    if contains_devanagari(text):
        merchant = extract_merchant_hindi(text)
    else:
        merchant = extract_merchant(text)

    return {
        "raw_text": text.strip(),
        "amount": amount,
        "merchant": merchant or "Unknown",
        "category": category,
        "confidence": confidence,
    }


# Connector words that join multiple expenses in one sentence.
# English: and/also/then/&/plus/as well as    Hindi: और/फिर/तथा/एवं/साथ ही
#
# Also handles comma-separated lists with no conjunction:
# "500 for food, 200 for cab" (safe: only matches ", " with a space, so
# "1,200" thousand-separators are never split since they have no space
# after the comma).
_MULTI_EXPENSE_SPLIT_RE = re.compile(
    r"\s+(?:and|also|then|&|plus|as well as|additionally|aur|phir)\s+"
    r"|,\s+"
    r"|\s+(?:और|फिर|तथा|एवं|साथ ही|उसके बाद)\s+",
    re.IGNORECASE,
)


def split_multi_expense(text: str) -> list:
    """
    Splits a compound sentence into separate expense-describing segments.
    First splits on explicit connectors ("500 at McDonald's and 200 for
    shopping", comma lists, Hindi और/फिर/...). Then, for any resulting
    segment that still contains more than one amount, splits it further at
    each new amount's position — this catches juxtaposed expenses with no
    connector or preposition at all, like "200 shopping 500 petrol", not
    just ones followed by a preposition like "300 for petrol 400 for tolls".
    Returns a single-item list if no split point is found anywhere.
    """
    parts = _MULTI_EXPENSE_SPLIT_RE.split(text)
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        parts = [text.strip()]

    final_parts = []
    for part in parts:
        starts = [start for start, _, _ in find_amount_spans(part)]
        if len(starts) <= 1:
            final_parts.append(part)
            continue
        # Text before the first amount ("Bought") belongs to the first chunk.
        starts[0] = 0
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(part)
            chunk = part[start:end].strip()
            if chunk:
                final_parts.append(chunk)

    return final_parts if len(final_parts) > 1 else [text.strip()]


def parse_multiple_expenses(text: str) -> list:
    """
    Main entry point for compound input. Splits the text into individual
    expense segments and parses each one. Segments with no detectable
    amount are dropped (likely leftover connector fragments), unless
    NONE of the segments had an amount — in that case the whole original
    text is parsed as a single expense so input is never silently lost.
    """
    segments = split_multi_expense(text)
    results = [parse_expense(seg) for seg in segments]
    results_with_amount = [r for r in results if r["amount"] is not None]
    return results_with_amount if results_with_amount else [parse_expense(text)]


if __name__ == "__main__":
    # Quick manual test cases
    samples = [
        "500 at McDonald's",
        "Paid 1200 for Uber ride",
        "Spent 3000 on groceries at DMart",
        "Netflix subscription 649",
        "Gym membership 2000",
        "1500 rent bill",
        "Random stuff 300",
        # Hindi test cases
        "डॉमिनोज़ पर पांच सौ रुपये खर्च किए",
        "उबर पर 200 रुपये",
        "किराना का सामान तीन सौ का",
        "बिजली का बिल 1500",
    ]
    for s in samples:
        print(s, "->", parse_expense(s))