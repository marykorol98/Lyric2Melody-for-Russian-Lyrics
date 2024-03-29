# Lyrics-based Melody and Harmony Generation for Russian Language

This repository is devoted to the master's thesis "Lyrics-based Melody and Harmony Generation for Russian Language" by Mariia Koroleva (ITMO University, supervisor: Petr Gladilin).

The solution represents the modified ROC model*, adapted to the Russian language. 

*Re-creation of Creations: A New Paradigm for Lyric-to-Melody Generation, Ang Lv, Xu Tan, Tao Qin, Tie-Yan Liu, Rui Yan, arXiv 2022.

## Installation Instructions:

1. Download the ROC model and melody pieces database from https://github.com/microsoft/muzic/tree/main/roc
2. Download the current repository files and add them to the original ROC project
3. To enable the automatic accentuation download the ru_core_new_md from https://github.com/natasha/natasha-spac, lemmas.dat and wordforms.dat from https://github.com/einhornus/russian_accentuation
4. To enable the conditioned chord generation download the model_chords_1-1 from https://drive.google.com/drive/folders/14fKdQJRXYhMAbMklJSlOMAUL18-gOBEX?usp=sharing and put it into the "conditioned" folder

## Inference

For inference use the same instructions as ROC's inference instructions with the following changes:

- you don't need a chord.txt file, since the chords are generated automatically
- there is an additional --conditioned argument, set to the "True" value by default in order to enable lyrics-conditioned chord generation. To disable it please type it with the "False" value


