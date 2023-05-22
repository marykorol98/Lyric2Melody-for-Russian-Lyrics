import music21
from midiutil.MidiFile import MIDIFile
import miditoolkit
import os
import re
from utils.lyrics_preprocessing import vowelcount, syllable_parse
import datetime

def to_midi_orig(bars, name, chords=None): #select_chords,
    notes_str = bars

    pitch_dict = {'C': 0, 'C#': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
    _CHORD_KIND_PITCHES = {
            '': [0, 4, 7],
            'm': [0, 3, 7],
            '+': [0, 4, 8],
            'dim': [0, 3, 6],
            '7': [0, 4, 7, 10],
            'maj7': [0, 4, 7, 11],
            'm7': [0, 3, 7, 10],
            'm7b5': [0, 3, 6, 10],
        }


    mf = MIDIFile(2)  # only 1 track
    melody_track = 0  # the only track
    chord_track = 1
    time = 0  # start at the beginning
    channel = 0

    mf.addTrackName(melody_track, time, "melody")
    # mf.addTrackName(chord_track, time, "chord")
    mf.addTempo(melody_track, time, 120) #can be modificated
    #mf.addTempo(chord_track, time, 120)

    notes = notes_str.split(' ')
    cnt = 0
    sen_idx = 0
    chord_time = []
    for i in range(len(notes) // 5):

        # print('writing idx: ', i)
        # cadence = notes[5 * i]
        bar = int(notes[5 * i + 1][4:])
        pos = int(notes[5 * i + 2][4:])  # // pos_resolution
        pitch = int(notes[5 * i + 3][6:])
        dur = int(notes[5 * i + 4][4:]) / 4

        time = bar * 4 + pos / 4  # + delta

        # if cadence == 'HALF':
        #     delta += 2
        # if cadence == 'AUT':
        #    delta += 4

        mf.addNote(melody_track, channel, pitch, time, dur, 100)

        # # fill all chords into bars before writing notes
        if cnt == 0:
            try:
                cds = [chords][sen_idx].split(' ')
                t = time - time % 2
                if len(chord_time) > 0:
                    blank_dur = t - chord_time[-1] - 2
                    insert_num = int(blank_dur / 2)


                    root, cd_type = cds[0][6:].split(':')
                    root = pitch_dict[root]
                    for i in range(insert_num):
                        for shift in _CHORD_KIND_PITCHES[cd_type]:
                            mf.addNote(chord_track, channel, 36 + root + shift, chord_time[-1] + 2, 2, 75)
                        chord_time.append(chord_time[-1] + 2)
                    

                # print('begin sentence:', sen_idx)
                for i, cd in enumerate(cds):
                    #print(cd)
                    if i % 2 == 0:
                        # print(cd)
                        root, cd_type = cd.split(':')
                        root = pitch_dict[root]
                        # mf.addNote(chord_track, channel, 36+root, t, 2, 75)  # 36 is C3
                        for shift in _CHORD_KIND_PITCHES[cd_type]:
                            mf.addNote(chord_track, channel, 36 + root + shift, t, 2, 75)
                        chord_time.append(t)
                        t += 2
            except IndexError:
                pass
        cnt += 1


    name = './originals_parsed/after/' + name
    name += '.mid'


    with open(name, 'wb') as outf:
        mf.writeFile(outf)
    
    score = music21.converter.parse(name)

    return score

def to_midi(bars, lyrics, select_chords, name=None, partly = False, part_num=None, with_lyrics=True):
    '''
    bars - ноты
    lyrics_line - строчка теста песни
    select_chords - аккорды гармонии

    '''

    notes_str = bars
    sentence = syllable_parse(lyrics)
    word_counter = [len(i) for i in sentence]

    pitch_dict = {'C': 0, 'C#': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
    _CHORD_KIND_PITCHES = {
            '': [0, 4, 7],
            'm': [0, 3, 7],
            '+': [0, 4, 8],
            'dim': [0, 3, 6],
            # 'dim': [0, 3],
            '7': [0, 4, 7, 10],
            'maj7': [0, 4, 7, 11],
            'm7': [0, 3, 7, 10],
            'm7b5': [0, 3, 6, 10],
        }

    chord_dict = {
        'C:': [0, 4, 7],
        'D:m': [2, 5, 9],
        'E:m': [4, 7, 11],
        'F:': [0, 5, 9],
        'G:': [2, 7, 11],
        'A:m': [0, 4, 9],
        'B:dim': [2, 5, 11]
        #'B:dim': [2, 11]

    }
    if name is None:
        name = 'test_mini_{}'.format(lyrics[0].replace(' ', '_'))
    else:
        name = name.replace(' ', '_')


    if part_num:
        name = '{}_part_{}_{}'.format(lyrics[0].replace(' ', '_'), part_num, str(datetime.datetime.now().time()))

    mf = MIDIFile(2)  # only 1 track
    melody_track = 0  # the only track
    chord_track = 1
    time = 0  # start at the beginning
    channel = 0

    mf.addTrackName(melody_track, time, "melody")
    mf.addTrackName(chord_track, time, "chord")
    mf.addTempo(melody_track, time, 120) #can be modificated
    mf.addTempo(chord_track, time, 120)

    channel = 0
    time = 0 # Eight beats into the composition
    program = 42 # A Cello
    # mf.addProgramChange(chord_track, channel, time, 0)
    # mf.addProgramChange(chord_track, 1, time, 42)


    notes = notes_str.split(' ')
    cnt = 0
    sen_idx = 0
    chord_time = []
    for i in range(len(notes) // 5):

        # print('note ', i)

        # print('writing idx: ', i)
        # cadence = notes[5 * i]
        # print(notes[5 * i + 1])
        bar = int(notes[5 * i + 1][4:])
        pos = int(notes[5 * i + 2][4:])  # // pos_resolution
        pitch = int(notes[5 * i + 3][6:])
        dur = int(notes[5 * i + 4][4:]) / 4

        time = bar * 4 + pos / 4  # + delta

        # if cadence == 'HALF':
        #     delta += 2
        # if cadence == 'AUT':
        #    delta += 4
        channel = 0
        mf.addNote(melody_track, channel, pitch, time, dur, 100)

        # fill all chords into bars before writing notes
        if cnt == 0:
            try:
                cds = select_chords[sen_idx].split(' ')
                t = time - time % 2
                if len(chord_time) > 0:
                    blank_dur = t - chord_time[-1] - 2
                    insert_num = int(blank_dur / 2)

                    # для любых аккордов
                    # root, cd_type = cds[0].split(':')
                    # root = pitch_dict[root]
                    # for i in range(insert_num):
                    #     for shift in _CHORD_KIND_PITCHES[cd_type]:
                    #         mf.addNote(chord_track, channel, 36 + root + shift, chord_time[-1] + 2, 2, 75)
                    #     chord_time.append(chord_time[-1] + 2)

                    # # для части аккордов

                    for i in range(insert_num):
                        # print('cds: ', cds)
                        # print('chord ', i)
                        chord_0 = cds[0]

                        try:
                            for shift in chord_dict[chord_0]:
                                # channel = 1
                                mf.addNote(chord_track, channel, 48 + shift, chord_time[-1] + 2, 2, 50)
                            chord_time.append(chord_time[-1] + 2)
                        except KeyError:
                            root, cd_type = cds[0].split(':')
                            root = pitch_dict[root]
                            for i in range(insert_num):
                                for shift in _CHORD_KIND_PITCHES[cd_type]:
                                    mf.addNote(chord_track, channel, 48 + root + shift, chord_time[-1] + 2, 2, 75)
                                chord_time.append(chord_time[-1] + 2)

                    

                # print('begin sentence:', sen_idx)
                # для любых аккордов
                # for cd in cds:
                #     #print(cd)
                #     root, cd_type = cd.split(':')
                #     root = pitch_dict[root]
                #     # mf.addNote(chord_track, channel, 36+root, t, 2, 75)  # 36 is C3
                #     for shift in _CHORD_KIND_PITCHES[cd_type]:
                #         mf.addNote(chord_track, channel, 36 + root + shift, t, 2, 75)
                #     chord_time.append(t)
                #     t += 2

                # для части аккордов
                for cd in cds:
                #print(cd)
                    try:
                        chord_i = chord_dict[cd]
                        for shift in chord_i:
                            # channel = 1
                            mf.addNote(chord_track, channel, 48 + shift, t, 2, 50)
                        chord_time.append(t)
                        t += 2          
                    except KeyError:
                        root, cd_type = cd.split(':')
                        root = pitch_dict[root]
                        for shift in _CHORD_KIND_PITCHES[cd_type]:
                            mf.addNote(chord_track, channel, 48 + root + shift, t, 2, 75)
                        chord_time.append(t)
                        t += 2

            except IndexError:
                print('1: sen_idx: ', sen_idx)
                pass
        cnt += 1
        # это я временно добавила try
        try:
            if cnt == word_counter[sen_idx]:
                cnt = 0
                sen_idx += 1
        except IndexError:
            print('2: sen_idx: ', sen_idx)
            pass

    name += '.mid'

    if partly:
        name = './parts/' + name
    else:
        name = './tests/' + name

    with open(name, 'wb') as outf:
        mf.writeFile(outf)

    if with_lyrics:
        midi_obj = miditoolkit.midi.parser.MidiFile(name)
        lyrics = re.split(' |-',(' '.join(lyrics)))

        word_idx = 0    
        short_word = ''

        for word in lyrics:
            if word not in [',', '.', ''] and vowelcount(word)>0:
                # print(word)
                # print(word_idx)
                try:
                    note = midi_obj.instruments[0].notes[word_idx]
                except IndexError:
                    print('Word index: ', word_idx)
                    print(word)
                    print(notes)
                    print(midi_obj.instruments)

                midi_obj.lyrics.append(miditoolkit.Lyric(text=short_word, time=note.start))
                if len(short_word) > 0:
                    midi_obj.lyrics[-1].text += ' '
                
                short_word = ''
                midi_obj.lyrics[-1].text += word
                word_idx += 1
            else:
                if word in [',', '.', '']:
                    midi_obj.lyrics[-1].text += word
                else:
                    short_word += word

                # print(word)
                # print(midi_obj.lyrics) 
        
        midi_obj.dump(f'{name}', charset='utf-8')

        new_name = "{}.xml".format(name[:-4])

        os.system("mscore "+ name +" -o " + new_name) # это для того, чтобы отображать со словами
        
        score = music21.converter.parse(new_name)
    else:
        score = music21.converter.parse(name)

    return score
