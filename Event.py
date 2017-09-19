# -*- coding: utf-8 -*-
import sys
import re
import operator
import itertools
import xml.etree.ElementTree as ET
sys.path.insert(1, "/home/huang/work/CDB_handler")
from CDB_Reader import CDB_Reader
import utils
from utils import CASE_ENG, ENG_HIRA, ENG_KATA, NEG2SUFFIX, VOICE2SUFFIX
from CaseFrame import CaseFrame

class Event(object):
    pred_pattern = r"[12]([vjn])([APCKML])(.+)$"
    arg_pattern = r"([12])([gwnod])(\d*)(.+)$"

    def __init__(self, pred, args, pred_key, config, debug=False):
        self.config = config
        self.debug = debug

        self._set_predicate(pred)
        self._set_givenArgs(args, pred_key)

    def _set_predicate(self, pred_str):
        regex = re.compile(Event.pred_pattern)
        self.predNegation, self.predVoice, self.predStem = regex.search(pred_str).groups()

        self.predRep = utils.getPredRep(self.predStem, self.predVoice)
        self.predAmb = utils.getAmbiguousPredicate(self.predRep)
        ###
        if self.predVoice == 'P':
            self.predAmb = self.predRep.replace("+れる/れる", "+られる/られる")
        ###
        self.predType = u"判".encode('utf-8') if self.predVoice == 'L' else u"動".encode('utf-8')

    def _set_givenArgs(self, args, pred_key):
        self.givenArgs = {}
        regex = re.compile(Event.arg_pattern)
        for arg_str in args:
            place, case, class_num, noun_str = regex.search(arg_str).groups()
            if class_num == "":
                self.givenArgs[case] = noun_str.split(",")
            else:
                class_id = "%s%s%s" % (place, case, class_num)
                self.givenArgs[case] = self._replace_word(pred_key, class_id, noun_str)

        self.givenArgsRep = utils.getArgsRep(self.givenArgs)
        if self.debug:
            print "\tevent: %s %s" % (self.givenArgsRep, self.predRep)

    def _replace_word(self, pred_key, class_id, noun_str=""):
        word_replace_cdbs = utils.search_file_with_prefix(self.config.word_replace_db)

        all_args = utils.search_cdbs(word_replace_cdbs, pred_key)
        all_args = sum(map(lambda x: x.split('|'), all_args), [])

        class_args = filter(lambda x: x.startswith("%s-" % class_id), all_args)
        class_args = sum([x.split('-')[-1].split(':') for x in class_args], [])
        class_args = map(lambda x: x.split('#')[0], class_args)

        if not class_args and noun_str != "":
            noun_str = re.sub(r"[\(\)]", "", noun_str)
            noun_str = re.sub(r"\.", "", noun_str)
            class_args = noun_str.split(",")

        return class_args

    def get_eventKeys(self):
        arg_keys, pred_keys = self._get_argKeys(), self._get_predKeys()
        eventKeys = ["%s%s" % (arg, pred) for arg, pred in itertools.product(arg_keys, pred_keys)]
        return eventKeys

    def _get_predKeys(self): 
        pred_stem = self.predStem if self.predVoice in ['P', 'C'] else self.predRep
        neg_suffix = NEG2SUFFIX[self.predNegation]
        voice_suffix = VOICE2SUFFIX[self.predVoice]

        predKeys = map(lambda x: "%s%s%s" % (pred_stem, neg_suffix, x.encode('utf-8')), voice_suffix)

        return predKeys 

    def _get_argKeys(self, upper_limit=3):
        argKeys = []
        for case in set(CASE_ENG) & set(self.givenArgs.keys()):
            case_kata = ENG_KATA[case].encode('utf-8')
            case_key = ["%s|%s|" % (arg, case_kata) for arg in self.givenArgs[case]]
            argKeys.append(case_key)

        argKeys = ["".join(x) for x in itertools.product(*argKeys)]
        if len(argKeys) > upper_limit:
            argKeys = argKeys[:upper_limit]
        return argKeys

    def set_supArgs(self, supArgs):
        self.supArgs = supArgs

    def set_cfs(self, max_cf_num=10):
        self.cfs, self.cf_rels, self.cf_strs = [], {}, {}
        self._get_all_cfs()
        if len(self.cfs) == 0:
            return

        self.cf_rels = sorted(self.cf_rels.items(), key=operator.itemgetter(1), reverse=True)
        max_score = self.cf_rels[0][-1]
        if max_score == 0.0:
            self.cfs = self.cfs[:10]
        else:
            self.cfs = []
            for cf_id, cf_rel in self.cf_rels[:10]:
                if cf_rel < max_score * 0.1:
                    break
                self.cfs.append(cf_id)

        self.cf_rels = dict(self.cf_rels)
        self.cfs = [x for x in self.cfs if x in self.cf_rels.keys()]
        self.cf_rels = {cf_id: self.cf_rels[cf_id] for cf_id in self.cfs}
        self.cf_strs = {cf_id: self.cf_strs[cf_id] for cf_id in self.cfs}

        assert len(self.cfs) == len(self.cf_rels)
        assert len(self.cfs) == len(self.cf_strs)

        if self.debug:
            print "num of cf: %s" % len(self.cfs)
            print "\n".join(["\t[%s]: %s (%.3f)" % (cf_id, self.cf_strs[cf_id], self.cf_rels[cf_id]) for cf_id in self.cfs])

    def _get_all_cfs(self):
        self.cfs = self._get_cf_ids(self.predRep)
        if self.predAmb and self.cfs == []:
            self.cfs += self._get_cf_ids(self.predAmb)

        for cf_id in self.cfs:
            cf = CaseFrame(self.config, cf_id=cf_id)
            cf_rel = cf.getRelevanceScore(self.supArgs)
            cf_str = cf.get_cf_str()

            self.cf_rels[cf.id] = cf_rel
            self.cf_strs[cf.id] = cf_str

    def _get_cf_ids(self, predSurface):
        if not predSurface:
            return []

        CF = CDB_Reader(self.config.cf_cdb)
        predCounts = CF.get(predSurface)
        if predCounts is None or self.predType not in predCounts:
            sys.stderr.write("Cannot find predicate %s.\n" % predSurface)
            return []

        predCounts = {x.split(':')[0]: x.split(':')[1] for x in predCounts.split('/')}
        cf_prefix = "%s:%s" % (predSurface, self.predType)
        cf_count = int(predCounts[self.predType])

        cf_ids = ["%s%s" % (cf_prefix, index) for index in xrange(1, cf_count + 1)]
        return cf_ids

    def get_eventRep(self):
        evRep = "%s %s" % (self.get_argsRep(), self.predRep)
        return evRep.lstrip()

    def get_argsRep(self):
        arg_reps = ["%s %s" % (arg_list[0], ENG_HIRA[case].encode('utf-8')) for case, arg_list in self.givenArgs.items()]
        return " ".join(arg_reps)

    def export(self):
        export_dict = {}
        export_dict['eventRep'] = self.get_eventRep()

        export_dict['predRep'] = self.predRep
        export_dict['givenArgs'] = self.givenArgs
        export_dict['supArgs'] = self.supArgs

        export_dict['cfs'] = self.cfs
        export_dict['cf_scores'] = self.cf_rels
        export_dict['cf_reps'] = self.cf_strs

        return export_dict

