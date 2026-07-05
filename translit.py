import re
import json
from collections import OrderedDict

# ======== ВБУДОВАНІ ПРАВИЛА ========

VOWELS = OrderedDict([
    ('yeo', 'йо'), ('ye', 'є'), ('yo', 'йо'), ('yu', 'ю'), ('ya', 'я'),     ('young', 'йон'),
    ('yong', 'йон'),
    ('woon', 'ун'), ('woo', 'у'), ('yung', 'ьон'),
    ('yae', 'йя'), ('yi', 'і'), ('yoo', 'ю'), ('you', 'ю'),
    ('wa', 'ва'), ('wae', 'ве'), ('wo', 'во'), ('we', 'ве'),
    ('wi', 'ві'), ('ui', 'ий'), ('eu', 'и'), ('eo', 'о'),
    ('ae', 'е'), ('oe', 'ве'), ('oo', 'у'), ('um', 'ом'), ('ee', 'і'),
    ('a', 'а'), ('o', 'о'), ('u', 'у'), ('e', 'е'), ('i', 'і'),
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
    'ng': 'н', 'ch': 'т', 'h': 'т','r': 'р'
}

# ======== СПЕЦІАЛЬНІ ВИПАДКИ (згідно з вашими правилами) ========
SPECIAL = {
    'hyoung': 'хьон',
    'choi': 'чхве',
    'uhm': 'ом',
    'shin': 'шін',
    'hwi': 'хві',
    'lee': 'лі',
    'lim': 'лім',
    'yang': 'ян',
    'ryang': 'ян',
    'ro': 'но',
    'jong': 'чон',
    'jung': 'чон',
    'jun': 'джун',        # нове правило
    'joon': 'джун',       # нове правило
    'joong': 'джун',      # нове правило
    'jeon': 'чон',
    'ahn': 'ан',
    'oh': 'о',
    'park': 'пак',
    'kim': 'кім',
    'kwon': 'квон',
    'won': 'вон',
    'jang': 'чан',
    'han': 'хан',
    'hong': 'хон',
    'nam': 'нам',
    'jin': 'джін',        # завжди Джін
    'sun': 'сон',
    'sung': 'сон',        # прізвище Сон
    'kye': 'кє',          # виняток для Kye
    'hye': 'хє',  # ДОДАТИ
    'hyun': 'хьон',  # ДОДАТИ (для впевненості)
    'hyuk': 'хьок',
    # ===== Окремі склади-винятки =====
    'si': 'ші',           # s+i → ші (але автоматика це вже робить, можна прибрати)
    'sik': 'шік',         # аналогічно
    'ah': 'а',            # ah → а
    # ===== Винятки для озвончення (якщо автоматика не спрацьовує) =====
    # Залишаємо тільки ті, які дійсно потрібні
    'je': 'дже',
    'ju': 'джу',
    'jo': 'джо',
    'ja': 'джа',
    'jye': 'джє',
    'jyo': 'дьо',
    'dae': 'де',
    'de': 'де',
    'di': 'ді',
    'du': 'ду',
    'do': 'до',
    'da': 'да',
    'bye': 'бє',
    'bi': 'бі',
    'bu': 'бу',
    'bo': 'бо',
    'ba': 'ба',
    'be': 'бе',
}

# ======== ВИПРАВЛЕННЯ РОЗКЛАДКИ ========

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

# ======== РОЗБИТТЯ НА СКЛАДИ (ВИПРАВЛЕНЕ) ========

def split_into_syllables(word):
    """
    Розбиває слово на склади, знаходячи найдовшу голосну на кожній позиції.
    Повертає список (initial, vowel, final).
    """
    word = word.lower()
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

# ======== ДОПОМІЖНІ ФУНКЦІЇ ========

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
        if not initial or initial in ('n', 'm', 'l') or (prev_orig and (prev_orig[-1] in 'aeiouy' or prev_orig.endswith('ng') or prev_orig[-1] in 'nml')):
            return 'і'
        else:
            return 'ий'
    return vowel_trans

# ======== ГОЛОВНА ФУНКЦІЯ ========

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
    parts = fixed_text.strip().split()
    if not parts:
        return ''

    result_parts = []
    prev_orig = ''  # Глобальний для всього тексту, не скидається між словами

    for part in parts:
        if not re.match(r'^[a-zA-Z]+$', part):
            result_parts.append(part)
            prev_orig = part
            continue

        word_lower = part.lower()

        # Спеціальний випадок для цілого слова
        if word_lower in rules['special']:
            trans = rules['special'][word_lower]
            result_parts.append(trans)
            prev_orig = word_lower  # запам'ятовуємо оригінал для озвончення наступного
            continue

        syllables = split_into_syllables(word_lower)
        trans_syllables = []

        for initial, vowel, final in syllables:
            orig_syllable = initial + vowel + final

            vowel_trans = rules['vowels'].get(vowel, vowel)
            vowel_trans = apply_vowel_softening(vowel, vowel_trans, initial, prev_orig)

            # Початкова приголосна (базова)
            initial_trans = rules['initial'].get(initial, initial)
            if initial == 'j' and vowel == 'i':
                initial_trans = 'дж'
            elif initial == 'j' and vowel in ('u', 'oo'):
                initial_trans = 'джу'
            # Спецправило: s + i -> ші
            if initial == 's' and vowel == 'i':
                initial_trans = 'ш'

            # ========== ОЗВОНЧЕННЯ ДЛЯ g, k, d, b, j ==========
            voiced = False
            if prev_orig:
                last_sound = get_final_sound(prev_orig)
                if is_sonorant(last_sound) or last_sound in 'aeiouy':
                    if initial in ('g', 'd', 'b', 'j', 'k'):   # додано 'k'
                        voiced = True
                    if initial in ('r', 'l') and (last_sound in 'aeiouy' or is_sonorant(last_sound)):
                        voiced = True
            if voiced:
                voiced_map = {
                    'g': 'ґ',
                    'k': 'ґ',    # додано для k
                    'd': 'д',
                    'b': 'б',
                    'j': 'дж',
                    'r': 'р',
                    'l': 'р'
                }
                initial_trans = voiced_map.get(initial, initial_trans)
            # =================================================

            final_trans = get_final_trans(final, rules)

            syllable_trans = initial_trans + vowel_trans + final_trans
            trans_syllables.append(syllable_trans)

            # Запам'ятовуємо оригінальний склад для наступного
            prev_orig = orig_syllable

        result_parts.append(''.join(trans_syllables))

    # Капіталізація
    final_result = ' '.join(result_parts)
    words = final_result.split()
    capitalized = []
    for w in words:
        if w and w[0].isalpha():
            capitalized.append(w[0].upper() + w[1:])
        else:
            capitalized.append(w)
    return ' '.join(capitalized)

# ======== ЗАВАНТАЖЕННЯ ЗОВНІШНІХ ПРАВИЛ ========

def load_rules_from_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Файл '{filepath}' не знайдено. Використовуються тільки вбудовані правила.")
        return None
    except json.JSONDecodeError:
        print(f"Помилка формату JSON у файлі '{filepath}'. Використовуються тільки вбудовані правила.")
        return None

# ======== ГОЛОВНА ПРОГРАМА ========

def main():
    RULES_FILE = 'rules.json'
    external_rules = load_rules_from_file(RULES_FILE)
    if external_rules:
        print(f"Додаткові правила завантажено з {RULES_FILE}")
    else:
        print("Використовуються вбудовані правила.")

    print("\n=== Транслітерація корейських імен (латиниця -> українська) ===")
    print("Введіть ім'я або назву латиницею (напр. 'Kim Soo Hyun').")
    print("Для виходу введіть 'exit' або 'quit'.\n")

    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ('exit', 'quit', ''):
            break
        if not user_input:
            continue
        result = transliterate(user_input, external_rules)
        print(f"→ {result}\n")

if __name__ == "__main__":
    main()