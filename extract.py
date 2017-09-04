# -*- coding: utf-8 -*-
import sys
import yaml
import argparse
from argparse import Namespace
from EventChain import EventChain

def setArgs(parser):
    subparsers = parser.add_subparsers(dest="_subcommand")

    task_parser = subparsers.add_parser("print_task")
    task_parser.add_argument("--arg_file", action="store", dest="arg_file")
    task_parser.add_argument("--config_file", action="store", dest="config_file")
    task_parser.add_argument("--task_file", action="store", dest="task_file")

    init_parser = subparsers.add_parser("init_event_chain")
    init_parser.add_argument("input_str", action="store")
    init_parser.add_argument("--config_file", action="store", dest="config_file")

    merge_parser = subparsers.add_parser("merge_tmp_db")
    merge_parser.add_argument("--config_file", action="store", dest="config_file")

def print_task(options):
    config_file = options.config_file
    arg_file = options.arg_file
    task_file = open(options.task_file, 'w')

    count = 0
    for line in open(arg_file).readlines():
        input_str = line.rstrip()
        task = 'python extract.py init_event_chain \"%s\" --config_file %s && echo %s done.' % (input_str, config_file, count)
        task_file.write(task + '\n')
        count += 1

    task_file.close()

def setEventChainConfig(config_file):
    config = yaml.load(open(config_file, 'r'))

    evs_config = Namespace()
    evs_config.gold_file = config['Raw']['GOLD']
    evs_config.word_replace_db = config['Raw']['WORD_REPLACE']
    evs_config.key2sid = config['Raw']['KEY_SID']
    evs_config.sid2pa = config['Raw']['SID_PA']
    evs_config.sid2sent_dir = config['Raw']['SID_SENT_DIR']
    evs_config.cf_cdb = config['Raw']['CF_CDB']
    evs_config.output_db = config['Output']['TMP_DB_PREFIX']

    return evs_config

def init_event_chain(options):
    evs_config = setEventChainConfig(options.config_file)
    evs = EventChain(evs_config, options.input_str)
    evs.export()

def merge_tmp_db(config_file):
    config = yaml.load(open(config_file, 'r'))['Output']

    ev_db = shelve.open(config['EVENT_PAIR'])
    feat_db = shelve.open(config['FEAT'])

    for f in utils.search_file_with_prefix(config['TMP_DB_PREFIX']):
        ID = f.split('_')[-1]
        tmp_db = shelve.open(f, flag='r')
        
        ev_db[ID] = tmp_db['ev']
        feat_db[ID] = tmp_db['feat']
        sys.stderr.write("id: %s written.\n" % ID)

    ev_db.close()
    feat_db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    setArgs(parser)
    options = parser.parse_args()

    if options._subcommand == "print_task":
        print_task(options.config_file)

    elif options._subcommand == "init_event_chain":
        init_event_chain(options)

    elif options._subcommand == "merge_tmp_db":
        merge_tmp_db(options.config_file)

