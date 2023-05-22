from lyrics_to_melody import Lyrics_match, get_chorus, lm_score, fill_template, splice, polish_chord, chord_truc, not_mono, not_duplicate
import random
import sqlite3
import re
import copy
from utils.midi_converter import to_midi
from utils.lyrics_preprocessing import preprocess, syllable_parse, accentuate, load
from utils.chords_generator import chords_generator, conditioned_chord_generator, shift_chord_generator
import pandas as pd
import argparse
from math import ceil

from dostoevsky.tokenization import RegexTokenizer
from dostoevsky.models import FastTextSocialNetworkModel


def select_melody(is_maj, is_chorus, length, last_bar, chord, chord_ptr, is_last_sentence):
    cursor = c.execute(
        "SELECT DISTINCT NOTES, CHORDS from MELOLIB_2  where LENGTH = '{}' and CHORUS = '{}' and MAJOR = '{}' ".format(
            length, is_chorus, is_maj))  # MELOLIB
    candidates_bars = []
    print("Retrive melody...")
    for row in cursor:
        notes = row[0]
        cd_ = row[1]
        candidates_bars.append((notes, cd_))

    # Filter by chords.
    chord_list_ = chord.strip().split(' ')
    chord_list_ = chord_list_[chord_ptr:] + chord_list_[:chord_ptr]
    re_str = ''

    if not is_last_sentence:
        key = ''
    else:
        if is_maj:
            key = ' C:'
        else:
            key = ' A:m'

    # For the given chord progression, we generate a regex like:
    # A:m F: G: C: -> ^A:m( A:m)*( F:)+( G:)+( C:)*$|^A:m( A:m)*( F:)+( G:)*$|^A:m( A:m)*( F:)*$|^A:m( A:m)*$
    # Given the regex, we find matched pieces.
    # We design the regex like this because alternations in regular expressions are evaluated from left to right,
    # the piece with the most various chords will be selected, if there's any.
    for j in range(len(chord_list_), 0, -1):
        re_str += '^({}( {})*'.format(chord_list_[0], chord_list_[0])
        for idx in range(1, j):
            re_str += '( {})+'.format(chord_list_[idx])
        re_str = re_str[:-1]
        re_str += '*{})$|'.format(key)
    re_str = re_str[:-1]

    tmp_candidates = []
    for row in candidates_bars:
        if re.match(r'{}'.format(re_str), row[1]):
            tmp_candidates.append(row)

    if len(tmp_candidates) == 0:
        re_str = '^{}( {})*$'.format(chord_list_[-1], chord_list_[-1])
        for row in candidates_bars:
            if re.match(r'{}'.format(re_str), row[1]):
                tmp_candidates.append(row)

    if len(tmp_candidates) > 0:
        candidates_bars = tmp_candidates
    else:
        if is_maj:
            re_str = '^C:( C:)*$'
        else:
            re_str = '^A:m( A:m)*$'
        for row in candidates_bars:
            if re.match(r'{}'.format(re_str), row[1]):
                tmp_candidates.append(row)
        if len(tmp_candidates) > 0:
            candidates_bars = tmp_candidates

    candidates_cnt = len(candidates_bars)
    if candidates_cnt == 0:

        print('No Matched Rhythm as {}'.format(length))
        return []

    if last_bar == None:  # we are at the begining of a song, random select bars.

        print('Start a song...')

        def not_too_high(bar):
            notes = bar.split(' ')[:-1][3::5]
            notes = [int(x[6:]) for x in notes]
            for i in notes:
                if 52 > i or i > 72: # new: вместо 57 > i or i > 66
                    return False
            return True

        tmp = []
        for bar in candidates_bars:
            if not_too_high(bar[0]):
                tmp.append(bar)
        return tmp
    else:
        last_note = int(last_bar.split(' ')[-3][6:])
        # tendency
        selected_bars = []
        prefer_note = None

        # Major C
        if is_maj:
            if last_note % 12 == 2 or last_note % 12 == 9:
                prefer_note = last_note - 2
            elif last_note % 12 == 5:
                prefer_note = last_note - 1
            elif last_note % 12 == 11:
                prefer_note = last_note + 1
                # Minor A
        else:
            if last_note % 12 == 11 or last_note % 12 == 2:  # 2 -> 1, 4 -> 3
                prefer_note = last_note - 2
            elif last_note % 12 == 6:  # 6 -> 5
                prefer_note = last_note - 1
            elif last_note % 12 == 7:  # 7-> 1
                prefer_note = last_note + 2

        if prefer_note is not None:
            for x in candidates_bars:
                if x[0][0] == prefer_note:
                    selected_bars.append(x)
        if len(selected_bars) > 0:
            print('Filter by tendency...')
            candidates_bars = selected_bars

        selected_bars = []
        for bar in candidates_bars:
            first_pitch = int(bar[0].split(' ')[3][6:])
            if (first_pitch > last_note - 8 and first_pitch < last_note + 8):
                selected_bars.append(bar)
        if len(selected_bars) > 0:
            print('Filter by pitch range...')
            return selected_bars

    # No candidates yet? randomly return some.
    print("Randomly selected...")
    return candidates_bars

def polish_0(bar, last_note_end=0, iscopy=False, first=False):
    '''
    Bar and lyrics stress alignment
    '''
    notes = bar.strip().split(' ')
    tmp = ''
    first_note_start = 0
    is_tuned = False
    

    for idx in range(len(notes) // 5):
        pos = int(notes[5 * idx + 2][4:])
        bar_idx_ = int(notes[5 * idx + 1][4:])
        dur = int(notes[5 * idx + 4][4:])
        cadence = notes[5*idx]
        this_note_start = 16 * bar_idx_ + pos

        # print('before:')
        # print('{} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur))
        # print('after:')

        if idx == 0:
            first_note_start = this_note_start
            blank_after_last_note = 16 - last_note_end % 16
            threshold = blank_after_last_note
        else:
            threshold = 0
    
        # Непонятно, зачем такое ограничение, поэтому пока что закомменчу
        if not iscopy and dur == 1:  # the minimum granularity is a 1/8 note.
            dur = 2
            # print(idx)
            # print('from 1 to 2')
        # # Непонятно, зачем такое ограничение, поэтому ограничу длительность одной целой нотой
        # if dur > 8:  # the maximum granularity is a 1/2 note.
        #     dur = 8

        if dur > 16:  # the maximum granularity is a 1/1 note.
            dur = 16
            # print('too long note')


        if not first:
            if this_note_start - last_note_end != threshold: # !=
                pos += (last_note_end + threshold - this_note_start)
                bar_idx_ += pos // 16
                pos = pos % 16

        last_note_end = 16 * bar_idx_ + pos + dur

        assert pos <= 16
        # print('{} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur))
        tmp += '{} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur)

        # print('{} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur))
        # print()

    return tmp

def polish(bar, last_note_end, iscopy=False, first=False):
    """
        Three fuctions:
        1. Avoid bars overlapping.
        2. Make the first note in all bars start at the position 0.
        3. Remove rest and cadence in a bar.
    """
    notes = bar.strip().split(' ')
    tmp = ''
    first_note_start = 0
    is_tuned = False
    for idx in range(len(notes) // 5):
        pos = int(notes[5 * idx + 2][4:])
        bar_idx_ = int(notes[5 * idx + 1][4:])
        dur = int(notes[5 * idx + 4][4:])
        pitch = int(notes[5 * idx + 3][6:]) #new

        
        this_note_start = 16 * bar_idx_ + pos

        cadence = 'NOT'

        # print('before: {} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur))

        if idx == 0:
            first_note_start = this_note_start
            blank_after_last_note = 16 - last_note_end % 16
            # print(blank_after_last_note)
            threshold = blank_after_last_note
        else:
            threshold = 0


        if not first:
            if this_note_start - last_note_end != threshold:
                new_pos = pos + (last_note_end + threshold - this_note_start)
                bar_idx_ += new_pos // 16
                # new_pos = new_pos % 16
                new_pos = pos

        
        cadence = 'HALF'  # just for the ease of model scoring

        last_note_end = 16 * bar_idx_ + pos + dur  # new_pos вместо pos
        last_note_pitch = int(notes[5 * idx + 3][6:]) #new

        assert pos <= 16
        tmp += '{} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur)
    return tmp, bar_idx_ + 1, last_note_end

# stress alignment function and auxiliary functions:
def stressLevel(syllable):
    if syllable == '+':
        return 2
    if syllable == '?':
        return 1
    else:
        return 0

def parse_pos(notes):
    result = []
    for idx in range(len(notes) // 5 - 1):
        pos = int(notes[5 * idx + 2][4:])
        bar_idx_ = int(notes[5 * idx + 1][4:])   
        result.append(pos + 16*bar_idx_) 
    return result

def parse_durs(notes):
    result = []
    for idx in range(len(notes) // 5 - 1):
        dur = int(notes[5 * idx + 4][4:])
        result.append(dur)
    return result

def beatScore(position):
    if position % 16 == 0: # downbeat
        return 40
    elif position % 16 == 12:
        return 20
    elif position % 16 == 4 or position % 16 == 8:
        return 10
    else:
        return 0

def stress_score(notes, syllable_accents):
    score = 0
    notes = notes.strip().split(' ')
    positions = parse_pos(notes)
    durs = parse_durs(notes)
    # print(len(durs))
    # print(len(positions))


    for idx, pos, dur, syllable in zip(range(len(positions)), positions, durs, syllable_accents):
        # accented syllables on strong beats
        # print()
        # print('idx = {}, pos = {}, dur = {}'.format(idx, pos, dur))
        # print('stress: ', stressLevel(syllable))
        score += stressLevel(syllable) * beatScore(pos)
        # penalty for long durations beginning on offbeats
        if pos % 4 == 2 and dur > 2:
            # print('pos % 4 == 2 and dur > 2')
            penalty = 10
        elif pos % 4 == 1 and dur > 2:
            # print('pos % 4 == 1 and dur > 2')
            penalty = 40
        elif pos % 4 == 3 and dur > 1:
            # print('pos % 4 == 3 and dur > 1')
            penalty = 40
        else:
            penalty = 0
        score -= stressLevel(syllable) * penalty

        # Accented syllables of short relative duration 
        if stressLevel(syllable) == 2:
            if idx == 0:
                if durs[idx+1] > dur:
                    # print('-1')
                    score -= 1
            elif idx == len(positions) - 1:
                if durs[idx-1] > dur:
                    score -= 1
                    # print('-1')
            else:
                if durs[idx-1] > dur or durs[idx+1] > dur:
                    score -= 1
                    # print('-1')

    return score

def notes_shift(notes, shift=4):
    res = []
    for note in notes:
        pos = note[2] + shift
        bar = note[1]
        if pos >= 16:
            bar = bar + pos // 16
            pos = pos - 16
        res.append([note[0], bar, pos, note[3], note[4]])
    
    #new 
    last_pos = res[-1][1]*16 + res[-1][2]
    return res, last_pos

def stress_alignment(bar, stress, iscopy=False):
    '''
    Bar and lyrics stress alignment
    '''
    notes = bar.strip().split(' ')
    tmp = ''
    idx = len(notes) // 5 - 1
    first = True
    prev_pos = 0
    tmp_array = []
    stress_dur = float("inf")

    while idx >= 0:
        pos = int(notes[5 * idx + 2][4:])
        bar_idx_ = int(notes[5 * idx + 1][4:])
        dur = int(notes[5 * idx + 4][4:])
        cadence = notes[5*idx]

        if stress[idx] == '+':
            while pos % 4 != 0:
                pos += 1
                if pos >= 16:
                    bar_idx_ += pos//16
                    pos = pos - 16
            if not first:
                dur = prev_pos - bar_idx_*16 - pos
            if dur <= 0:
                tmp_array, prev_pos = notes_shift(tmp_array) # смещаем все ноты вперёд на четыре
                dur = tmp_array[-1][1]*16 + tmp_array[-1][2] - bar_idx_*16 - pos # снова подтягиваем длительность
                tmp = '' #записываем заново
                for note in tmp_array:
                    tmp = '{} bar_{} Pos_{} {} Dur_{} '.format(*note) + tmp # добавляем каждую новую ноту пере
            stress_dur = dur

        else:
            if pos % 4 == 0:
                pos += ceil(dur/2)
                if pos >= 16:
                    bar_idx_ += pos//16
                    pos = pos - 16
            if prev_pos - bar_idx_*16 - pos > 0:
                dur = min(prev_pos - bar_idx_*16 - pos, dur)  
                pos =  prev_pos - dur

            if not first and dur >= stress_dur:
                if stress_dur > 1:
                    dur = stress_dur 
                    pos = prev_pos - dur

        if pos >= 16:
            bar_idx_ = pos//16 
            pos = pos - bar_idx_*16

        prev_pos = bar_idx_*16 + pos # записываем в буфер прошлый position
        if first:
            dur = int(notes[5 * idx + 4][4:])
            first = False

        tmp_array.append([cadence, bar_idx_, pos, notes[5 * idx + 3], dur])
        # print('{} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur))
        tmp = '{} bar_{} Pos_{} {} Dur_{} '.format(cadence, bar_idx_, pos, notes[5 * idx + 3], dur) + tmp
        idx -= 1
    return tmp



def sentiment(lyrics):
    tokenizer = RegexTokenizer()
    model = FastTextSocialNetworkModel(tokenizer=tokenizer)
    results = model.predict(lyrics)[0]
    print(results)

    if results['positive'] > results['negative']:
        print('positive')
        return 1
    else:
        print('negative')
        return 0


def block_cnts(lyrics):
    i = 0
    cnts = []
    for lyric in lyrics:
        if len(lyric) == 0:
            cnts.append(i)
            i = 0
        else:
            i += 1

    cnts.append(i)
    
    return cnts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='none.')
    parser.add_argument('--lyrics_path', default='lyrics.txt')
    parser.add_argument('--db_path', default='database/ROC.db')
    parser.add_argument('--debug', action='store_true', help='Output composition details')
    parser.add_argument('--conditioned', action='store_true')
 
    config = parser.parse_args()

    lyrics_path = config.lyrics_path

    # Загрузка базы мелодий
    db_path = config.db_path
    conn = sqlite3.connect(db_path)
    global c
    c = conn.cursor()
    print("Database connected")

    lemmas, wordforms = load()

    with open(lyrics_path) as lyrics_file:
        lyrics_lines = lyrics_file.read()
    lyrics_with_white_lines = [lyric for lyric in lyrics_lines.split('\n') if (lyric + 'x')[0] != '[']
    lyric_blocks_cnts = [i for i in block_cnts(lyrics_with_white_lines) if i != 0]
    lyrics_for_chords = [line for line in lyrics_with_white_lines if len(line) > 0]

    lines = accentuate(lyrics_for_chords, wordforms, lemmas)
    lyrics = preprocess(lines, one_line = False)

    name = lyrics[0]
    sentence = syllable_parse(lyrics) # parsing the syllables
    syllables = [len(x.strip().split(' ')) * '_' for x in lyrics]

    word_counts = [len(x) for x in sentence]
    print(*word_counts)

    def recomender(lines):
        print('The following lines need to be shortened: \n')
        for sentence, line in zip(lyrics, lines):
            if len(line) > 10:
                print(sentence)

    recomender(sentence)


    # structure recognition
    parent, chorus_start, chorus_length = Lyrics_match(syllables)  # The last element must be -1, because the chord should go back to tonic
    print('Struct Array: ', parent)

    chorus_range = get_chorus(chorus_start, chorus_length, lyrics)
    print('Recognized Chorus: ', chorus_start, chorus_length)

    sent = sentiment([' '.join(lyrics_with_white_lines)])


    is_debug = config.debug
    score_before = []
    score_after = []
    conditioned = config.conditioned

    chord_ptr = 0

    is_maj = sent
    threshold = 120

    sentence = syllable_parse(lyrics)

    # chord = chords_generator(lyrics, is_maj=is_maj)
    # chord = 'C: B:dim C: D:m B:dim A:m C: C: B:dim A:m C: C: B:dim A:m C: C:'
    chord = shift_chord_generator('\n'.join(lyrics_for_chords), is_maj, lyric_blocks_cnts)
    print(chord)

    if conditioned:
        chord = conditioned_chord_generator('\n'.join(lyrics_for_chords))
    else:
        print('If you want a song in a major scale, print 1, else: 0')
        is_maj = input()
        chord_ptr = 0
        chord = chords_generator(lyrics, is_maj=is_maj)

    print(chord)

    print('Tonality:', is_maj)

    # structure recognition
    parent, chorus_start, chorus_length = Lyrics_match(
        sentence)  # The last element must be -1, because the chord should go back to tonic
    if is_debug:
        print('Struct Array: ', parent)

    chorus_range = get_chorus(chorus_start, chorus_length, lyrics)
    if is_debug:
        print('Recognized Chorus: ', chorus_start, chorus_length)

    select_notes = []  # selected_melodies
    select_chords = []  # selected chords
    is_chorus = 0  # is a chorus?
    note_string = ''  # the 'melody context' mentioned in the paper.
    bar_idx = 0  # current bar index. it is used to replace bar index in retrieved pieces.
    last_note_end = -16
    # is_1smn = 0             # Does 1 Syllable align with Multi Notes? In the future, we will explore better methods to realize this function. Here by default, we disable it.

    for i in range(len(sentence)):
        print('Line ', i)
        print('Lyrics: ', lyrics[i])

        is_last_sentence = (i == len(sentence) - 1)

        if i in chorus_range:
            is_chorus = 1
        else:
            is_chorus = 0

        cnt = len(sentence[i])
        if cnt <= 2 and parent[i] == -2:  # if length is too short, do not partially share
            parent[i] = -1

        if conditioned:
            chord_i = chord[i]
        # Following codes correspond to 'Retrieval and Re-ranking' in Section 3.2.
        # parent[i] is the 'struct value' in the paper.
        if parent[i] == -1:
            if is_debug:
                print('No sharing.')

            # пока для простоты не будем
            # one_syllable_multi_notes_probabilty = random.randint(1,100)
            # if one_syllable_multi_notes_probabilty == 1:
            #     is_1smn = 1
            #     connect_notes = random.randint(1,2)
            #     cnt += connect_notes
            #     connect_start = random.randint(1,cnt)
            #     print('One Syllable Multi Notes range:',connect_start, connect_start + connect_notes)

            if len(select_notes) == 0:  # The first sentence of a song.
                last_bar = None
            else:
                last_bar = select_notes[-1]

            if conditioned:
                selected_bars = select_melody(is_maj, is_chorus, cnt, last_bar, chord_i, chord_ptr, is_last_sentence)
            else:
                selected_bars = select_melody(is_maj, is_chorus, cnt, last_bar, chord, chord_ptr, is_last_sentence)

            
            if len(selected_bars) > 0: # убрала cnt < 9
                selected_bars = lm_score(selected_bars, note_string, bar_idx)
                # selected_bars = no_keep_trend(selected_bars)
                bar_chord = selected_bars[random.randint(0, len(selected_bars) - 1)]
                s_bar = bar_chord[0]
                print('chosen melody: ', s_bar)
                s_chord = bar_chord[1]
                s_bar, bar_idx = fill_template(s_bar,
                                                bar_idx)  # The returned bar index is the first bar index which should be in the next sentence, that is s_bar + 1.
                
                print('Chord from the database: ', s_chord)
                # Добавила 28.01.2023 - блок, сохраняющий заданные аккорды
                if conditioned:
                    s_chord = chord_i.strip()
                else:
                    s_chord = chord.strip().split(' ')[i] 
                    for _ in range(len(bar_chord[1].strip().split(' ')) - 1):
                        s_chord += ' ' + chord.strip().split(' ')[i] 
            
            
            else:  # If no pieces is retrieved or there are too many syllables in a lyric.
                if is_debug:
                    print('No pieces is retrieved or there are too many syllables in a lyric. Split the lyric.')
                s_bar = ''
                s_chord = ''
                origin_cnt = cnt
                error = 0
                while cnt > 0:
                    l = max(origin_cnt // 3, 5)
                    r = max(origin_cnt // 2, 7)  # Better to use long pieces, for better coherency.
                    split_len = random.randint(l, r)
                    if split_len > cnt:
                        split_len = cnt
                    if is_debug:
                        print('Split at ', split_len)

                    if conditioned:
                        selected_bars = select_melody(is_maj, is_chorus, split_len, last_bar, chord_i, chord_ptr,
                                                    is_last_sentence)
                    else:
                        selected_bars = select_melody(is_maj, is_chorus, split_len, last_bar, chord, chord_ptr,
                                                    is_last_sentence)


                    if len(selected_bars) > 0:
                        selected_bars = lm_score(selected_bars, note_string + s_bar, bar_idx)
                        bar_chord = selected_bars[random.randint(0, len(selected_bars) - 1)]
                        last_bar = bar_chord[0]
                        last_chord = bar_chord[1]
                        s_bar = splice(s_bar, last_bar)
                        s_chord += ' ' + last_chord

                        # Explanation: if this condition is true, i.e., the length of s_bar + last_bar == the length of last_bar,
                        # then the only possibility is that we are in the first step of this while loop. We need to replace the bar index in retrieved pieces with the true bar index.
                        # In the following steps, there is no need to do so because there is a implicit 'fill_template' in 'splice'.
                        if len(s_bar) == len(last_bar):
                            s_bar, bar_idx = fill_template(s_bar, bar_idx)

                        if conditioned:
                            s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord_i, chord_ptr)
                        else:
                            s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord, chord_ptr)

                        last_bar = s_bar
                        cnt -= split_len
                    else:
                        error += 1
                        if error >= 10:
                            print('Database has not enough pieces to support ROC.')
                            exit()

                s_chord = s_chord[1:]
                print('Chord from the database: ', s_chord)


            # if i > 0: # new
            #     s_bar, bar_idx, last_note_end = polish(s_bar, last_note_end)
            # else: # new
            #     s_bar, bar_idx, last_note_end = polish(s_bar, last_note_end, first=True)


            s_bar = polish_0(s_bar)
            
            # new: stress alignment
            score_before.append(stress_score(s_bar, sentence[i]))
            if stress_score(s_bar, sentence[i]) <= threshold: # new condition: change only if there is bad alignment
                s_bar = stress_alignment(s_bar, sentence[i])

            score_after.append(stress_score(s_bar, sentence[i]))
            print('Notes before polishing: ', s_bar)
            print('last note end: ', last_note_end)
            s_bar, bar_idx, last_note_end = polish(s_bar, last_note_end)

            if conditioned:
                s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord_i, chord_ptr)
            else:
                s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord, chord_ptr)

            note_string += s_bar
            select_notes.append(s_bar)
            select_chords.append(s_chord)
            if is_debug:
                print('Selected notes: ', s_bar)
                print('Chords: ', s_chord)

        elif parent[i] == -2:
            if is_debug:
                print('Share partial melody from the previous lyric.')

            l = min(cnt // 3,
                    3)  # As mentioned in 'Concatenation and Polish' Section, for adjacents lyrics having the same syllabels number,
            r = min(cnt // 2, 5)  # we 'polish their melodies to sound similar'

            # modify some notes then share.
            replace_len = random.randint(l, r)
            last_bar = ' '.join(select_notes[-1].split(' ')[:- replace_len * 5 - 1]) + ' '
            tail = select_notes[-1].split(' ')[- replace_len * 5 - 1:]
            
            last_chord = ' '.join(chord_truc(last_bar, select_chords[-1]))
            print('1: last_chord: ', last_chord)

            # new: заменяем last_chord на текущий аккорд
            # new block for keeping the chords
            if conditioned:
                s_chord_0 = chord_i.strip() 
            else:
                s_chord_0 = chord.strip().split(' ')[i] 

            print('2: chord ', s_chord_0)
            if not conditioned:
                for _ in range(len(last_chord.strip().split(' ')) - 1):
                    s_chord_0 += ' ' + chord.strip().split(' ')[i] 
            print('3: chord ', s_chord_0)        

            if conditioned:
                selected_bars = select_melody(is_maj, is_chorus, replace_len, last_bar, chord_i, i, ### i вместо chord_ptr
                                            is_last_sentence)
            else:
                selected_bars = select_melody(is_maj, is_chorus, replace_len, last_bar, chord, i, ### i вместо chord_ptr
                                            is_last_sentence)            
            selected_bars = lm_score(selected_bars, note_string + last_bar, bar_idx)
            for bar_chord in selected_bars:
                bar = bar_chord[0]
                s_chord = bar_chord[1]
                print('1: chord ', s_chord)

                # new block for keeping the chords
                if conditioned:
                    s_chord = chord_i.strip()
                else: 
                    s_chord = chord.strip().split(' ')[i]

                print('2: chord ', s_chord)

                if not conditioned:
                    for _ in range(len(bar_chord[1].strip().split(' ')) - 1):
                        s_chord += ' ' + chord.strip().split(' ')[i] 
                print('3: chord ', s_chord)
                

                s_bar = splice(last_bar, bar)

                # 24.02.2023: Непонятно, зачем эта часть кода
                if not_mono(s_bar) and not_duplicate(s_bar, select_notes[-1]):
                    s_chord = s_chord_0 + ' ' + s_chord
                    print('4: chord ', s_chord)

                    break

            # print('1: s_bar: ', s_bar)

            # # Добавила 28.01.2023 - блок, сохраняющий заданные аккорды
            # s_chord = chord.strip().split(' ')[chord_ptr] 
            # for _ in range(len(bar_chord[1].strip().split(' ')) - 1):
            #     s_chord += ' ' + chord.strip().split(' ')[i] 

                
            s_bar, bar_idx = fill_template(s_bar, bar_idx)
            # print('2: s_bar: ', s_bar)

            s_bar = s_bar.split(' ')

            for j in range(2, len(tail)):  # Modify duration
                if j % 5 == 2 or j % 5 == 1:  # dur and cadence
                    s_bar[-j] = tail[-j]
            s_bar = ' '.join(s_bar)

            # print('3: s_bar: ', s_bar)
            print('chosen melody: ', s_bar)
            s_bar = polish_0(s_bar, True)
            # print('4: s_bar: ', s_bar)
            # new
            score_before.append(stress_score(s_bar, sentence[i]))
            if stress_score(s_bar, sentence[i]) <= threshold: # new condition: change only if there is bad alignment
                print('i = ', i)
                print(stress_score(s_bar, sentence[i]))
                print( sentence[i])
                s_bar = stress_alignment(s_bar, sentence[i])
                print('5: s_bar: ', s_bar)

            s_bar, bar_idx, last_note_end = polish(s_bar, last_note_end, True)

            score_after.append(stress_score(s_bar, sentence[i]))
            
            if conditioned:
                s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord_i, chord_ptr)
            else:
                s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord, chord_ptr)


            note_string += s_bar
            select_notes.append(s_bar)
            select_chords.append(s_chord)

            if is_debug:
                print('Modified notes: ', s_bar)
                print('chords: ', s_chord)
        else:
            # 'struct value is postive' as mentioned in the paper, we directly share melodies.
            if is_debug:
                print('Share notes with sentence No.', parent[i])

            s_bar = copy.deepcopy(select_notes[parent[i]])

            # s_chord = copy.deepcopy(select_chords[parent[i]])
            # Аккорд должен идти в порядке последователньости
            if conditioned:
                s_chord = chord_i.strip()
            else:
                s_chord = chord.strip().split(' ')[i]  

            print('1: chord ', s_chord)
            if not conditioned:
                for _ in range(len(select_chords[parent[i]].strip().split(' ')) - 1):
                    s_chord += ' ' + chord.strip().split(' ')[i] 

            s_bar, bar_idx = fill_template(s_bar, bar_idx)

            s_bar = polish_0(s_bar, True)
            print('chosen melody: ', s_bar)

            # # new
            score_before.append(stress_score(s_bar, sentence[i]))
            if stress_score(s_bar, sentence[i]) <= threshold: # new condition: change only if there is bad alignment
                s_bar = stress_alignment(s_bar, sentence[i])
            score_after.append(stress_score(s_bar, sentence[i]))

            s_bar, bar_idx, last_note_end = polish(s_bar, last_note_end, True)

            if conditioned:
                s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord_i, chord_ptr)
            else:
                s_chord, chord_ptr = polish_chord(s_bar, s_chord, chord, chord_ptr)
            note_string += s_bar
            select_notes.append(s_bar)
            select_chords.append(s_chord)

        if is_debug:
            print(
                '----------------------------------------------------------------------------------------------------------')

    if is_debug:
        print(select_chords)
        print(select_notes)


    scores = pd.DataFrame([score_before, score_after])
    scores.sample(10)


    part_midi = to_midi(note_string, preprocess(lyrics_for_chords, one_line = False), select_chords, name=name, partly=False)
    part_midi.show()
    part_midi.show('midi')
