// Interface text in the three languages the app replies in. A value is a string or a function of its inputs.

const en = {
  tagline: "Is this forward true?",
  subtitle: "Checked against official sources and fact-checkers",
  heroTitle: "Check before you forward.",
  heroBody: "Send any message you received. We check its claims against official sources and fact-checkers, then tell you what is true, what is false, and why.",
  how: "How it works",
  how1t: "Send anything", how1b: "Text, a screenshot, a voice note, a PDF or a link.",
  how2t: "We find the claims", how2b: "The statements that can actually be checked.",
  how3t: "We check live", how3b: "Official sites and fact-checkers, searched as you watch.",
  how4t: "No source, no verdict", how4b: "Code verifies every source. Weak proof means we say so.",
  verdictsTitle: "What the answers mean",
  v_VERIFIED: "True", d_VERIFIED: "Reliable sources confirm it, and it is true today.",
  v_FALSE: "False", d_FALSE: "Reliable sources say the opposite, or it does not exist.",
  v_OUTDATED: "Outdated", d_OUTDATED: "It was true once, but things have changed.",
  v_PARTLY_SUPPORTED: "Partly true", d_PARTLY_SUPPORTED: "One part is right and another part is wrong.",
  v_UNVERIFIABLE: "Cannot be confirmed", d_UNVERIFIABLE: "We found no reliable proof either way.",
  trusted: "Sources we trust",
  tier_official: "Official", tier_fact_checker: "Fact-checker", tier_news: "News", tier_other: "Other site",
  tiers_official: "Official bodies", tiers_fact_checker: "Fact-checkers", tiers_news: "News and journals",
  poweredBy: (model) => `Reasoning by ${model}`,
  language: "Language", langAuto: "Auto", clearChat: "Clear chat", aboutApp: "About", close: "Close",
  dropHere: "Drop the file to check it",
  attach: "Attach a screenshot, PDF or voice note",
  placeholder: "Paste a message or a link",
  record: "Record a voice note", send: "Send", cancel: "Cancel", recording: "Recording",
  micDenied: "The microphone is not available. Allow it in your browser, or attach a voice note file.",
  welcome1: "Hello! Send me any forwarded message and I will check it for you.",
  welcome2: "Type or paste text, attach a screenshot or PDF, record a voice note, or paste a link.",
  tryExamples: "Or try one of these",
  ex_scheme: "Free laptop scheme", ex_note: "₹2000 note deadline", ex_shot: "6 days of darkness",
  ex_voice: "Garlic cures dengue", ex_marathi: "Hot water and corona",
  kind_text: "Text", kind_image: "Screenshot", kind_audio: "Voice note", kind_pdf: "PDF", kind_url: "Link",
  st_text: "Reading your message", st_audio: "Listening to your voice note", st_link: "Opening the link",
  st_image: "Reading your screenshot", st_pdf: "Reading the PDF", st_retrying: "Trying another way",
  findClaims: "Finding the claims",
  claimsFound: (n) => (n === 1 ? "1 claim to check" : `${n} claims to check`),
  checking: "Checking with trusted sources",
  starting: "Looking for sources",
  searching: (q) => `Searching: ${q}`,
  readingSite: (d) => `Reading ${d}`,
  usuallyTakes: "This usually takes about 30 seconds.",
  conf_high: "High confidence", conf_medium: "Medium confidence", conf_low: "Low confidence",
  whatWrong: "What is wrong", whatTrue: "What is true",
  warning: "Warning signs in this message",
  checkedMessage: "Your message, checked",
  claimsChecked: "Claims we checked",
  sources: (n) => (n === 1 ? "1 source" : `${n} sources`),
  showProof: (n) => `See the proof (${n === 1 ? "1 source" : `${n} sources`})`,
  hideProof: "Hide the proof",
  noProof: "No source was strong enough to show.",
  howChecked: "How we checked",
  searchCount: (n) => (n === 1 ? "1 search" : `${n} searches`),
  pageCount: (n) => (n === 1 ? "1 page read" : `${n} pages read`),
  seconds: (t) => `${t} sec`,
  stance_refutes: "Says this is wrong", stance_supports: "Confirms this", stance_context: "Background",
  samePage: "The page you sent",
  openSource: "Open source",
  listen: "Listen", stop: "Stop", share: "Share", copy: "Copy", copied: "Copied",
  tl_was: "Was true", tl_changed: "Changed", tl_today: "Today",
  cached: (n) => `Checked before, asked ${n} times`,
  health: "This is not medical advice. For any illness, talk to a doctor.",
  withdrawn: (label) => `The AI first answered “${label}”, but it had no strong source, so we are not confirming it.`,
  noClaimsTitle: "Nothing to check here",
  error: "Something went wrong. Please try again.", retry: "Try again", more: "Show more",
  fallback: "Our main checker was busy, so this answer drew on fewer sources.",
  readImage: "What we read", readAudio: "What we heard",
  shareTitle: "Share the correction",
  shareHint: "Send this back to the group where you got the message.",
  download: "Download image", shareSend: "Share",
  sc_said: "The message said", sc_sources: "Sources", sc_footer: "Check before you forward.",
  sc_checked: (d) => `Checked on ${d}`,
};

const hi = {
  tagline: "क्या यह फ़ॉरवर्ड सच है?",
  subtitle: "सरकारी स्रोतों और फ़ैक्ट-चेकर्स से जाँच",
  heroTitle: "आगे भेजने से पहले जाँच लें।",
  heroBody: "आपको मिला कोई भी संदेश भेजिए। हम उसके दावों को सरकारी स्रोतों और फ़ैक्ट-चेकर्स से मिलाते हैं, और बताते हैं कि क्या सही है, क्या गलत है और क्यों।",
  how: "यह कैसे काम करता है",
  how1t: "कुछ भी भेजिए", how1b: "टेक्स्ट, स्क्रीनशॉट, वॉइस नोट, PDF या लिंक।",
  how2t: "हम दावे ढूँढते हैं", how2b: "वे बातें जिनकी सचमुच जाँच हो सकती है।",
  how3t: "हम तुरंत जाँचते हैं", how3b: "सरकारी साइटें और फ़ैक्ट-चेकर्स, आपके सामने खोजे जाते हैं।",
  how4t: "स्रोत नहीं, तो फ़ैसला नहीं", how4b: "हर स्रोत कोड से जाँचा जाता है। सबूत कमज़ोर हो तो हम साफ़ बताते हैं।",
  verdictsTitle: "जवाबों का मतलब",
  v_VERIFIED: "सही", d_VERIFIED: "भरोसेमंद स्रोत इसकी पुष्टि करते हैं और यह आज भी सही है।",
  v_FALSE: "गलत", d_FALSE: "भरोसेमंद स्रोत इसका उल्टा कहते हैं, या ऐसी कोई चीज़ है ही नहीं।",
  v_OUTDATED: "पुराना", d_OUTDATED: "यह पहले सही था, लेकिन अब बात बदल चुकी है।",
  v_PARTLY_SUPPORTED: "आंशिक रूप से सही", d_PARTLY_SUPPORTED: "एक हिस्सा सही है और दूसरा गलत।",
  v_UNVERIFIABLE: "पुष्टि नहीं हो सकी", d_UNVERIFIABLE: "हमें किसी भी तरफ़ का भरोसेमंद सबूत नहीं मिला।",
  trusted: "हमारे भरोसेमंद स्रोत",
  tier_official: "सरकारी", tier_fact_checker: "फ़ैक्ट-चेकर", tier_news: "समाचार", tier_other: "अन्य साइट",
  tiers_official: "सरकारी संस्थाएँ", tiers_fact_checker: "फ़ैक्ट-चेकर", tiers_news: "समाचार और शोध पत्रिकाएँ",
  poweredBy: (model) => `${model} से तर्क`,
  language: "भाषा", langAuto: "अपने-आप", clearChat: "चैट साफ़ करें", aboutApp: "जानकारी", close: "बंद करें",
  dropHere: "जाँच के लिए फ़ाइल यहाँ छोड़ें",
  attach: "स्क्रीनशॉट, PDF या वॉइस नोट जोड़ें",
  placeholder: "संदेश या लिंक यहाँ चिपकाएँ",
  record: "वॉइस नोट रिकॉर्ड करें", send: "भेजें", cancel: "रद्द करें", recording: "रिकॉर्ड हो रहा है",
  micDenied: "माइक्रोफ़ोन उपलब्ध नहीं है। ब्राउज़र में इसकी अनुमति दें, या वॉइस नोट की फ़ाइल जोड़ें।",
  welcome1: "नमस्ते! कोई भी फ़ॉरवर्ड किया हुआ संदेश भेजिए, हम उसकी जाँच करके बताएँगे।",
  welcome2: "टेक्स्ट लिखें या चिपकाएँ, स्क्रीनशॉट या PDF जोड़ें, वॉइस नोट रिकॉर्ड करें, या लिंक भेजें।",
  tryExamples: "या इनमें से कोई आज़माइए",
  ex_scheme: "फ़्री लैपटॉप योजना", ex_note: "₹2000 के नोट की तारीख", ex_shot: "6 दिन का अँधेरा",
  ex_voice: "लहसुन से डेंगू ठीक", ex_marathi: "गरम पानी और कोरोना",
  kind_text: "टेक्स्ट", kind_image: "स्क्रीनशॉट", kind_audio: "वॉइस नोट", kind_pdf: "PDF", kind_url: "लिंक",
  st_text: "आपका संदेश पढ़ रहे हैं", st_audio: "आपका वॉइस नोट सुन रहे हैं", st_link: "लिंक खोल रहे हैं",
  st_image: "आपका स्क्रीनशॉट पढ़ रहे हैं", st_pdf: "PDF पढ़ रहे हैं", st_retrying: "दूसरे तरीके से कोशिश कर रहे हैं",
  findClaims: "दावे ढूँढ रहे हैं",
  claimsFound: (n) => (n === 1 ? "1 दावे की जाँच" : `${n} दावों की जाँच`),
  checking: "भरोसेमंद स्रोतों से जाँच रहे हैं",
  starting: "स्रोत ढूँढ रहे हैं",
  searching: (q) => `खोज: ${q}`,
  readingSite: (d) => `पढ़ रहे हैं: ${d}`,
  usuallyTakes: "इसमें आम तौर पर लगभग 30 सेकंड लगते हैं।",
  conf_high: "ज़्यादा भरोसा", conf_medium: "मध्यम भरोसा", conf_low: "कम भरोसा",
  whatWrong: "क्या गलत है", whatTrue: "सही बात क्या है",
  warning: "इस संदेश में खतरे के संकेत",
  checkedMessage: "आपका संदेश, जाँच के बाद",
  claimsChecked: "जिन दावों की जाँच हुई",
  sources: (n) => `${n} स्रोत`,
  showProof: (n) => `सबूत देखें (${n} स्रोत)`,
  hideProof: "सबूत छिपाएँ",
  noProof: "दिखाने लायक कोई मज़बूत स्रोत नहीं मिला।",
  howChecked: "हमने कैसे जाँचा",
  searchCount: (n) => `${n} खोज`,
  pageCount: (n) => (n === 1 ? "1 पन्ना पढ़ा" : `${n} पन्ने पढ़े`),
  seconds: (t) => `${t} सेकंड`,
  stance_refutes: "इसे गलत बताता है", stance_supports: "इसकी पुष्टि करता है", stance_context: "पृष्ठभूमि",
  samePage: "आपका भेजा हुआ पन्ना",
  openSource: "स्रोत खोलें",
  listen: "सुनें", stop: "रोकें", share: "शेयर करें", copy: "कॉपी करें", copied: "कॉपी हो गया",
  tl_was: "तब सही था", tl_changed: "बदल गया", tl_today: "आज",
  cached: (n) => `पहले जाँचा जा चुका है, ${n} बार पूछा गया`,
  health: "यह डॉक्टरी सलाह नहीं है। किसी भी बीमारी के लिए डॉक्टर से मिलें।",
  withdrawn: (label) => `AI का पहला जवाब “${label}” था, लेकिन उसके पास कोई मज़बूत स्रोत नहीं था, इसलिए हम इसकी पुष्टि नहीं कर रहे।`,
  noClaimsTitle: "इसमें जाँचने लायक कुछ नहीं है",
  error: "कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।", retry: "फिर से कोशिश करें", more: "और दिखाएँ",
  fallback: "हमारा मुख्य जाँच तंत्र व्यस्त था, इसलिए यह जवाब कम स्रोतों पर आधारित है।",
  readImage: "हमने यह पढ़ा", readAudio: "हमने यह सुना",
  shareTitle: "सही जानकारी शेयर करें",
  shareHint: "इसे उसी ग्रुप में भेजिए जहाँ से यह संदेश आया था।",
  download: "तस्वीर डाउनलोड करें", shareSend: "शेयर करें",
  sc_said: "संदेश में कहा गया", sc_sources: "स्रोत", sc_footer: "आगे भेजने से पहले जाँच लें।",
  sc_checked: (d) => `${d} को जाँचा गया`,
};

const mr = {
  tagline: "हा फॉरवर्ड खरा आहे का?",
  subtitle: "सरकारी स्रोत आणि फॅक्ट-चेकर्सकडून पडताळणी",
  heroTitle: "पुढे पाठवण्याआधी तपासा.",
  heroBody: "तुम्हाला आलेला कोणताही संदेश पाठवा. आम्ही त्यातील दावे सरकारी स्रोत आणि फॅक्ट-चेकर्सशी पडताळतो, आणि काय खरे आहे, काय खोटे आहे आणि का, ते सांगतो.",
  how: "हे कसे काम करते",
  how1t: "काहीही पाठवा", how1b: "मजकूर, स्क्रीनशॉट, व्हॉइस नोट, PDF किंवा लिंक.",
  how2t: "आम्ही दावे शोधतो", how2b: "ज्या गोष्टी खरोखर तपासता येतात त्या.",
  how3t: "आम्ही लगेच तपासतो", how3b: "सरकारी साइट आणि फॅक्ट-चेकर्स, तुमच्यासमोर शोधले जातात.",
  how4t: "स्रोत नाही, तर निकाल नाही", how4b: "प्रत्येक स्रोत कोडद्वारे तपासला जातो. पुरावा कमकुवत असेल तर आम्ही तसे सांगतो.",
  verdictsTitle: "उत्तरांचा अर्थ",
  v_VERIFIED: "खरे", d_VERIFIED: "विश्वासार्ह स्रोत याची पुष्टी करतात आणि हे आजही खरे आहे.",
  v_FALSE: "खोटे", d_FALSE: "विश्वासार्ह स्रोत याच्या उलट सांगतात, किंवा अशी गोष्ट अस्तित्वातच नाही.",
  v_OUTDATED: "जुने", d_OUTDATED: "हे आधी खरे होते, पण आता परिस्थिती बदलली आहे.",
  v_PARTLY_SUPPORTED: "अंशतः खरे", d_PARTLY_SUPPORTED: "एक भाग बरोबर आहे आणि दुसरा चुकीचा.",
  v_UNVERIFIABLE: "खात्री करता आली नाही", d_UNVERIFIABLE: "आम्हाला कोणत्याही बाजूचा विश्वासार्ह पुरावा सापडला नाही.",
  trusted: "आमचे विश्वासार्ह स्रोत",
  tier_official: "सरकारी", tier_fact_checker: "फॅक्ट-चेकर", tier_news: "बातम्या", tier_other: "इतर साइट",
  tiers_official: "सरकारी संस्था", tiers_fact_checker: "फॅक्ट-चेकर", tiers_news: "बातम्या आणि संशोधन नियतकालिके",
  poweredBy: (model) => `${model} द्वारे विश्लेषण`,
  language: "भाषा", langAuto: "आपोआप", clearChat: "चॅट साफ करा", aboutApp: "माहिती", close: "बंद करा",
  dropHere: "तपासण्यासाठी फाइल इथे सोडा",
  attach: "स्क्रीनशॉट, PDF किंवा व्हॉइस नोट जोडा",
  placeholder: "संदेश किंवा लिंक इथे पेस्ट करा",
  record: "व्हॉइस नोट रेकॉर्ड करा", send: "पाठवा", cancel: "रद्द करा", recording: "रेकॉर्ड होत आहे",
  micDenied: "मायक्रोफोन उपलब्ध नाही. ब्राउझरमध्ये परवानगी द्या, किंवा व्हॉइस नोटची फाइल जोडा.",
  welcome1: "नमस्कार! कोणताही फॉरवर्ड केलेला संदेश पाठवा, आम्ही तो तपासून सांगू.",
  welcome2: "मजकूर टाइप किंवा पेस्ट करा, स्क्रीनशॉट किंवा PDF जोडा, व्हॉइस नोट रेकॉर्ड करा, किंवा लिंक पाठवा.",
  tryExamples: "किंवा यापैकी एक वापरून पाहा",
  ex_scheme: "मोफत लॅपटॉप योजना", ex_note: "₹2000 च्या नोटेची मुदत", ex_shot: "6 दिवस अंधार",
  ex_voice: "लसणाने डेंग्यू बरा", ex_marathi: "गरम पाणी आणि कोरोना",
  kind_text: "मजकूर", kind_image: "स्क्रीनशॉट", kind_audio: "व्हॉइस नोट", kind_pdf: "PDF", kind_url: "लिंक",
  st_text: "तुमचा संदेश वाचत आहोत", st_audio: "तुमची व्हॉइस नोट ऐकत आहोत", st_link: "लिंक उघडत आहोत",
  st_image: "तुमचा स्क्रीनशॉट वाचत आहोत", st_pdf: "PDF वाचत आहोत", st_retrying: "दुसऱ्या मार्गाने प्रयत्न करत आहोत",
  findClaims: "दावे शोधत आहोत",
  claimsFound: (n) => (n === 1 ? "1 दाव्याची तपासणी" : `${n} दाव्यांची तपासणी`),
  checking: "विश्वासार्ह स्रोतांकडून तपासत आहोत",
  starting: "स्रोत शोधत आहोत",
  searching: (q) => `शोध: ${q}`,
  readingSite: (d) => `वाचत आहोत: ${d}`,
  usuallyTakes: "याला साधारण 30 सेकंद लागतात.",
  conf_high: "जास्त खात्री", conf_medium: "मध्यम खात्री", conf_low: "कमी खात्री",
  whatWrong: "काय चुकीचे आहे", whatTrue: "खरी माहिती काय आहे",
  warning: "या संदेशातील धोक्याची चिन्हे",
  checkedMessage: "तुमचा संदेश, तपासणीनंतर",
  claimsChecked: "तपासलेले दावे",
  sources: (n) => `${n} स्रोत`,
  showProof: (n) => `पुरावा पाहा (${n} स्रोत)`,
  hideProof: "पुरावा लपवा",
  noProof: "दाखवण्याजोगा भक्कम स्रोत सापडला नाही.",
  howChecked: "आम्ही कसे तपासले",
  searchCount: (n) => `${n} शोध`,
  pageCount: (n) => (n === 1 ? "1 पान वाचले" : `${n} पाने वाचली`),
  seconds: (t) => `${t} सेकंद`,
  stance_refutes: "हे चुकीचे असल्याचे सांगतो", stance_supports: "याची पुष्टी करतो", stance_context: "पार्श्वभूमी",
  samePage: "तुम्ही पाठवलेले पान",
  openSource: "स्रोत उघडा",
  listen: "ऐका", stop: "थांबवा", share: "शेअर करा", copy: "कॉपी करा", copied: "कॉपी झाले",
  tl_was: "तेव्हा खरे होते", tl_changed: "बदलले", tl_today: "आज",
  cached: (n) => `आधी तपासले आहे, ${n} वेळा विचारले गेले`,
  health: "हा वैद्यकीय सल्ला नाही. कोणत्याही आजारासाठी डॉक्टरांना भेटा.",
  withdrawn: (label) => `AI चे पहिले उत्तर “${label}” होते, पण त्याच्याकडे भक्कम स्रोत नव्हता, म्हणून आम्ही याची खात्री देत नाही.`,
  noClaimsTitle: "यात तपासण्यासारखे काही नाही",
  error: "काहीतरी चुकले. कृपया पुन्हा प्रयत्न करा.", retry: "पुन्हा प्रयत्न करा", more: "आणखी दाखवा",
  fallback: "आमची मुख्य तपासणी यंत्रणा व्यस्त होती, त्यामुळे हे उत्तर कमी स्रोतांवर आधारित आहे.",
  readImage: "आम्ही हे वाचले", readAudio: "आम्ही हे ऐकले",
  shareTitle: "योग्य माहिती शेअर करा",
  shareHint: "ज्या ग्रुपमधून हा संदेश आला तिथेच हे पाठवा.",
  download: "चित्र डाउनलोड करा", shareSend: "शेअर करा",
  sc_said: "संदेशात म्हटले होते", sc_sources: "स्रोत", sc_footer: "पुढे पाठवण्याआधी तपासा.",
  sc_checked: (d) => `${d} रोजी तपासले`,
};

const STRINGS = { en, hi, mr };
const LOCALES = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

export const VERDICTS = ["VERIFIED", "FALSE", "OUTDATED", "PARTLY_SUPPORTED", "UNVERIFIABLE"];

// The language to draw interface text in; anything we have no strings for falls back to English.
export function uiLang(code) {
  return STRINGS[code] ? code : "en";
}

export function t(lang, key, ...args) {
  const value = STRINGS[uiLang(lang)][key] ?? en[key];
  if (value === undefined) return key;
  return typeof value === "function" ? value(...args) : value;
}

// Dates arrive as YYYY, YYYY-MM or YYYY-MM-DD; show exactly as much as the source knew.
export function formatDate(text, lang) {
  const match = /^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?/.exec(text || "");
  if (!match) return text || "";
  const [, year, month, day] = match;
  if (!month) return year;
  const date = new Date(Date.UTC(+year, +month - 1, day ? +day : 1));
  const options = { year: "numeric", month: "short", timeZone: "UTC", numberingSystem: "latn" };
  if (day) options.day = "numeric";
  return new Intl.DateTimeFormat(LOCALES[uiLang(lang)], options).format(date);
}

// A Date as YYYY-MM-DD in the reader's own time zone (toISOString would give the UTC day).
export function localDay(date = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function formatTime(date, lang) {
  return new Intl.DateTimeFormat(LOCALES[uiLang(lang)], { hour: "numeric", minute: "2-digit", numberingSystem: "latn" }).format(date);
}

// Fill every element marked data-i18n / data-i18n-aria / data-i18n-title / data-i18n-placeholder.
export function applyStatic(lang, root = document) {
  for (const el of root.querySelectorAll("[data-i18n]")) el.textContent = t(lang, el.dataset.i18n);
  for (const el of root.querySelectorAll("[data-i18n-aria]")) el.setAttribute("aria-label", t(lang, el.dataset.i18nAria));
  for (const el of root.querySelectorAll("[data-i18n-title]")) el.title = t(lang, el.dataset.i18nTitle);
  for (const el of root.querySelectorAll("[data-i18n-placeholder]")) el.placeholder = t(lang, el.dataset.i18nPlaceholder);
  if (root === document) document.documentElement.lang = uiLang(lang);
}
