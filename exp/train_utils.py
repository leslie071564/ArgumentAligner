# -*- coding: utf-8 -*-
import os
import sys
import yaml
import shelve
import argparse
import random
exp_script_dir = os.path.dirname(os.path.realpath(__file__))
print_feat_script="%s/print_feature_file.py" % exp_script_dir

def setArgs(parser):
    subparsers = parser.add_subparsers(dest="_subcommand")

    train_parser = subparsers.add_parser("print_train_task")
    train_parser.add_argument("--config_file", action="store", dest="config_file")
    train_parser.add_argument("--key_file", action="store", dest="key_file")
    train_parser.add_argument("--output_dir", action="store", dest="output_dir")

    test_parser = subparsers.add_parser("print_test_task")
    test_parser.add_argument("--config_file", action="store", dest="config_file")
    test_parser.add_argument("--ids_file", action="store", dest="ids_file")
    test_parser.add_argument("--output_dir", action="store", dest="output_dir")

    choose_parser = subparsers.add_parser("print_choose_task")
    choose_parser.add_argument("--config_file", action="store", dest="config_file")
    choose_parser.add_argument("--ids_file", action="store", dest="ids_file")
    choose_parser.add_argument("--output_dir", action="store", dest="output_dir")

    init_parser = subparsers.add_parser("initialize")
    init_parser.add_argument("--config_file", action="store", dest="config_file")
    init_parser.add_argument("--ids_file", action="store", dest="ids_file")
    init_parser.add_argument("--key_file", action="store", dest="key_file")

def print_train_task(options):
    keys = get_ids(options.key_file)

    for key in keys:
        ev_id = key.split('_')[0]
        output_file = "%s/%s.txt" % (options.output_dir, ev_id)
        print "python %s print_train --config_file %s --key %s --output_file %s && echo %s done." % (print_feat_script, options.config_file, key, output_file, ev_id) 

def print_test_task(options):
    ids = get_ids(options.ids_file)
    for ev_id in ids:
        output_file = "%s/%s.txt" % (options.output_dir, ev_id)
        print "python %s print_test --config_file %s --id %s --output_file %s && echo %s done." % (print_feat_script, options.config_file, ev_id, output_file, ev_id) 

def print_choose_task(options):
    ids = get_ids(options.ids_file)

    for ev_id in ids:
        output_file = "%s/%s.txt" % (options.output_dir, ev_id)
        print "python %s print_test --config_file %s --id %s --output_file %s --only_gold_align && echo %s done." % (print_feat_script, options.config_file, ev_id, output_file, ev_id) 

def initilize_model(options):
    ids = get_ids(options.ids_file)
    key_file = open(options.key_file, 'w')
    
    config = yaml.load(open(options.config_file, 'r'))
    FEAT_DB = shelve.open(config['db']['feat_db'], flag='r')

    for ev_id in ids:
        cf_pairs = [x for x in FEAT_DB[ev_id]['features'].keys() if x != 'general']
        #key = "%s_0_0_0" % ev_id
        key = "%s_%s_0" % (ev_id, random.choice(cf_pairs))
        key_file.write(key + '\n')

def get_ids(ids_file):
    ids_file = open(ids_file, 'r')
    ids = map(str.strip, ids_file.readlines())
    ids_file.close()

    return ids

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    setArgs(parser)
    options = parser.parse_args() 

    if options._subcommand == "print_train_task":
        print_train_task(options)

    elif options._subcommand == "print_test_task":
        print_test_task(options)

    elif options._subcommand == "print_choose_task":
        print_choose_task(options)

    elif options._subcommand == "initialize":
        initilize_model(options)
