# -*- coding: utf-8 -*-
import os
import sys
import cdb
import sqlite3
from collections import Counter, defaultdict
sys.path.insert(1, "/home/huang/work/CDB_handler")
from CDB_Reader import CDB_Reader
from utils import CASE_ENG, CASE_KATA, KATA_ENG, KATA_VER

class SupportSentences(object):
    def __init__(self, config, support_sentence_keys):
        self.config = config
        self.config.sid2pa = CDB_Reader(self.config.sid2pa)

        self._set_sids(support_sentence_keys)

    def _set_sids(self, support_sentence_keys):
        self.sids, self.rels, self.sents, self.pas = [], [], [], []

        raw_sids = self._get_raw_sids(support_sentence_keys)
        for raw_sid in raw_sids:
            self._parse_raw_sids(raw_sid)

        assert len(self.sids) == len(self.rels)
        assert len(self.sids) == len(self.sents)
        assert len(self.sids) == len(self.pas)

    def _get_raw_sids(self, support_sentence_keys):
        if self.config.key2sid.endswith("cdb.keymap"):
            key2sid_cdb = CDB_Reader(self.config.key2sid)
            raw_sids = [key2sid_cdb.get(key) for key in support_sentence_keys]

        elif self.config.key2sid.endswith(".sqlite"):
            conn = sqlite3.connect(self.config.key2sid)
            c = conn.cursor()

            raw_sids = []
            for key in support_sentence_keys:
                #print key
                condition_string = self.get_condition(key.split('-'))
                c.execute("select sids from pairs where %s" % condition_string)
                all_rows = c.fetchall()
                for row in all_rows:
                    raw_sids.append(row[0])

            conn.close()

        raw_sids = sum([x.split(',') for x in raw_sids if x is not None], [])
        return raw_sids

    def get_condition(self, keys):
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

    def _parse_raw_sids(self, raw_sid):
        sid = raw_sid.split(":")[0]
        rel = raw_sid.split(":")[1].split(";")[0]
        sent = self._get_sentence_by_sid(sid)
        pa = self._get_pa_by_sid(sid)
        if sent == None or pa == None:
            return

        self.sids.append(sid)
        self.rels.append(rel)
        self.sents.append(sent)
        self.pas.append(pa)

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

    def get_supArgs(self):
        supArgs = [defaultdict(list), defaultdict(list)]

        for pas in [x for x in self.pas if x is not None]:
            for index, pa in enumerate(pas):
                for case, arg in pa.items():
                    supArgs[index][case].append(arg)

        supArgs = [{case: dict(Counter(args)) for case, args in x.items()} for x in supArgs]
        return supArgs

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

    def get_conflict_dict(self):
        conflict_dict = defaultdict(int)
        for PAs in self.pas:
            PA1, PA2 = PAs
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
        return self.sids

