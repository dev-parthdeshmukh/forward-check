"""Fixed strings the app itself writes, in the languages we reply in. Unknown languages get English."""
from .schemas import Verdict

VERDICT_LABELS = {
    "en": {
        Verdict.VERIFIED: "True", Verdict.FALSE: "False", Verdict.OUTDATED: "Outdated",
        Verdict.PARTLY_SUPPORTED: "Partly true", Verdict.UNVERIFIABLE: "Cannot be confirmed",
    },
    "hi": {
        Verdict.VERIFIED: "सही", Verdict.FALSE: "गलत", Verdict.OUTDATED: "पुराना",
        Verdict.PARTLY_SUPPORTED: "आंशिक रूप से सही", Verdict.UNVERIFIABLE: "पुष्टि नहीं हो सकी",
    },
    "mr": {
        Verdict.VERIFIED: "खरे", Verdict.FALSE: "खोटे", Verdict.OUTDATED: "जुने",
        Verdict.PARTLY_SUPPORTED: "अंशतः खरे", Verdict.UNVERIFIABLE: "खात्री करता आली नाही",
    },
}

# Shown when a verdict is withdrawn, so the reader never sees an explanation for a verdict we dropped.
ABSTAIN = {
    "en": "We could not find a reliable source that confirms or denies this claim. Treat it with caution and check before you forward it.",
    "hi": "इस दावे की पुष्टि या खंडन करने वाला कोई भरोसेमंद स्रोत हमें नहीं मिला। इसे सावधानी से लें और आगे भेजने से पहले जाँच लें।",
    "mr": "या दाव्याची पुष्टी किंवा खंडन करणारा कोणताही विश्वासार्ह स्रोत आम्हाला सापडला नाही. सावधगिरी बाळगा आणि पुढे पाठवण्यापूर्वी तपासा.",
}

RISK = {
    "unofficial_link": {
        "en": "The link {domain} is not an official government website. Indian government sites end in .gov.in or .nic.in.",
        "hi": "लिंक {domain} कोई सरकारी वेबसाइट नहीं है। भारत सरकार की वेबसाइटें .gov.in या .nic.in पर खत्म होती हैं।",
        "mr": "{domain} ही लिंक सरकारी वेबसाइट नाही. भारत सरकारच्या वेबसाइट .gov.in किंवा .nic.in ने संपतात.",
    },
    "short_link": {
        "en": "The link {domain} is shortened, so you cannot see which site it really opens.",
        "hi": "लिंक {domain} छोटा किया गया है, इसलिए पता नहीं चलता कि यह असल में कौन-सी वेबसाइट खोलेगा।",
        "mr": "{domain} ही लिंक लहान केलेली आहे, त्यामुळे ती प्रत्यक्षात कोणती वेबसाइट उघडते ते कळत नाही.",
    },
    "personal_info": {
        "en": "This message involves private details such as an OTP, password or bank account number. Never share these with anyone.",
        "hi": "इस संदेश में OTP, पासवर्ड या बैंक खाते जैसी निजी जानकारी की बात है। यह जानकारी कभी किसी को न दें।",
        "mr": "या संदेशात OTP, पासवर्ड किंवा बँक खात्यासारख्या खाजगी माहितीचा उल्लेख आहे. ही माहिती कधीही कोणाला देऊ नका.",
    },
    "pressure": {
        "en": "The message pushes you to act quickly or forward it to everyone. False messages often do this.",
        "hi": "यह संदेश जल्दी करने या सबको भेजने का दबाव डालता है। झूठे संदेशों में अक्सर ऐसा होता है।",
        "mr": "हा संदेश घाई करायला किंवा सगळ्यांना पाठवायला सांगतो. खोट्या संदेशांमध्ये असे अनेकदा असते.",
    },
}


BOT = {
    "en": {
        "welcome": "Hello! Forward me any message, screenshot, voice note, PDF or link and I will check it.\n\nTo choose the reply language, send /lang hi, /lang mr, /lang en or /lang auto.",
        "start": "Checking…", "claims": "Found {n} claim(s). Checking with trusted sources…",
        "search": "Searching: {detail}", "fetch": "Reading: {detail}",
        "wrong": "What is wrong", "true": "What is true", "warning": "Warning signs", "sources": "Sources",
        "listen": "🔊 Listen", "lang_set": "Reply language set to {name}.", "lang_help": "Use /lang hi, /lang mr, /lang en or /lang auto.",
        "unsupported": "Send text, a photo, a voice note, a PDF or a link.",
        "error": "Something went wrong. Please try again.",
    },
    "hi": {
        "welcome": "नमस्ते! कोई भी संदेश, स्क्रीनशॉट, वॉइस नोट, PDF या लिंक फ़ॉरवर्ड कीजिए, हम उसकी जाँच करेंगे।\n\nजवाब की भाषा चुनने के लिए /lang hi, /lang mr, /lang en या /lang auto भेजें।",
        "start": "जाँच हो रही है…", "claims": "{n} दावे मिले। भरोसेमंद स्रोतों से जाँच रहे हैं…",
        "search": "खोज: {detail}", "fetch": "पढ़ रहे हैं: {detail}",
        "wrong": "क्या गलत है", "true": "सही बात क्या है", "warning": "खतरे के संकेत", "sources": "स्रोत",
        "listen": "🔊 सुनें", "lang_set": "जवाब की भाषा अब {name} है।", "lang_help": "/lang hi, /lang mr, /lang en या /lang auto भेजें।",
        "unsupported": "टेक्स्ट, फ़ोटो, वॉइस नोट, PDF या लिंक भेजें।",
        "error": "कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।",
    },
    "mr": {
        "welcome": "नमस्कार! कोणताही संदेश, स्क्रीनशॉट, व्हॉइस नोट, PDF किंवा लिंक फॉरवर्ड करा, आम्ही तो तपासू.\n\nउत्तराची भाषा निवडण्यासाठी /lang hi, /lang mr, /lang en किंवा /lang auto पाठवा.",
        "start": "तपासत आहोत…", "claims": "{n} दावे सापडले. विश्वासार्ह स्रोतांकडून तपासत आहोत…",
        "search": "शोध: {detail}", "fetch": "वाचत आहोत: {detail}",
        "wrong": "काय चुकीचे आहे", "true": "खरी माहिती काय आहे", "warning": "धोक्याची चिन्हे", "sources": "स्रोत",
        "listen": "🔊 ऐका", "lang_set": "उत्तराची भाषा आता {name} आहे.", "lang_help": "/lang hi, /lang mr, /lang en किंवा /lang auto पाठवा.",
        "unsupported": "मजकूर, फोटो, व्हॉइस नोट, PDF किंवा लिंक पाठवा.",
        "error": "काहीतरी चुकले. कृपया पुन्हा प्रयत्न करा.",
    },
}

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


def bot_text(key: str, language_code: str, **fields) -> str:
    return _pick(BOT, language_code)[key].format(**fields)


def resolve_reply(requested: str | None, message_code: str, message_name: str) -> tuple[str, str]:
    """(code, name) of the language to reply in: the one asked for, else the message's own."""
    wanted = (requested or "").strip()
    if not wanted or wanted.lower() == "auto":
        return message_code, message_name
    if wanted.lower() in LANGUAGE_NAMES:
        return wanted.lower(), LANGUAGE_NAMES[wanted.lower()]
    for code, name in LANGUAGE_NAMES.items():
        if name.lower() == wanted.lower():
            return code, name
    # A language we hold no fixed strings for: the model writes in it, our own labels stay English.
    return "en", wanted


def reply_key(requested: str | None) -> str:
    """One spelling per reply-language request: "auto", a code we know, or the name as typed."""
    wanted = (requested or "").strip().lower()
    if not wanted or wanted == "auto":
        return "auto"
    for code, name in LANGUAGE_NAMES.items():
        if wanted in (code, name.lower()):
            return code
    return wanted


def _pick(table: dict, language_code: str):
    return table.get(language_code, table["en"])


def verdict_label(verdict: Verdict, language_code: str) -> str:
    return _pick(VERDICT_LABELS, language_code)[verdict]


def abstain_text(language_code: str) -> str:
    return _pick(ABSTAIN, language_code)


def risk_text(code: str, language_code: str, **fields) -> str:
    return _pick(RISK[code], language_code).format(**fields)
