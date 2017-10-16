# -*- coding: utf-8 -*-
import os
import sys
import cdb
import sqlite3
import operator
from collections import Counter, defaultdict, namedtuple
from pyknp import KNP
sys.path.insert(1, "/home/huang/work/CDB_handler")
from CDB_Reader import CDB_Reader
import utils
from utils import CASE_ENG, CASE_KATA, KATA_ENG, KATA_VER
from db_interface import KNP_extractor

### where?
supSent = namedtuple('supSent', ['sid', 'rel', 'raw_sentence', 'pa_struc'])

class SupportSentences(object):
    def __init__(self, config, support_sentence_keys):
        self.config = config
        self.config.sid2pa = CDB_Reader(self.config.sid2pa)

        self._set_sents(support_sentence_keys)

    def _set_sents(self, support_sentence_keys):
        self.sents = []

        for sid in self._get_sids(support_sentence_keys):
            sent_tuple = self._get_sentence_tuple(sid)
            if sent_tuple != None:
                self.sents.append(sent_tuple)

    def _get_sids(self, support_sentence_keys):
        if self.config.key2sid.endswith("cdb.keymap"):
            key2sid_cdb = CDB_Reader(self.config.key2sid)
            sids = [key2sid_cdb.get(key) for key in support_sentence_keys]

        elif self.config.key2sid.endswith(".sqlite"):
            conn = sqlite3.connect(self.config.key2sid)
            c = conn.cursor()

            sids = []
            for key in support_sentence_keys:
                query_condition = self._get_sqlQueryCondition(key.split('-'))
                c.execute("select sids from pairs where %s" % query_condition)
                all_rows = c.fetchall()
                sids += [row[0] for row in all_rows]

            conn.close()

        sids = sum([x.split(',') for x in sids if x is not None], [])
        return sids

    def _get_sqlQueryCondition(self, keys):
        conditions = []
        for index, key in enumerate(keys):
            pred, args = key.split('|')[-1], key.split('|')[:-1]

            conditions.append('pa%s=\"%s\"' % (index + 1, pred))
            for arg, case_k in zip(args[0::2], args[1::2]):
                case = KATA_VER[case_k.decode('utf-8')]
                cond = 'pa%s_%s=\"%s\"' % (index + 1, case, arg)
                conditions.append(cond)

        condition_string = ' and '.join(conditions)
        return condition_string

    def _get_sentence_tuple(self, raw_sid):
        sid = raw_sid.split(":")[0]
        rel = raw_sid.split(":")[1].split(";")[0]
        sent = self._get_sentence_by_sid(sid)
        pa = self._get_pa_by_sid(sid)
        if sent == None or pa == None:
            return None

        return supSent(sid, rel, sent, pa)

    def _get_sentence_by_sid(self, sid):
        sid = sid.split('%')[0]
        sid_components = sid.split('-')

        if os.path.basename(self.config.sid2sent_dir) == "tsubame.results.orig-cdb":
            sub_dirs = [sid_components[0], sid_components[1][:4], sid_components[1][:6]]
            sub_dir_str = "/".join(sub_dirs)

        elif os.path.basename(self.config.sid2sent_dir) == "v2006-2015.text-cdb": 
            if 'data' in sid:
                sid_components = [x for x in sid_components if x != ""]
                sub_dirs = [sid_components[0], sid_components[1]] + list(sid_components[2][:3]) + [sid_components[2][:4]]
                sub_dir_str = "/".join(sub_dirs)
            else:
                sub_dirs = [sid_components[0]] + list(sid_components[1][:3]) + [sid_components[1][:4]]
                sub_dir_str = "/".join(sub_dirs)

        sid2sent = "%s/%s.cdb" % (self.config.sid2sent_dir, sub_dir_str)
        SID2SENT = cdb.init(sid2sent.encode('utf-8'))

        sent = SID2SENT.get(sid)
        if sent == None:
            sys.stderr.write("Cannot retrieve sentence of sid:%s.\n" % sid)
        return sent
    
    def _get_pa_by_sid(self, sid):
        paStr = self.config.sid2pa.get("%s:" % sid)
        if paStr == None:
            sys.stderr.write("Cannot retrieve PAS for sid:%s.\n" % sid)
            return None
        else:
            return self._parse_pa_str(paStr)

    def _parse_pa_str(self, pa_str):
        pa_str = pa_str.split(" | ")[0]
        pa1, pa2 = map(lambda x: x.split(" "), pa_str.split(" - "))

        pa_dicts = []
        for pa_components in [pa1, pa2]:
            kata_cases = pa_components[1::2]
            cases = [KATA_ENG[x.decode('utf-8')] for x in kata_cases if x in CASE_KATA]
            args = pa_components[0::2]

            pa_dict = dict(zip(cases, args))
            pa_dicts.append(pa_dict)

        return pa_dicts

    def get_supArgs(self):
        supArgs = [defaultdict(list), defaultdict(list)]

        for sent_tuple in self.sents:
            pas = sent_tuple.pa_struc
            for index, pa in enumerate(pas):
                for case, arg in pa.items():
                    supArgs[index][case].append(arg)

        supArgs = [{case: dict(Counter(args)) for case, args in x.items()} for x in supArgs]
        return supArgs

    def get_context_words(self, sentence_size_limit=100):
        knp = KNP()
        knp_extractor = KNP_extractor(self.config.knp_index_db, self.config.knp_parent_dir, self.config.knp_sub_index_length)
        context_words = Counter()
        for index, sent_tuple in enumerate(self.sents[:sentence_size_limit]):
            sid = sent_tuple.sid.split('%')[0]
            sup_knp = knp_extractor.get_knp(sid)
            if not sup_knp:
                continue

            result = knp.result(sup_knp.decode('utf-8'))
            context_words.update(self._get_sentence_args(result))
        
        context_words = dict(context_words)
        return context_words

    def _get_sentence_args(self, result):
        all_args = []

        for tag_id, tag in enumerate(result.tag_list()):
            if u"<用言:" in tag.fstring:    # remove predicates.
                continue

            prev_tag = result.tag_list()[tag_id - 1] if tag_id else None
            arg = utils.getNounRep(tag, prev_tag)
            if arg:
                arg = arg.rstrip('va')  # remove trailing 'v'/'a' characters
                all_args.append(arg.encode('utf-8'))
        return all_args

    def getConflictScores(self):
        conflict_dict = defaultdict(int)
        for sent_tuple in self.sents:
            PA1, PA2 = sent_tuple.pa_struc
            for c1 in filter(lambda x: x in CASE_ENG, PA1.keys()):
                conflict_dict["%s1" % c1] += 1
                for c2 in filter(lambda x: x in CASE_ENG, PA2.keys()):
                    conflict_dict["%s2" % c2] += 1

                    conflict_dict["%s-%s" % (c1, c2)] += 1
                    arg1, arg2 = PA1[c1], PA2[c2]
                    if arg1 != arg2:
                        conflict_dict["%sX%s" % (c1, c2)] += 1
        return dict(conflict_dict)

    def export(self):
        return list(map(operator.attrgetter('sid'), self.sents))

