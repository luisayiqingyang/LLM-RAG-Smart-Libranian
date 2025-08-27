from __future__ import annotations
import re
import unicodedata
from typing import Tuple

POLITE_REPLY_RO = (
    "Îți răspund cu respect. Te rog să păstrăm o conversație civilizată. "
    "Dacă ai o întrebare sau cauți o recomandare, sunt aici să te ajut."
)

POLITE_REPLY_EN = (
    "I will answer you with respect. Please keep our conversation polite. "
    "If you have a question or need a recommendation, I’m here to help."
)

# --- seturi separate RO / EN, apoi uniune (util pentru detectarea limbii) ---
BAD_WORDS_RO = {
    "pula", "pizda", "muie", "futut", "fute", "dracului", "javra",
    "prost", "proasta", "idiot", "idiota", "imbecil", "tampit", "tampita",
    "cretin", "cretina", "nesimtit", "nesimtita", "bou", "dobitoc", "jigar",
    "handicapat", "handicapata", "retard", "retardat",
}
BAD_WORDS_EN = {
    "fuck", "fucking", "fucker", "motherfucker", "shit", "bitch", "bastard",
    "asshole", "dick", "cock", "pussy", "cunt", "slut",
}
BAD_WORDS = BAD_WORDS_RO | BAD_WORDS_EN

# Substituții de „leet”
LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"
})

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _normalize(text: str) -> str:
    t = (text or "").lower()
    t = _strip_accents(t)
    t = t.translate(LEET_MAP)
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)  # reduce repetări (fuuuuck -> fuuck)
    t = re.sub(r"\s+", " ", t)            # spații multiple -> unul singur
    return t.strip()

def _profanity_lang(norm_text: str) -> str:
    """Returnează 'ro' sau 'en' în funcție de limba injuriei detectate."""
    tokens = norm_text.split()

    # 1) potrivire exactă pe token
    for w in tokens:
        if w in BAD_WORDS_RO:
            return "ro"
        if w in BAD_WORDS_EN:
            return "en"

    # 2) fallback substring (ex: 'idiot!!', 'ass-hole' după normalizare)
    for bad in BAD_WORDS_RO:
        if re.search(rf"{re.escape(bad)}", norm_text):
            return "ro"
    for bad in BAD_WORDS_EN:
        if re.search(rf"{re.escape(bad)}", norm_text):
            return "en"

    # default rezonabil
    return "ro"

def polite_reply_for(text: str) -> str:
    norm = _normalize(text)
    return POLITE_REPLY_EN if _profanity_lang(norm) == "en" else POLITE_REPLY_RO

def contains_profanity(text: str) -> bool:
    norm = _normalize(text)

    # 1) verificare directă pe cuvinte
    words = norm.split()
    for w in words:
        if w in BAD_WORDS:
            return True

    # 2) fallback regex pentru forme cu simboluri sau intercalări (cr*etin, pr0st etc.)
    for bad in BAD_WORDS:
        if re.search(rf"{re.escape(bad)}", norm):
            return True

    # 3) expresii tip „esti bou/prost/cretin...”
    if re.search(
        r"\b(esti|eşti|sunt|pari|erai)\s+(foarte\s+)?"
        r"(prost|proasta|bou|cretin|cretina|idiot|idiota|imbecil|tampit|tampita|nesimtit|nesimtita|dobitoc|handicapat|handicapata|retard|retardat)\b",
        norm,
    ):
        return True

    return False

def censor(text: str) -> str:
    def mask_word(w: str) -> str:
        if len(w) <= 2:
            return "★" * len(w)
        return w[0] + "★" * (len(w) - 2) + w[-1]

    tokens = re.findall(r"\w+|\W+", text, flags=re.UNICODE)
    out = []
    for t in tokens:
        if re.search(r"\w", t) and contains_profanity(t):
            out.append(mask_word(t))
        else:
            out.append(t)
    return "".join(out)

def filter_prompt(text: str, mode: str = "block") -> Tuple[bool, str]:
    """
    mode:
      - "block": blochează complet → returnează mesaj politicos (RO/EN)
      - "censor": cenzurează și lasă să treacă la LLM
    returnează: (ok, text|mesaj)
      - ok=False → NU trimitem la LLM, returnăm direct răspunsul
      - ok=True  → text curățat (poate fi trimis la LLM)
    """
    if contains_profanity(text):
        if mode == "censor":
            return True, censor(text)
        return False, polite_reply_for(text)
    return True, text
