import re
import json
from collections import OrderedDict

# ============================================================
# ГОЛОВНІ СЛОВНИКИ (згідно з вашими правилами)
# ============================================================

VOWELS = OrderedDict([
    ('yeon', 'йон'),
    ('yeo', 'йо'), ('ye', 'є'), ('yo', 'йо'), ('yu', 'ю'), ('ya', 'я'),
    ('young', 'йон'), ('yong', 'йон'),
    ('yae', 'йя'), ('yi', 'і'), ('yoo', 'ю'), ('you', 'ю'),
    ('woon', 'ун'), ('woo', 'у'), ('yung', 'ьон'),
    ('wa', 'ва'), ('wae', 'ве'), ('wo', 'во'), ('we', 'ве'),
    ('wi', 'ві'), ('ui', 'і'),  # ← виправлено з 'ий'
    ('eu', 'и'), ('eo', 'о'),
    ('eon', 'он'),
    ('ae', 'е'), ('oe', 'ве'), ('oo', 'у'), ('um', 'ом'), ('ee', 'і'),
    ('a', 'а'), ('o', 'о'), ('u', 'у'), ('e', 'е'), ('i', 'і'),
    # Додано згідно з системою Концевича
    ('jho', 'чо'),
    ('ul', 'оль'),
    ('yea', 'є'),
    ('eui', 'і'),
    ('uk', 'ук'),  # ← виправлено з 'ок'
    ('ub', 'оп'),
    ('up', 'оп'),
    ('yun', 'юн'),  # ← виправлено з 'юн'
    ('joo', 'джу'),
    ('yul', 'ьоль'),  # ← додано
    ('tae', 'те'),  # ← додано
    ('seong', 'сон'),  # ← додано
    ('hui', 'хі'),  # ← додано
    ('ju', 'джу'),  # ← додано
])

INITIAL_CONSONANTS = {
    'g': 'к', 'kk': 'кк', 'k': 'к',
    'd': 'т', 'tt': 'тт', 't': 'т',
    'b': 'п', 'pp': 'пп', 'p': 'п',
    'j': 'ч', 'jj': 'чч', 'ch': 'ч',
    's': 'с', 'ss': 'сс', 'h': 'х',
    'n': 'н', 'm': 'м', 'r': 'р', 'l': 'ль',
    'ng': '', 'sh': 'ш',
}

FINAL_CONSONANTS = {
    'k': 'к', 'kk': 'к', 'ks': 'кс', 'n': 'н',
    'nj': 'нч', 'nh': 'нх', 't': 'т', 'l': 'ль',
    'lg': 'лк', 'lm': 'лм', 'lb': 'лп', 'ls': 'лс',
    'lt': 'лт', 'lp': 'лп', 'lh': 'лх', 'm': 'м',
    'p': 'п', 'ps': 'пс', 's': 'т', 'ss': 'т',
    'ng': 'н', 'ch': 'т', 'h': 'т', 'r': 'р',
    'b': 'п',  # ← додано для Sang Yeob → Йоп
}

COMMON_PARTS = [
    'kim', 'lee', 'park', 'jung', 'choi', 'shin', 'ahn', 'oh', 'kwon', 'jang', 'jae',
    'han', 'hong', 'nam', 'yim', 'uhm', 'hur', 'eum', 'song', 'jeon', 'seo',
    'kang', 'yoon', 'ryu', 'lim', 'yang', 'ro', 'won', 'ko', 'go', 'jo',
    'min', 'soo', 'hyun', 'joon', 'jun', 'jin', 'sung', 'sun', 'yeon', 'hye',
    'young', 'yong', 'kyung', 'gyeong', 'hyeon', 'hyon', 'seok', 'suk',
    'seong', 'tae', 'ju', 'hui', 'joong', 'ki', 'sik', 'bong', 'bang',
    'gyeol', 'yeol',
]


def split_compound_word(word):
    word = word.lower()
    parts = []
    i = 0
    while i < len(word):
        found = False
        for part in sorted(COMMON_PARTS, key=len, reverse=True):
            if word[i:].startswith(part):
                parts.append(part)
                i += len(part)
                found = True
                break
        if not found:
            return None
    return parts


SPECIAL = {
    'choi': 'чхве', 'shin': 'шін', 'hwi': 'хві',
    'lee': 'лі', 'lim': 'лім', 'yang': 'ян', 'ryang': 'ян',
    'ro': 'но', 'ahn': 'ан', 'oh': 'о', 'park': 'пак',
    'kim': 'кім', 'kwon': 'квон', 'won': 'вон', 'jang': 'чан',
    'han': 'хан', 'hong': 'хон', 'nam': 'нам',
    'yim': 'ім', 'uhm': 'ом', 'hur': 'хо', 'eum': 'им',
    'kwang': 'кван', 'noh': 'но', 'taec': 'тек',
    'jeong': 'чон', 'jong': 'чон', 'jung': 'чон',
    'jeon': 'чон', 'jun': 'джун', 'joon': 'джун',
    'joong': 'джун', 'jin': 'джін','suk': 'сок',
    'hyun': 'хьон', 'hyuk': 'хьок', 'hyoung': 'хьон',
    'hye': 'хє', 'kye': 'кє',
    'sung': 'сон', 'sun': 'сон', 'soon': 'сун',
    'woong': 'ун', 'gun': 'ґон', 'bum': 'бом', 'yul':'юль',
    'chung': 'чон',
    'ki': 'кі', 'gi': 'кі',
    'si': 'ші', 'sik': 'шік', 'ah': 'а',
    'jho': 'чо', 'dong':'дон', 'do':'до', 'byung':'бьон','krystal':'крістал',
    # ========== ВИНЯТКИ З ТАБЛИЦІ ==========
    'park ji hoon': 'пак джі хун',
    'park jae bum': 'пак дже бом',
    'park ji min': 'пак джі мін',
    'park bong sub': 'пак бон соп',
    'han ji min': 'хан чі мін',
    'bang si hyuk': 'бан ші хьок',  # ← виняток: Бан, а не Пан
    'seong huiju': 'сон хі джу',
    'jo yun hee': 'чо йон хі',
    'lee sang yeob': 'лі сан йоп',
    'jeon kwang ryul': 'чон кван рьоль',
    'seo in guk': 'со ін ґук',
    'ok jin uk': 'ок джін ук',
    'min hyo gi': 'мін хьо ґі',
    'shim dal gi': 'шім даль ґі',
    'min yoon gi': 'мін юн ґі',
}

CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ґ': 'g',
    'д': 'd', 'е': 'e', 'є': 'ye', 'ж': 'zh', 'з': 'z',
    'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y',
    'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya',
    'А': 'a', 'Б': 'b', 'В': 'v', 'Г': 'g', 'Ґ': 'g',
    'Д': 'd', 'Е': 'e', 'Є': 'ye', 'Ж': 'zh', 'З': 'z',
    'И': 'y', 'І': 'i', 'Ї': 'yi', 'Й': 'y',
    'К': 'k', 'Л': 'l', 'М': 'm', 'Н': 'n',
    'О': 'o', 'П': 'p', 'Р': 'r', 'С': 's', 'Т': 't',
    'У': 'u', 'Ф': 'f', 'Х': 'h', 'Ц': 'ts', 'Ч': 'ch',
    'Ш': 'sh', 'Щ': 'shch', 'Ь': '', 'Ю': 'yu', 'Я': 'ya',
}


def fix_cyrillic_input(text):
    return ''.join(CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)


def split_into_syllables(word):
    word = word.lower()
    if word in SPECIAL:
        return [(word, '', '')]
    parts = split_compound_word(word)
    if parts and len(parts) > 1:
        return [(part, '', '') for part in parts]
    syllables = []
    while word:
        best_vowel = None
        best_pos = len(word)
        best_len = 0
        for vowel in VOWELS:
            pos = word.find(vowel)
            if pos != -1:
                if pos < best_pos or (pos == best_pos and len(vowel) > best_len):
                    best_pos = pos
                    best_vowel = vowel
                    best_len = len(vowel)
        if best_vowel is None:
            syllables.append((word, '', ''))
            break
        initial = word[:best_pos]
        rest_after_vowel = word[best_pos + best_len:]
        next_vowel_pos = len(rest_after_vowel)
        for vowel in VOWELS:
            pos2 = rest_after_vowel.find(vowel)
            if pos2 != -1 and pos2 < next_vowel_pos:
                next_vowel_pos = pos2
        final = rest_after_vowel[:next_vowel_pos]
        word = rest_after_vowel[next_vowel_pos:]
        syllables.append((initial, best_vowel, final))
    return syllables


def get_final_sound(orig):
    s = orig.lower()
    if s.endswith('ng'):
        return 'ng'
    return s[-1] if s else ''


def is_sonorant(char):
    return char in ('n', 'm', 'ng', 'l')


def get_final_trans(final, rules):
    if not final:
        return ''
    if final in rules['final']:
        return rules['final'][final]
    for i in range(len(final), 0, -1):
        sub = final[-i:]
        if sub in rules['final']:
            return rules['final'][sub]
    return final[-1]


def apply_vowel_softening(vowel, vowel_trans, initial, prev_orig):
    if vowel in ('ye', 'yeo', 'yo'):
        if not initial:
            return 'є' if vowel == 'ye' else 'йо'
        else:
            return 'е' if vowel == 'ye' else 'ьо'
    elif vowel == 'ui':
        if not initial or initial in ('n', 'm', 'l') or (
                prev_orig and (prev_orig[-1] in 'aeiouy' or prev_orig.endswith('ng') or prev_orig[-1] in 'nml')):
            return 'і'
        else:
            return 'ий'
    return vowel_trans


# ============================================================
# НОВА ЛОГІКА ОЗВОНЧЕННЯ (згідно з вашими правилами)
# ============================================================

def apply_voicing(initial, prev_orig):
    """
    Визначає, чи потрібно озвончити початкову приголосну,
    і повертає правильний варіант.
    Згідно з вашими правилами + система Концевича.
    """
    # Якщо немає попереднього слова — це початок, не озвончуємо
    if not prev_orig:
        return False, None

    # Отримуємо останній звук попереднього слова
    last_sound = get_final_sound(prev_orig)

    # Перевіряємо, чи попередній звук є голосним або сонорним
    is_sonorant_or_vowel = is_sonorant(last_sound) or last_sound in 'aeiouy'

    # ============================================================
    # ВАШІ АВТОРСЬКІ ПРАВИЛА ДЛЯ ІМЕН
    # ============================================================

    # 1. ㅈ (j) → завжди дж в іменах (крім початку слова)
    if initial == 'j':
        return True, 'дж'  # завжди дж (крім початку, який ми вже відкинули)

    # 2. ㅂ (b) → завжди б в іменах (крім початку слова)
    if initial == 'b':
        return True, 'б'  # завжди б (крім початку)

    # 3. ㄱ (g/k) → за системою Концевича
    if initial in ('g', 'k'):
        if is_sonorant_or_vowel:
            return True, 'ґ'
        return False, None

    # 4. ㄷ (d/t) → за системою Концевича
    if initial in ('d', 't'):
        if is_sonorant_or_vowel:
            return True, 'д'
        return False, None

    # 5. ㄹ (r/l) → за системою Концевича
    if initial in ('r', 'l'):
        if is_sonorant_or_vowel:
            return True, 'р'
        return False, None

    # Інші приголосні не озвончуються
    return False, None


# ============================================================
# ГОЛОВНА ФУНКЦІЯ ТРАНСЛІТЕРАЦІЇ
# ============================================================

def transliterate(text, rules=None):
    base_rules = {
        'vowels': VOWELS,
        'initial': INITIAL_CONSONANTS,
        'final': FINAL_CONSONANTS,
        'special': SPECIAL
    }
    if rules:
        for key in base_rules:
            if key in rules:
                base_rules[key].update(rules[key])
    rules = base_rules

    fixed_text = fix_cyrillic_input(text).replace('-', ' ')
    full_lower = fixed_text.lower().strip()

    if full_lower in rules['special']:
        return ' '.join(word.capitalize() for word in rules['special'][full_lower].split())

    parts = fixed_text.strip().split()
    if not parts:
        return ''

    result_parts = []
    prev_orig = ''

    for part in parts:
        if not re.match(r'^[a-zA-Z]+$', part):
            result_parts.append(part)
            prev_orig = part
            continue

        word_lower = part.lower()

        if word_lower in rules['special']:
            trans = rules['special'][word_lower]
            result_parts.append(trans)
            prev_orig = word_lower
            continue

        syllables = split_into_syllables(word_lower)

        # ========== ЛОГІКА ДЛЯ ДВОСКЛАДОВИХ ІМЕН ==========
        if len(syllables) > 1 and all(init and not vowel and not final for init, vowel, final in syllables):
            trans_parts = []
            for init, _, _ in syllables:
                trans_part = transliterate(init, rules)
                trans_parts.append(trans_part)
            result_parts.append(' '.join(trans_parts))
            prev_orig = word_lower
            continue
        # ===================================================

        trans_syllables = []

        for initial, vowel, final in syllables:
            if initial and not vowel and not final:
                trans_part = transliterate(initial, rules)
                trans_syllables.append(trans_part)
                prev_orig = initial
                continue

            orig_syllable = initial + vowel + final

            vowel_trans = rules['vowels'].get(vowel, vowel)
            vowel_trans = apply_vowel_softening(vowel, vowel_trans, initial, prev_orig)

            initial_trans = rules['initial'].get(initial, initial)

            # ========== ЛОГІКА ДЛЯ si* ==========
            if initial == 's' and vowel and vowel.startswith('i'):
                initial_trans = 'ш'
            # ===================================

            # ========== НОВА ЛОГІКА ОЗВОНЧЕННЯ ==========
            voiced, voiced_trans = apply_voicing(initial, prev_orig)
            if voiced and voiced_trans:
                initial_trans = voiced_trans
            # ===========================================

            final_trans = get_final_trans(final, rules)

            syllable_trans = initial_trans + vowel_trans + final_trans
            trans_syllables.append(syllable_trans)

            prev_orig = orig_syllable

        result_parts.append(''.join(trans_syllables))

    final_result = ' '.join(result_parts)
    words = final_result.split()
    capitalized = []
    for w in words:
        if w and w[0].isalpha():
            capitalized.append(w[0].upper() + w[1:])
        else:
            capitalized.append(w)
    return ' '.join(capitalized)


# ============================================================
# ТЕСТУВАННЯ
# ============================================================

def main():
    print("\n=== Транслітератор (система Концевича + авторські правила) ===\n")


    print("\nВведіть ім'я латиницею (або 'exit' для виходу):")
    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ('exit', 'quit', ''):
            break
        if not user_input:
            continue
        result = transliterate(user_input)
        print(f"→ {result}\n")


if __name__ == "__main__":
    main()
