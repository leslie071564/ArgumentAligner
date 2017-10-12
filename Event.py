# -*- coding: utf-8 -*-
import sys
import re
import operator
import itertools
import xml.etree.ElementTree as ET
from collections import defaultdict, namedtuple

sys.path.insert(1, "/home/huang/work/CDB_handler")
from CDB_Reader import CDB_Reader
import utils
from utils import CASE_ENG, ENG_HIRA, ENG_KATA
from CaseFrame import CaseFrame
from event_to_counts import event_to_count
### where?
CF = namedtuple('CF', ['cf_id', 'cf_str', 'rel_score'])

class Event(object):
    pred_pattern = r"[12]([vjn])([APCKML])(.+)$"
    arg_pattern = r"([12])([gwnod])(\d*)(.+)$"

    VOICE = ['A','P','C','K','M','L']
    VOICE_SUFFIX = [[""],[u"[受動]",u"[受動│可能]"], [u"[使役]"], [u"[可能]"], [u"[もらう]"], [u"[判]"]]
    VOICE2SUFFIX = dict(zip(VOICE, VOICE_SUFFIX))

    NEG = ['v', 'j', 'n']
    NEG_SUFFIX = ["", u"[準否定]", u"[否定]"]
    NEG2SUFFIX = dict(zip(NEG, NEG_SUFFIX))

    def __init__(self, pred, args, pred_key, config, debug=False):
        self.config = config
        self.debug = debug

        self._set_predicate(pred)
        self._set_givenArgs(args, pred_key)

    def _set_predicate(self, pred_str):
        regex = re.compile(Event.pred_pattern)
        self.predNegation, self.predVoice, self.predStem = regex.search(pred_str).groups()
        self.predType = u"判".encode('utf-8') if self.predVoice == 'L' else u"動".encode('utf-8')

        self._set_predRep()
        self._set_predAmb()

        if self.debug:
            print self.predRep, '->', " ".join(self.predAmb)

    def _set_predRep(self):
        self.predRep = utils.getPredRep(self.predStem, self.predVoice)

    def _set_predAmb(self):
        self.predAmb = []

        predAmb = utils.getAmbiguousPredicate(self.predRep)
        if predAmb:
            self.predAmb.append(predAmb)

        ### MODIFY
        if self.predVoice == 'P':
            predAmb = self.predRep.replace("+れる/れる", "+られる/られる")
            self.predAmb.append(predAmb)

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
        neg_suffix = Event.NEG2SUFFIX[self.predNegation]
        voice_suffix = Event.VOICE2SUFFIX[self.predVoice]

        predKeys = map(lambda x: "%s%s%s" % (pred_stem, neg_suffix, x.encode('utf-8')), voice_suffix)
        return predKeys 

    def _get_argKeys(self, upper_limit=3):
        argKeys = []
        for case in set(CASE_ENG) & set(self.givenArgs.keys()):
            case_kata = ENG_KATA[case].encode('utf-8')
            case_key = ["%s|%s|" % (arg, case_kata) for arg in self.givenArgs[case]]
            argKeys.append(case_key)

        argKeys = ["".join(x) for x in itertools.product(*argKeys)]
        ### MODIFY
        if len(argKeys) > upper_limit:
            argKeys = argKeys[:upper_limit]
        return argKeys

    def set_supArgs(self, supArgs):
        self.supArgs = supArgs

    def set_cfs(self, max_cf_num=10, trim_threshold=0.1):
        candidate_cfs = self._get_all_cfs()
        if candidate_cfs == []:
            return

        self.cfs = sorted(candidate_cfs, key=operator.attrgetter('rel_score'), reverse=True)[:max_cf_num]
        max_score = self.cfs[0].rel_score * trim_threshold
        if max_score != 0.0:
            self.cfs = [cf for cf in self.cfs if cf.rel_score >= max_score]

        if self.debug:
            print "num of cf: %s" % len(self.cfs)
            print "\n".join(["\t[%s]: %s (%.3f)" % (cf.cf_id, cf.cf_str, cf.rel_score) for cf in self.cfs])

    def _get_all_cfs(self):
        cf_ids = self._get_cf_ids()

        candidate_cfs = []
        for cf_id in cf_ids:
            cf = CaseFrame(self.config, cf_id=cf_id)
            cf_rel = cf.getRelevanceScore(self.supArgs)
            cf_str = cf.get_cf_str()

            cf_tuple = CF(cf_id, cf_str, cf_rel)
            candidate_cfs.append(cf_tuple)

        return candidate_cfs

    def _get_cf_ids(self):
        cf_cdb = CDB_Reader(self.config.cf_cdb)
        predicates = [self.predRep] + self.predAmb
        
        cf_ids = []
        for pred in predicates:
            predCounts = cf_cdb.get(pred)
            if predCounts != None and self.predType in predCounts:
                predCountDict = {x.split(':')[0]: x.split(':')[1] for x in predCounts.split('/')}
                cf_count = int(predCountDict[self.predType])
                cf_ids += ["%s:%s%s" % (pred, self.predType, index) for index in xrange(1, cf_count + 1)]
            else:
                sys.stderr.write('No case frame found for predicate %s:%s\n' % (pred, self.predType) )

            if pred == self.predRep and cf_ids != []:
                break

        return cf_ids

    def get_contextArgScore(self, context_word):
        if not hasattr(self, 'contextArgDenom'):
            self.get_contextArgDenom()

        sup_dict = defaultdict(int)
        for pred, denom in self.contextArgDenom.iteritems():
            for this_case in CASE_ENG:
                if this_case not in denom.keys():
                    continue
                denomCount = denom[this_case]

                arg_dict = self.givenArgs.copy()
                arg_dict.update({this_case: [context_word]})
                numerCount = event_to_count(pred, arg_dict)

                supScore = round(float(numerCount) / denomCount, 3)
                if supScore != 0:
                    sup_dict[this_case] = max(sup_dict[this_case], supScore)
        return dict(sup_dict)

    def get_contextArgDenom(self):
        """
        Get the counts of the Evnet Predicate taking arguments in each case, cosidering givenArgs.
            ex: [切手を貼る] => count(X-が/に/で 切手を 貼る)
        """
        contextArgDenom = {}
        predicates = [self.predRep]
        if self.predAmb:
            predicates += self.predAmb

        for pred in predicates:
            pred_dict = {}

            for this_case in set(CASE_ENG) - set(self.givenArgs.keys()):
                arg_dict = self.givenArgs.copy()
                arg_dict.update({this_case: ['X']})
                count = event_to_count(pred, arg_dict)
                if count != 0:
                    pred_dict[this_case] = count

            if pred_dict != {}:
                contextArgDenom[pred] = pred_dict
        self.contextArgDenom = contextArgDenom

    def get_contextCaseScore(self, context_word):
        predicates = [self.predRep]
        if self.predAmb:
            predicates += self.predAmb

        contextCaseScores = {}
        for pred in predicates:
            for this_case in set(CASE_ENG) - set(self.givenArgs.keys()):
                arg_dict = self.givenArgs.copy()
                arg_dict.update({this_case: [context_word]})
                count = event_to_count(pred, arg_dict)
                if count:
                    contextCaseScores[this_case] = count
        if contextCaseScores != {}:
            sup_sum = sum(contextCaseScores.values())
            contextCaseScores = {case : round(float(score)/sup_sum, 3) for case, score in contextCaseScores.iteritems()}

        return contextCaseScores

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
        export_dict['predAmb'] = self.predAmb

        export_dict['givenArgs'] = self.givenArgs
        export_dict['supArgs'] = self.supArgs

        export_dict['cfs'] = self.cfs

        return export_dict

