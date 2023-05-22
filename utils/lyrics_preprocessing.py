import re
import spacy
import pickle

"""
Списки согласных, глухих, гласных
"""
consonants = [u'б', u'в', u'г', u'д', u'ж', u'з', u'й', u'к',
u'л', u'м', u'н', u'п', u'р', u'с', u'т', u'ф', u'х', u'ц', u'ч', u'ш', u'щ', u'b', u'c', u'd', u'f', u'g', u'h', u'j', u'k', u'l', u'm', u'n', u'p', u'q', u'r', u's', u't', u'v', u'w', u'x', u'z']
thud = [u'к', u'п', u'с', u'т', u'ф', u'х', u'ц', u'ч', u'ш', u'щ']
vowels = ['а', 'у', 'о', 'ы', 'и', 'э', 'я', 'ю', 'ё', 'е', 'a', 'o', 'i', 'e', 'u', 'y', 'а́', 'о́', 'е́', 'у́', 'ё', 'и́', 'э́', 'ю́', 'я́', 'а́', 'о́', 'е́', 'у́', 'ё', 'и́', 'э́', 'ю́', 'я́']
#vowels = [u'а', u'у', u'о', u'ы', u'и', u'э', u'я', u'ю', u'ё', u'е', u'a', u'o', u'i', u'e', u'u', u'y', 'а́', 'о́', 'е́', 'у́', 'ё', 'и́', 'э́', 'ю́', 'я́', u'а́', u'о́', u'е́', u'у́', u'ё', u'и́', u'э́', u'ю́', u'я́']
accented_letters = [u'а́', u'о́', u'е́', u'у́', u'ё', u'и́', u'э́', u'ю́', u'я́']

"""
Если согласный
"""
def isconsonant(char):
    x = char.lower()[0]
    for c in consonants:
        if c == x:
            return True

"""
Если глухой
"""
def isthud(char):
    x = char.lower()[0]
    for c in thud:
        if c == x:
            return True

"""
Если гласный
"""
def isvowel(char):
    x = char.lower()[0]
    for c in vowels:
        if c == x:
            return True
    return False

"""
считает гласные
"""
def vowelcount(word):
    cnt = 0
    for c in word:
        if(isvowel(c)):
            cnt += 1
    return cnt

def split2syllables(word):
    splited = ''
    slog = ''
    i =  0
    #v = False
    if vowelcount(word) <= 1:
        return word

    # print(len(word))
    while i < len(word):
        # print(i)
        # print(splited)
        # print(word[i])
        
        # word = list(word) # new

        c = word[i]
        #добавляем букву в слог
        slog += c
        # если гласная
        if isvowel(c):
            # смотрим что идет после
            # есть буквы
            if i+1 < len(word):
                c1 = word[i+1]

                # если знак ударения
                if c1 == '́':
                    slog += word[i+1]
                    i+=1

                # если согласная
                if isconsonant(c1):
                    # если последняя в слове - добавляем в слог и выходим
                    if i+1 >= len(word) - 1:
                        slog += word[i+1]
                        i+=1
                    else:
                        # не последняя,запоминаем проверяем что идет после нее
                        c2 = word[i+2]
                        # если идет Й и следом согласный - добавляем в слог
                        if (c1 == u'й' or c1 == u'Й') and isconsonant(c2):
                            slog += c1
                            i += 1
                        # если после звонкой не парной идет глухой согласный - добавляем в слог
                        elif (c1 in [u'м',u'н',u'р',u'л'] or c1 in [u'М',u'Н',u'Р',u'Л']) and isthud(c2):
                            slog += c1
                            i += 1
                        elif i+2 >= len(word) - 1 and (c2 == u'ь' or c2 == u'Ь' or c2 == u'ъ' or c2 == u'Ъ'):
                            # заканчивается на мягкий
                            i+=2
                            slog += c1 + c2
                        # added new option
                        elif i+2 >= len(word) - 1 and isconsonant(c2):
                            i+=2
                            slog += c1 + c2                            

            splited += slog
            if i+1 < len(word):
                #splited += '-'
                if vowelcount(word[i+1:]) > 0:
                    splited += ' '
                else:
                    splited += word[i+1:]
                    break                    
            slog = ''
        i += 1
    return splited

"""
Разбивает строки на слоги
"""
def split2words(line):
    i = 0
    result = ''
    word = ''
    while i < len(line)+1:
        if i != len(line):
            c = line[i]
        if (isconsonant(c) or isvowel(c) or c == u'ь' or c == u'Ь' or c == u'ъ' or c == u'Ъ' or c == '́') and i != len(line): # new: or c == '́'
            word += c
        else:
            if len(word) > 0:
                if len(word) <= 1:
                    result += word
                else:
                    result += split2syllables(word)
                word = ''
            if i != len(line):
                result += c
        i += 1
    return result.strip()

# def split2words(line):
#     i = 0
#     result = []
#     word = ''
#     while i < len(line)+1:
#         if i != len(line):
#             c = line[i]
#         if (isconsonant(c) or isvowel(c) or c == u'ь' or c == u'Ь' or c == u'ъ' or c == u'Ъ' or c == '́') and i != len(line): # new: or c == '́'
#             word += c
#         else:
#             if len(word) > 0:
#                 if len(word) <= 2:
#                     result += [word]
#                 else:
#                     result += [split2syllables(word)]
#                 word = ''
#             if i != len(line):
#                 result += [c]
#         i += 1
#     return result

def clean(text):
    result = []
    for i, line in enumerate(text):
        line = re.sub('\\n', '', line)
        line = re.sub(r'\([^\)]+\)', '', line)
        if text[i][0] != '[' and len(line)>0:
            result.append(line)
    return result

def preprocess(lyrics, one_line=True): # вместо пути к файлу укажем массив со строчками
    result = []
    # with open(lyrics_path, 'r') as file:
    #     lyrics = file.readlines()
    lyrics = clean(lyrics)   

    for line in lyrics:
        res = split2words(line)
        #res = translit(split2words(line), reversed=True)
        result.append(res)

    if one_line:
        sep_line = ' [sep] '.join(result)
        return sep_line
    else:
        return result

# parsing the sylables
def syllable_parse(lyrics):
    result = []
    for line in lyrics:
        words = re.split(' |-', line.strip())
        #counter = 0
        line_str = '' # new
        for word in words:
            if vowelcount(word) > 0:
                # new
                if '́' in word or 'ё' in word:
                    line_str += '+'
                else:
                    line_str += '_'
                #counter += 1
        #result.append(counter * '_')
        result.append(line_str)
    return result     

# def syllable_parse(lyrics):
#     result = []
#     for line in lyrics:
#         words = line
#         #counter = 0
#         line_str = '' # new
#         for word in words:
#             word_whole = re.sub(' +', '', word)
#             if vowelcount(word_whole) > 0:
#                 if '́' in word or 'ё' in word:
#                     for syl in re.split(' |-', word.strip()):
#                         # new
#                         if '́' in syl or 'ё' in syl:
#                             line_str += '+'
#                         else:
#                             line_str += '_'
#                 else:
#                     for syl in re.split(' |-', word.strip()):
#                         line_str += '?'
#                 #counter += 1
#         #result.append(counter * '_')
#         result.append(line_str)
#     return result   

 #-------------------------------------------------------
 # Блок функций по расставлению ударений
 # Источник: https://github.com/einhornus/russian_accentuation


# Реализация русского языка для spacy на основе natasha
# Источник: https://github.com/natasha/natasha-spacy
ru_nlp = spacy.load('ru_core_news_md')


def load():
    with open(file="lemmas.dat", mode='rb') as f:
        lemmas = pickle.loads(f.read())
    with open(file="wordforms.dat", mode='rb') as f:
        wordforms = pickle.loads(f.read())
    return lemmas, wordforms


def introduce_special_cases_from_dictionary(dictionary):
    '''
    Пока что не работает: не добавляются исключения
    '''
    for word in dictionary:
        if (" " in word) or ("-" in word):
            if len(dictionary[word]) == 1:
                ru_nlp.tokenizer.add_special_case(word, [{"ORTH": dictionary[word][0]["accentuated"]}])
                ru_nlp.tokenizer.add_special_case(word.capitalize(), [{"ORTH": dictionary[word][0]["accentuated"].capitalize()}])


def compatible(interpretation, lemma, tag, lemmas):
    if lemma in lemmas:
        pos_exists = False
        possible_poses = lemmas[lemma]["pos"]
        for i in range(len(possible_poses)):
            if possible_poses[i] in tag:
                pos_exists = True
                break
        if not (pos_exists):
            return False

    if interpretation == "canonical":
        return True

    # попробую закомментить это условие
    # if "plural" in interpretation and not ("Number=Plur" in tag):
    #     return False
    
    if "singular" in interpretation: #  and not ("Number=Sing" in tag)
        return False

    if not ("nominative" in interpretation) and ("Case=Nom" in tag):
        return False
    if not ("genitive" in interpretation) and ("Case=Gen" in tag):
        return False
    if not ("dative" in interpretation) and ("Case=Dat" in tag):
        return False
    if not ("accusative" in interpretation) and ("Case=Acc" in tag):
        adj = False
        if "ADJ" in tag and "Animacy=Inan" in tag:
            adj = True
        if not adj:
            return False
    if not ("instrumental" in interpretation) and ("Case=Ins" in tag):
        return False
    if not ("prepositional" in interpretation) and not ("locative" in interpretation) and ("Case=Loc" in tag):
        return False
    if (("present" in interpretation) or ("future" in interpretation)) and ("Tense=Past" in tag):
        return False
    if (("past" in interpretation) or ("future" in interpretation)) and ("Tense=Pres" in tag):
        return False
    if (("past" in interpretation) or ("present" in interpretation)) and ("Tense=Fut" in tag):
        return False

    return True


def derive_single_accentuation(interpretations):
    if len(interpretations) == 0:
        return None
    res = interpretations[0]["accentuated"]
    for i in range(1, len(interpretations)):
        if interpretations[i]["accentuated"] != res:
            return None
    return res


def accentuate_word(word, lemmas):
    if ("tag" in word) and ("PROPN" in word["tag"]): # PROPN - имя собственное
        return word["token"]

    if word["is_punctuation"] or (not "interpretations" in word):
        return word["token"]
    else:
        res = derive_single_accentuation(word["interpretations"])
        if not (res is None):
            return res
        else:
            compatible_interpretations = []
            for i in range(len(word["interpretations"])):
                if compatible(word["interpretations"][i]["form"], word["interpretations"][i]["lemma"], word["tag"], lemmas):
                    compatible_interpretations.append(word["interpretations"][i])
            res = derive_single_accentuation(compatible_interpretations)

            if not (res is None):
                return res
            else:
                new_compatible_interpretations = []
                for i in range(len(compatible_interpretations)):
                    if compatible_interpretations[i]["lemma"] == word["lemma"]:
                        new_compatible_interpretations.append(compatible_interpretations[i])
                res = derive_single_accentuation(new_compatible_interpretations)
                if not (res is None):
                    return res
                else:
                    return word["token"]


def tokenize(text, wordforms):
    res = []
    doc = ru_nlp(text)
    for token in doc:
        if token.pos_ != 'PUNCT':
            word = {"token": token.text, "tag": token.tag_}
            if word["token"] in wordforms:
                word["interpretations"] = wordforms[word["token"]]
            if word["token"].lower() in wordforms:
                word["interpretations"] = wordforms[word["token"].lower()]
            word["lemma"] = token.lemma_
            word["is_punctuation"] = False
            word["uppercase"] = word["token"].upper() == word["token"]
            word["starts_with_a_capital_letter"] = word["token"][0].upper() == word["token"][0]
        else:
            word = {"token": token.text, "is_punctuation": True}
        word["whitespace"] = token.whitespace_
        res.append(word)
    return res


def accentuate(text_lines, wordforms, lemmas):
    result = [] # new
    for line in text_lines: #new
        res = "" 
        words = tokenize(line, wordforms)
        for i in range(len(words)):
            accentuated = accentuate_word(words[i], lemmas)
            if "starts_with_a_capital_letter" in words[i] and words[i]["starts_with_a_capital_letter"]:
                accentuated = accentuated.capitalize()
            if "uppercase" in words[i] and words[i]["uppercase"]:
                accentuated = accentuated.upper()
            res += accentuated
            res += words[i]["whitespace"]
        result.append(res) # new
    return result


