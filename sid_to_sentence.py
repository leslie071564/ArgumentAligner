# -*- coding: utf-8 -*-
import sys
import yaml
import shelve
import argparse
from utils import get_sentence_by_sid

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="store", dest="id")
    parser.add_argument("--ev_db", action="store", dest="ev_db")
    parser.add_argument("--sid2sent", action="store", default="/pear/share/www-uniq/v2006-2015.text-cdb", dest="sid2sent")
    options = parser.parse_args() 
   
    ev_db = shelve.open(options.ev_db, flag='r')
    ev_dict = ev_db[options.id]

    sents = []
    for sid in ev_dict['supSents']:
        sent = get_sentence_by_sid(sid, options.sid2sent)
        if sent:
            sents.append(sent)

    print "<br>".join(sents)
    
