# -*- coding: utf-8 -*-
import sys
import yaml
import argparse
import shelve
from argparse import Namespace
from collections import defaultdict
from math import log
import utils
import itertools
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
    init_parser.add_argument("--debug", action="store_true", dest="debug")

    merge_parser = subparsers.add_parser("merge_tmp_db")
    merge_parser.add_argument("--config_file", action="store", dest="config_file")

def print_task(options):
    config_file = options.config_file
    arg_file = options.arg_file
    task_file = open(options.task_file, 'w')

    count = 0
    for line in open(arg_file).readlines():
        input_str = line.rstrip()
        task = 'nice -n 19 python extract.py init_event_chain \"%s\" --config_file %s && echo %s done.' % (input_str, config_file, count)
        task_file.write(task + '\n')
        count += 1

    task_file.close()

def setEventChainConfig(config_file):
    config = yaml.load(open(config_file, 'r'))

    evs_config = Namespace()
    config_raw = config['Raw']
    evs_config.gold_file = config_raw['GOLD']
    evs_config.word_replace_db = config_raw['WORD_REPLACE']
    evs_config.key2sid = config_raw['KEY_SID']
    evs_config.sid2pa = config_raw['SID_PA']
    evs_config.sid2sent_dir = config_raw['SID_SENT_DIR']

    db_locs = config['DB']
    evs_config.cf_cdb = db_locs['CF_CDB']
    evs_config.count_db = db_locs['COUNT_DB']
    evs_config.knp_index_db = db_locs['KNP_INDEX_DB']
    evs_config.knp_parent_dir = db_locs['KNP_PARENT_DIR']
    evs_config.knp_sub_index_length = int(db_locs['KNP_SUB_LENGTH'])

    evs_config.output_db = config['Output']['TMP_DB_PREFIX']

    return evs_config

def init_event_chain(options):
    evs_config = setEventChainConfig(options.config_file)
    evs = EventChain(evs_config, options.input_str, debug=options.debug)
    evs.export()

def merge_tmp_db(config_file):
    config = yaml.load(open(config_file, 'r'))['Output']

    ev_db = shelve.open(config['EVENT_PAIR'])
    feat_db = shelve.open(config['FEAT'])
    ids_file = open(config['IDS'], 'wb')

    doc_freq = defaultdict(int)
    for f in utils.search_file_with_prefix(config['TMP_DB_PREFIX']):
        ID = f.split('_')[-1]
        tmp_db = shelve.open(f, flag='r')
        
        ev_db[ID] = tmp_db['ev']
        feat_db[ID] = tmp_db['feat']
        ids_file.write('%s\n' % ID)
        sys.stderr.write("id: %s written.\n" % ID)

    ev_db.close()
    feat_db.close()
    ids_file.close()

    set_tf_idf(config['EVENT_PAIR'], config['FEAT'])

def set_tf_idf(ev_db, feat_db):
    ev_db = shelve.open(ev_db)
    feat_db = shelve.open(feat_db)

    nums = ev_db.keys()
    N = len(nums)

    doc_freq = defaultdict(int)
    for ID in nums:
        ev_dict = ev_db[ID]
        for word, count in ev_dict['context_words'].iteritems():
            doc_freq[word] += 1

    for ID in nums:
        feat_dict = feat_db[ID]
        ev_dict = ev_db[ID]

        tf_idf_dict = {}
        for word in ev_dict['cArgScores'].keys():
            tf_idf_dict[word] = ev_dict['context_words'][word] * log(float(N) / doc_freq[word])

        ev_dict['tf_idf'] = tf_idf_dict
        
        feat_dict['features']['general']['cArg'], ev_dict['feature_contributors']['general']['cArg'] = _get_contextFeatDict(ev_dict['cArgScores'], tf_idf_dict)
        feat_dict['features']['general']['cCase'], ev_dict['feature_contributors']['general']['cCase'] = _get_contextFeatDict(ev_dict['cCaseScores'], tf_idf_dict, normalize=True)

        ev_db[ID] = ev_dict
        feat_db[ID] = feat_dict

    ev_db.close()
    feat_db.close()

def _get_contextFeatDict(contextDicts, weightDict, normalize=False):
    contextFeatDict = defaultdict(float)
    contributorDict = defaultdict(str)

    for context_word, weight in weightDict.iteritems():
        s1, s2 = contextDicts[context_word]
        for c1, c2 in itertools.product(s1.keys(), s2.keys()):
            score = weight * s1[c1] * s2[c2]
            contextFeatDict['%s-%s' % (c1, c2)] += score
            contributorDict['%s-%s' % (c1, c2)] += "%s(%.3f)<br>" % (context_word, score)

    if normalize:
        sup_sum = sum(contextFeatDict.values())
        if sup_sum:
            contextFeatDict = {case : score/sup_sum for case, score in contextFeatDict.iteritems()}

    return (dict(contextFeatDict), dict(contributorDict))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    setArgs(parser)
    options = parser.parse_args()

    if options._subcommand == "print_task":
        print_task(options)

    elif options._subcommand == "init_event_chain":
        init_event_chain(options)

    elif options._subcommand == "merge_tmp_db":
        merge_tmp_db(options.config_file)


