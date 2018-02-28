# -*- coding: utf-8 -*-
import sys
import random
import argparse
import cdb
from CDB_Reader import CDB_Reader
import yaml
import os.path
import ConfigParser
import itertools
from utils import CASE_ENG, ENG_KATA

def event_to_count(pred, arg_dict):
    cases = [case for case in CASE_ENG if case in arg_dict.keys()]

    args = [arg_dict[case] for case in cases]
    cases = [ENG_KATA[case] for case in cases]

    count_db_loc = "/windroot/huang/EventCounts_customized/all_count.cdb.keymap"
    count_db = CDB_Reader(count_db_loc)

    all_count = 0
    for arg_list in itertools.product(*args):
        query = '%s:%s' % ("##".join(["%s-%s" % x for x in zip(arg_list, cases)]), pred)
        count = count_db.get(query) 
        if count:
            all_count += int(count)

    return all_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', "--event", action="store", dest="event")
    parser.add_argument('--setting_file', action="store", dest="setting_file")
    options = parser.parse_args() 

    if options.setting_file:
        config = yaml.load(open(options.setting_file)) 

    print event_to_count(options.event)
    
