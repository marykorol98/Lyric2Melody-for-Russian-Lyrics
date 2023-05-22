from lyrics_to_melody import Lyrics_match, get_chorus
import random
from transformers import T5ForConditionalGeneration, AutoTokenizer
from utils.generating import SongWriter
import re
from pychord import ChordProgression
from joblib import load
import itertools
import pandas as pd
import numpy as np


def chords_generator(lyrics, is_maj=True):
    syllables = [len(x.strip().split(' ')) * '_' for x in lyrics] # parsing the syllables

    # structure recognition
    parent, chorus_start, chorus_length = Lyrics_match(syllables)  # The last element must be -1, because the chord should go back to tonic
    chorus_range = get_chorus(chorus_start, chorus_length, lyrics)

    chords = []
    top_chords = ['C:', 'D:m', 'E:m', 'F:', 'G:', 'A:m', 'B:dim'] 
    # Добавить статистические вероятности! B:dim явно встречается реже остальных

    # 'D:m7', 'G:7', 'A:m7', 'F:maj7', 'C:maj7', 'E:m7'
    # 'Bb:', 'E:', 'E:7'

    if is_maj:
        chord = 'C:'
    else:
        chord = 'A:m'

    chords = [chord]

    i_v = 0
    i_ch = 0
    i = 0

    if i in chorus_range: # If a song starts from chorus
        random_set_verse = random.choices(top_chords, k=4)
        random_set_chorus = [chord] + random.choices(top_chords, k=3)
        i_ch+=1
        
    else: # If a song starts from verse
        random_set_verse = [chord] + random.choices(top_chords, k=3)
        random_set_chorus = random.choices(top_chords, k=4)
        i_v += 1
        


    # # for the first iteration
    # # if len(syllables[0]) > 8:
    # # for _ in range(ceil(len(syllables[0])/8)):
    # if i in chorus_range or (parent[i]>=0 and parent[parent[i]] in chorus_range): # расщирила то, что входит в припев
    #     chords.append(random_set_chorus[i_ch % 4])
    #     i_ch += 1
    # else:
    #     chords.append(random_set_verse[i_v % 4])
    #     i_v+=1

    i += 1

    for i in range(len(parent)-1):
        if i in chorus_range or (parent[i]>=0 and parent[parent[i]] in chorus_range): # расширила то, что входит в припев
            chords.append(random_set_chorus[i_ch % 4])
            i_ch += 1
            # if len(syllables[0]) > 8:
            #     if i in chorus_range or (parent[i]>=0 and parent[parent[i]] in chorus_range): # расщирила то, что входит в припев
            #         chords.append(random_set_chorus[i_ch % 4])
            #         i_ch += 1
            #     else:
            #         chords.append(random_set_verse[i_v % 4])
            #         i_v+=1


        else:
            chords.append(random_set_verse[i_v % 4])
            i_v+=1
            # if len(syllables[0]) > 8:
            #     for _ in range(ceil(len(syllables[0])/8)):
            #         if i in chorus_range or parent[i] in chorus_range: # расщирила то, что входит в припев
            #             chords.append(random_set_chorus[i_ch % 4])
            #             i_ch += 1
            #         else:
            #             chords.append(random_set_verse[i_v % 4])
            #             i_v+=1         



    # for i in range(len(parent)-1):
    #     if parent[i+1] == -1:
    #         if i in chorus_range:
    #             chords.append(random_set_chorus[i_ch % 4])
    #             i_ch += 1
    #         else:
    #             chords.append(random_set_verse[i_v % 4])
    #             i_v+=1  
    #     elif parent[i+1] == -2:
    #         chords.append(chords[-1])
    #     else:
    #         chords.append(chords[parent[i+1]])

    return ' '.join(chords)


def shift_chord_generator(lyrics, is_maj, lyric_blocks_cnts, dist=True):

    # clf = load('/home/marykorol/roc-model/lyrics2chords/amdm/multilabel_classification/LogReg_pipeline.joblib') 
    clf = load('multilabel_classification/LogReg_pipeline.joblib') 

    lines = re.sub(' +', ' ', lyrics).split('\n')
    # overall_length = len(lines)
    y_pred = clf.predict([' '.join(lines)])
    length = 4

    if dist:
        # tones = pd.read_csv('/home/marykorol/roc-model/lyrics2chords/amdm/multilabel_classification/tone_distr.csv')
        # colors = pd.read_csv('/home/marykorol/roc-model/lyrics2chords/amdm/multilabel_classification/color_distr.csv')

        tones = pd.read_csv('multilabel_classification/tone_distr.csv')
        colors = pd.read_csv('multilabel_classification/color_distr.csv')   

        chords_set = {'C' : 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6} 

        if is_maj == 1:
            chords = ['C:']
        else:
            chords = ['A:m']

        for i in range(1, length):
            notgood = True
            while notgood:
                chord = np.random.choice(tones.chord.values, p=tones.freq.values)

                if 'm' in chord:
                    chord = chord[0] + ':' + chord[1]
                else:
                    chord += ':'

                shift = chords_set[chord[0]] - chords_set[chords[-1][0]]
                if shift < 0:
                    shift += 7

                if y_pred[0][shift] == 1:
                    notgood = False

                # проверка на shift между первым и последним
                if i == length - 1:
                    shift_2 = chords_set[chord[0]] - chords_set[chords[0][0]]
                    if shift_2 < 0:
                        shift_2 += 7

                    if y_pred[0][shift_2] == 1:
                        notgood = False

            
            color = np.random.choice(colors.color.values, p=colors.freq.values)
            if color != '_':
                chord += color
            
            chords.append(chord)

    else:
        if is_maj == 1:
            chords_set = ['C:', 'D:m', 'E:m', 'F:', 'G:', 'A:m', 'B:m']
            chords = ['C:']
        else:
            chords_set = ['A:m', 'B:m', 'C:', 'D:m', 'E:m', 'F:', 'G:']
            chords = ['A:m']
        current_tone = 0
        # random shifts

        shifts = [i for i, boolean in enumerate(y_pred[0]) if boolean == 1]
        shifts_combs = list(itertools.product(shifts, repeat = length-1))
        shifts_choice = random.choice(shifts_combs)
        print(shifts_choice)

        # аккорды
        for shift in shifts_choice:
            current_tone += shift
            while current_tone > 6:
                current_tone -= 7
            
            chords.append(chords_set[current_tone])

    # chords *= overall_length//4 + 1
    all_chords = []
    for block in lyric_blocks_cnts:
        if block % length == 0:
            # print(0)
            all_chords += chords * (block//length)
        else:
            # print(block)
            all_chords += chords * (block//length) + chords[:block % length]
        # print(*all_chords)

    
    return ' '.join(all_chords)


def num_odd_chords(chords):
    counter = 0
    for chord in chords:
        # if (str(chord)[0] in ['D', 'E', 'B'] or 'Bb' in str(chord)) and 'b' not in str(chord) and '#' not in str(chord):
        #     continue
        for i, note in enumerate(chord.components()):
            if ('b' in note or '#' in note):
                if i == 0:
                    counter += 1
                else:
                    counter += 0.4
                break

    
    
    return counter
def odd_notes_num(notes):
    counter = 0
    for note in notes:
        if 'b' in note or '#' in note:
            counter += 1
    return counter

def get_all_notes(chords):
    notes = set()
    for chord in chords:
        for note in chord.components():
            notes.add(note)
    return notes

def add_two_dots(chord):
    if len(chord) == 1:
        return chord + ':'
    
    if chord[1] in ['#','b']:
        result = chord[:2] + ':' + chord[2:]
    else:
        result = chord[0] + ':' + chord[1:]   
    # result += chord[1:]
    return result

def simple_transpose(cds, debug=False):

    try:
        cp, cnt = ChordProgression(cds), 0
    except ValueError:
            print(cds)

    min_odds = num_odd_chords(cp)
    min_odd_notes = odd_notes_num(get_all_notes(cp))
    cp_0 = ChordProgression(cds)
    tonic = cp._chords[0]._chord

    while num_odd_chords(cp) > 0:
        cp.transpose(+1)
        # print(cp._chords[0]._chord)
        # print('num_odd_chords: ', num_odd_chords(cp))
        # print(num_odd_chords(cp) < min_odds)
        
        if num_odd_chords(cp) < min_odds or (num_odd_chords(cp) == min_odds and (odd_notes_num(get_all_notes(cp)) < min_odd_notes or cp._chords[0]._chord in {'Am', 'C'})):
            # if debug:
            #     print('{} odd chords:'.format(num_odd_chords(cp)))
            #     print(cp)
            #     print()
            min_odds, min_odd_notes, tonic = num_odd_chords(cp), odd_notes_num(get_all_notes(cp)), cp._chords[0]._chord
            # print(tonic)
            # print(min_odds)
            # print(min_odd_notes)

        # elif num_odd_chords(cp) == min_odds:
        #     if odd_notes_num(get_all_notes(cp)) < min_odd_notes or cp._chords[0]._chord in {'A', 'C'}: # добавить возможность повышения шестой или пятой ступеней (гармонический/мелодический)
        #         min_odds, min_odd_notes, tonic = num_odd_chords(cp), odd_notes_num(get_all_notes(cp)), cp._chords[0]._chord

        if cnt >= 13: # если не найдено вариантов без диезов и бимолей, то выбрать тональность с минимальным количеством таких нот
            cnt = 0
            # print('has blacks')
            # print(tonic)
            # print(min_odds)
            # print(min_odd_notes)
            while cp_0._chords[0]._chord != tonic:
                cnt += 1
                # print('cnt: ', cnt)
                cp_0.transpose(+1)
            # print('{} odd notes remain'.format(odd_notes_num(get_all_notes(cp))))
            # print('{} odd chords'.format(num_odd_chords(cp)))
            return ' '.join([add_two_dots(chord._chord) for chord in cp_0._chords]), cnt, min_odds
        cnt += 1
        # print('cnt: ', cnt)
            
    # check if Am or C is better

    return ' '.join([add_two_dots(chord._chord) for chord in cp._chords]), cnt, min_odds


def conditioned_chord_generator(lyrics):
    '''
    import lyrics should be not devided into syllables
    '''

    tokenizer = AutoTokenizer.from_pretrained("t5-base")
    # chords_model = T5ForConditionalGeneration.from_pretrained(f'/home/marykorol/roc-model/lyrics2chords/amdm/model_chords_1-1')
    chords_model = T5ForConditionalGeneration.from_pretrained(f'/conditioned/model_chords_1-1')
    
    chords_model = chords_model.to(device='cuda')
    song_writer = SongWriter(chords_model, tokenizer, verbose=True)
    
    all_chords_set = set()
    odd_num = 0


    while len(all_chords_set) <=2 or odd_num >= 5: # нужно, чтобы в последовательности было хотя бы два аккорда
        trial = song_writer.write_songs_chords([lyrics])[0]

        # get the chords array
        chords = [re.sub(r' +', ' ', line) for i, line in enumerate(trial.split('\n')) if i%2 == 0]
        all_chords = re.sub(r' +', ' ', ' '.join(chords))
        all_chords = re.sub(r'^ | $', '', all_chords).split(' ')
        all_chords_set = set(all_chords)
        tr, cnt, odd_num = simple_transpose(all_chords)


    print(all_chords)
    
    
    # print(tr)
    # print('cnt: ', cnt)

    # transpose
    new_chords = []

    for line in chords:
        cds =  re.sub(r' +', ' ', line)
        cds = re.sub(r'^ | $', '', cds).split(' ')
        # print(cds)
        cp = ChordProgression(cds)

        if cnt != 0:
            cp.transpose(+cnt)
        res = ' '.join([add_two_dots(chord._chord) for chord in cp._chords])
        new_chords.append(res)


    # # :
    # new_chords = []
    # for line in chords:
    #     new_line = ''
    #     for chord in line.split(' '):
    #         if 'b' not in chord:
    #             new_chord = ' ' + chord[0] + ':' + chord[1:]
    #         else:
    #             new_chord = ' ' + chord[0:1] + ':' + chord[2:]
    #         new_line += new_chord
        
    #     new_chords.append(re.sub('^ ', '', new_line))


    return new_chords

