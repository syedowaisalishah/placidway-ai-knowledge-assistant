"""Local query analysis. Raw visitor messages never enter the Gemini request."""

import re
import unicodedata
from dataclasses import dataclass, field


def normalize(text: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(c)
    )


TOPICS = {
    "adenocarcinoma": [
        "adenocarcinoma",
        "adenocarcinomas",
        "السرطان الغدي",
        "سرطان غدي",
        "الغدية",
        "غدي",
    ],
    "adrenal cancer": ["adrenal", "suprarrenal", "الكظر", "كظري"],
    "anal cancer": [
        "anal cancer",
        "anal package",
        "anal treatment",
        "cancer anal",
        "سرطان الشرج",
        "الشرج",
    ],
    "breast cancer": ["breast cancer", "cancer de mama", "سرطان الثدي"],
    "prostate cancer": ["prostate cancer", "cancer de prostata", "سرطان البروستاتا"],
    "lung cancer": ["lung cancer", "cancer de pulmon", "سرطان الرئة"],
    "pancreatic cancer": ["pancreatic cancer", "cancer de pancreas", "سرطان البنكرياس"],
    "colorectal cancer": ["colorectal", "القولون والمستقيم"],
    "colon cancer": ["colon cancer", "cancer de colon", "سرطان القولون"],
    "ozone therapy": ["ozone", "ozono", "الاوزون", "اوزون"],
    "acupuncture": ["acupuncture", "acupuntura", "الوخز", "الابر"],
    "ayurvedic panchakarma": ["panchakarma", "ayurved", "ayurvedic"],
    "stem cell therapy": [
        "stem cell",
        "celulas madre",
        "خلايا جذعية",
        "الخلايا الجذعية",
    ],
    "live cell therapy": ["live cell"],
    "naturopathic wellness": ["naturopathic", "naturopatia"],
    "ITC": ["itc", "immunity therapy", "inmunidad", "العلاج المناعي"],
    "alternative medicine": [
        "alternative medicine",
        "medicina alternativa",
        "الطب البديل",
    ],
}
COUNTRIES = {
    "Mexico": ["mexico", "tijuana", "المكسيك", "تيخوانا", "zapopan", "puebla"],
    "Turkey": ["turkey", "turkiye", "turquia", "تركيا", "konya"],
    "Thailand": ["thailand", "tailandia", "تايلاند", "bangkok"],
    "USA": [
        "united states",
        "usa",
        "united states of america",
        "estados unidos",
        "الولايات المتحدة",
    ],
    "India": ["india", "الهند"],
    "Spain": ["spain", "espana", "اسبانيا"],
    "Germany": ["germany", "alemania", "المانيا"],
    "Canada": ["canada", "كندا"],
    "Brazil": ["brazil", "brasil", "البرازيل"],
    "Pakistan": ["pakistan", "باكستان"],
    "Japan": ["japan", "japon", "اليابان"],
    "China": ["china", "الصين"],
    "UAE": ["uae", "dubai", "united arab emirates", "دبي", "الامارات"],
    "UK": ["uk", "united kingdom", "britain", "england", "london", "المملكة المتحدة"],
    "France": ["france", "francia", "paris", "فرنسا"],
    "Colombia": ["colombia", "كولومبيا"],
    "Australia": ["australia", "استراليا"],
    "South Korea": ["south korea", "seoul", "كوريا الجنوبية"],
    "Costa Rica": ["costa rica", "كوستاريكا"],
    "Egypt": ["egypt", "cairo", "مصر"],
    "Saudi Arabia": ["saudi arabia", "السعودية"],
    "Poland": ["poland", "polonia", "بولندا"],
    "Hungary": ["hungary", "hungria", "المجر"],
    "Singapore": ["singapore", "سنغافورة"],
}
CLINICS = {
    "ITC": ["itc", "immunity therapy"],
    "Fizikon": ["fizikon"],
    "Stem Health": ["stem health"],
    "VISANI": ["visani"],
    "Form Recovery": ["form recovery"],
}
ASPECTS = {
    "flights": ["flight", "airfare", "vuelo", "طيران"],
    "accommodation": [
        "hotel",
        "accommodation",
        "room",
        "lodging",
        "alojamiento",
        "اقامة",
        "فندق",
    ],
    "meals": ["meal", "food", "nutrition", "comida", "وجبات"],
    "medications": ["medication", "drug", "medicine included", "medicamento", "ادوية"],
    "imaging": ["scan", "imaging", "x-ray", "اشعة"],
    "lab work": ["lab", "blood test", "laboratorio", "تحاليل"],
    "insurance": ["insurance", "seguro medico", "تأمين", "تامين"],
    "refund": ["refund", "cancel", "reembolso", "استرداد"],
    "visa": ["visa", "تاشيرة"],
    "contact": ["phone number", "email address", "telephone", "telefono", "رقم الهاتف"],
    "chemotherapy": ["chemotherapy", "chemo", "quimioterapia", "كيميائي"],
    "radiation": ["radiation", "radiotherapy", "radioterapia", "اشعاعي"],
    "surgery": ["surgery", "surgical", "cirugia", "جراحة"],
    "emergency": ["emergency", "ambulance", "emergencia", "اسعاف"],
    "approval": [
        "fda",
        "approved",
        "approval",
        "accreditation",
        "accredited",
        "license",
        "certified",
    ],
}
INTENT_TERMS = {
    "pricing": [
        "cost",
        "price",
        "prices",
        "pricing",
        "how much",
        "cuanto",
        "precio",
        "costo",
        "تكلفة",
        "سعر",
        "اسعار",
        "بكم",
        "تكلف",
    ],
    "inclusions": [
        "includ",
        "inclusion",
        "incluy",
        "incluid",
        "يشمل",
        "تشمل",
        "يتضمن",
        "باقة",
        "باقة",
    ],
    "recovery": [
        "recovery",
        "recover",
        "recupera",
        "التعافي",
        "تعافي",
        "recovery time",
    ],
    "duration": [
        "duration",
        "how long",
        "weeks",
        "duracion",
        "cuanto tiempo",
        "مدة",
        "اسابيع",
    ],
    "doctors": [
        "doctor",
        "physician",
        "bautista",
        "medical director",
        "medico",
        "طبيب",
        "اطباء",
    ],
    "location": [
        "where",
        "location",
        "address",
        "located",
        "donde",
        "ubicacion",
        "اين",
        "موقع",
        "عنوان",
    ],
    "videos": ["video", "testimonial", "review", "فيديو", "تجارب", "resena"],
    "treatments": [
        "treatments",
        "therapies",
        "offer",
        "treat",
        "tratamiento",
        "علاجات",
        "علاج",
    ],
    "languages": ["language", "bilingual", "spanish speaking", "idioma", "لغة", "لغات"],
    "aftercare": [
        "aftercare",
        "follow-up",
        "follow up",
        "post-discharge",
        "seguimiento",
        "متابعة",
    ],
    "exclusions": [
        "excluded",
        "not included",
        "extra cost",
        "adicional",
        "غير مشمول",
        "غير شامل",
    ],
}


@dataclass
class Query:
    intent: str = "overview"
    topic: str = ""
    topics: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    clinic: str = ""
    program: str = ""
    language: str = "en"
    block: str = ""
    followup: bool = False
    false_premise: bool = False
    aspect: str = ""

    @property
    def safe_description(self) -> str:
        # Every value originates in a fixed vocabulary, never arbitrary user content.
        return f"{self.intent}; {self.topic or 'ITC'}; {', '.join(self.countries)}; {self.clinic}; {self.program}; {self.aspect}"

    @property
    def retrieval_text(self) -> str:
        intent = {
            "inclusions": "included program lab work meals imaging medications",
            "recovery": "recovery time after treatment",
            "duration": "program duration weeks",
            "treatments": "treatments offered therapies",
            "aftercare": "follow-up after discharge",
            "exclusions": "excluded services additional costs",
            "pricing": "cost price USD program",
            "location": "location address Tijuana",
            "doctors": "doctors medical director",
            "languages": "bilingual English Spanish",
            "videos": "video titles experiences",
        }.get(self.intent, self.intent)
        return f"{self.topic or 'ITC Immunity Therapy Center'} {intent} {' '.join(self.countries)} {self.program} {self.aspect}"


def analyze(
    message: str, previous: dict | None = None, language: str | None = None
) -> Query:
    text = normalize(message)
    language = language or (
        "ar"
        if re.search(r"[\u0600-\u06ff]", message)
        else "es"
        if re.search(
            r"\b(cuanto|precio|incluye|tratamiento|puedes|recuperacion|costo|donde|hola|buenos dias|buenas tardes|buenas noches)\b",
            text,
        )
        else "en"
    )
    query = Query(language=language)
    if re.search(
        r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\+?\d[\d\s().-]{8,}\d|\b(my name is|me llamo|mi nombre|اسمي)\b",
        text,
    ):
        query.block = "privacy"
        return query
    personal = r"\b(i have|i was diagnosed|my (?:diabetes|cancer|condition|symptoms|mother|father|wife|husband)|for me|should i|can i take|is it safe for me|my medical|tengo|mi diabetes|mi cancer|para mi)\b|لدي|حالتي|اعاني|هل يناسبني|مرض السكري لدي"
    if re.search(personal, text):
        query.block = "medical_safety"
        return query
    if re.search(
        r"ignore.{0,40}(instruct|rules|previous)|system prompt|api.?key|credential|pretend|invent|make up|act as my doctor|bypass|jailbreak|ignore las|تجاهل.{0,20}(تعليمات|قواعد)",
        text,
    ):
        query.block = "out_of_scope"
        return query
    # Social openers are not knowledge requests. Match the whole message so
    # "Hi, what does the package cost?" still reaches the grounded price path.
    if re.fullmatch(
        r"\s*(?:hi|hi there|hey|hello|hello there|good morning|good afternoon|good evening|hola|buenos dias|buenas tardes|buenas noches|مرحبا|اهلا|أهلا|السلام عليكم|صباح الخير|مساء الخير)[!?.،\s]*",
        text,
    ):
        query.intent = "greeting"
        return query
    if re.search(
        r"\b(book|schedule|reserve|appointment tomorrow|reservar|cita manana)\b|احجز|حجز موعد",
        text,
    ):
        query.intent = "booking"
        return query
    if re.search(
        r"\b(quote|contact|cotizacion|presupuesto|contactar)\b|عرض سعر|التواصل", text
    ):
        query.intent = "quote"
        return query
    if re.search(
        r"\b(weather|bitcoin|stock market|football|recipe|poem|clima|tiempo en cancun)\b|الطقس|كرة القدم",
        text,
    ):
        query.block = "out_of_scope"
        return query
    if re.search(
        r"convert|exchange rate|\bpkr\b|currency conversion|tipo de cambio|سعر الصرف|تحويل العملة",
        text,
    ):
        query.block = "out_of_scope"
        return query
    if re.search(
        r"\b(cure|guarantee|success rate|survival rate|safe|effective|safety|proven|curar|cura|seguro)\b|شفاء|مضمون|امن|نسبة النجاح",
        text,
    ):
        query.block = "medical_safety"
        return query
    query.topics = [
        topic
        for topic, aliases in TOPICS.items()
        if any(alias in text for alias in aliases)
    ]
    # ITC is a clinic context, not a second requested treatment.
    treatments = [t for t in query.topics if t not in ("ITC", "alternative medicine")]
    query.topic = (
        treatments[0] if treatments else (query.topics[0] if query.topics else "")
    )
    if len(treatments) > 1:
        query.block = "multiple_treatments"
        return query
    query.countries = [
        country
        for country, aliases in COUNTRIES.items()
        if any(
            re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text)
            for alias in aliases
        )
    ]
    query.clinic = next(
        (
            clinic
            for clinic, aliases in CLINICS.items()
            if any(alias in text for alias in aliases)
        ),
        "",
    )
    query.aspect = next(
        (
            aspect
            for aspect, aliases in ASPECTS.items()
            if any(
                re.search(r"(?<!\w)" + re.escape(alias) + r"(?:s)?(?!\w)", text)
                for alias in aliases
            )
        ),
        "",
    )
    # Avoid carrying package context into a clearly new unsupported treatment/clinic.
    unsupported = r"dental|implant|rhinoplasty|hair transplant|hip replacement|knee replacement|ivf|fertility|bariatric|gastric|mayo clinic|cleveland clinic|johns hopkins|diente|implante|اسنان|زراعة الشعر"
    if re.search(unsupported, text):
        query.block = "unsupported_topic"
        return query
    # Unrecognized explicit destinations and providers must not silently become
    # Mexico/ITC. Preserve only known vocabulary; never send the raw entity to AI.
    place = re.search(r"\bin\s+([a-z][a-z -]*?)(?:[?.!,]|$)", text)
    if place and not query.countries:
        phrase = place.group(1).strip()
        if not re.match(r"(?:the |a |an |this |that |itc\b|an?d?\b)", phrase):
            query.block = "unsupported_topic"
            return query
    provider = re.search(r"\b(?:at|by)\s+([a-z][a-z -]*?)(?:[?.!,]|$)", text)
    if (
        provider
        and not query.clinic
        and re.search(r"clinic|hospital|center|centre", provider.group(1))
    ):
        query.block = "unsupported_topic"
        return query
    query.false_premise = bool(
        re.search(r"\b(confirm|heard|is it true)\b|confirmar|confirma|اكد|سمعت", text)
        and re.search(r"\d|\$", text)
    )
    query.intent = next(
        (
            intent
            for intent, terms in INTENT_TERMS.items()
            if any(term in text for term in terms)
        ),
        "overview",
    )
    # More specific question types override broad substrings such as "included"
    # inside "not included" or "treatment" inside "treatment recovery".
    for intent in ("exclusions", "aftercare", "languages", "recovery"):
        if any(term in text for term in INTENT_TERMS[intent]):
            query.intent = intent
    if re.search(
        r"cheaper|compare|comparison|less expensive|mas barato|comparar|ارخص|مقارنة",
        text,
    ):
        query.intent = "comparison"
    if query.false_premise:
        query.intent = "pricing"
    if re.search(r"out.?patient|ambulatorio", text):
        query.program = "out-patient"
    elif re.search(r"in.?patient|hospitaliz", text):
        query.program = "in-patient"
    query.followup = (
        not query.topic
        and bool(previous)
        and (
            query.intent != "overview"
            or bool(re.search(r"what about|and |it\b|that|this|y |وماذا|وما", text))
        )
    )
    if query.followup:
        query.topic = previous.get("topic", "")
        if not query.countries:
            query.countries = previous.get("countries", [])
        query.clinic = query.clinic or previous.get("clinic", "")
        query.program = query.program or previous.get("program", "")
    if query.aspect in ("insurance", "refund", "visa", "approval"):
        query.block = "unsupported_topic"
    if query.intent == "pricing" and query.aspect:
        # A package base price does not establish the price of an add-on or component.
        query.block = "unsupported_topic"
    if not query.topic and query.intent not in ("quote", "booking"):
        # Only deliberately generic website questions get the default ITC scope.
        generic = bool(
            re.fullmatch(
                r"(?:what (?:prices|treatments|videos|languages|doctors)(?: are available| do you have)?|what prices are available|where is the clinic|where is it located)[?.! ]*",
                text,
            )
        )
        if generic:
            query.topic = "ITC"
        else:
            query.block = "unsupported_topic"
    return query
