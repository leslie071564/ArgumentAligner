# -*- coding: utf-8 -*-
import re
import sys
import argparse
from collections import namedtuple


INPUT_PAS_TYPES = ['gold', '170724', '170905']

DB_DEFS = {'CF_DB': '/windroot/huang/cf_cdbs/20170502/new_cdb/new_cf.cdb.keymap',\
           'COUNT_DB': '/windroot/huang/EventCounts/EventCounts_customized/all_count.cdb.keymap',\

          }

GOLD_DEFS = {'arg_file': '$extract_dir/input_pas.txt',\
                 'gold_file': '/windroot/huang/argumentAligner/goldExp/gold.txt',\
                 'input_dir': '/zinnia/huang/EventKnowledge/data',\
                 'word_replace': '$input_dir/word_replace_db/wordreplace.cdb',\
                 'key2sid': '$input_dir/pa_pairs_relation_db/pa_pairs_relation.cdb.keymap',\
                 'sid2pa': '$input_dir/sid2pa/sid2pa.cdb.keymap',\
                 'sid2sent': '',\
                }
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pas_type", choices=INPUT_PAS_TYPES)

    parser.add_argument("--arg_file", action="store", dest="arg_file")
    parser.add_argument("--gold_file", action="store", dest="gold_file")
    parser.add_argument("--extract_dir", action="store", dest="extract_dir")

    parser.add_argument("--config_fn", action="store", dest="config_fn")

    options = parser.parse_args() 
    print vars(options)
