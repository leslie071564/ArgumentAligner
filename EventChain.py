# -*- coding: utf-8 -*-
import sys
import re
import shelve
import itertools
from subprocess import check_output
from collections import defaultdict
from Event import Event
from CaseFrame import CaseFrame
from SupportSentences import SupportSentences
import utils
from utils import cosineSimilarity

class EventChain(object):
    input_pattern = r"(.+) {(.+)} => {(.+)} .*"
    def __init__(self, config, arg_str, debug=False):
        self.config = config
        self.debug = debug

        self._init_events(arg_str)
        self._init_gold()
        # may move to somewhere else
        self.set_support_sentences()
        self.set_event_cfs()
        # may move to somewhere else

    def _init_events(self, arg_str):
        regex = re.compile(EventChain.input_pattern)
        ID, ev1, ev2 = regex.search(arg_str).groups()
        if self.debug:
            print "# %s %s => %s" % (ID, ev1, ev2)

        self.id = ID
        self.events = []
        self.add_events([ev1, ev2])

    def add_events(self, ev_strs):
        raw_preds, raw_args = [], []
        for ev_str in ev_strs:
            raw_pred, raw_arg = ev_str.split(':')[0], ev_str.split(':')[1:]

            raw_preds.append(raw_pred)
            raw_args.append(raw_arg)

        pred_key = "-".join(raw_preds)
        for raw_pred, raw_arg in zip(raw_preds, raw_args): 
            ev = Event(raw_pred, raw_arg, pred_key, self.config, self.debug)
            self.events.append(ev)

    def _init_gold(self):
        if self.config.gold_file == 'None':
            self.goldRaw, self.gold, self.goldSets = None, None, []
            return

        command = 'grep \"^%s\" %s' % (self.id, self.config.gold_file)
        line = check_output(command, shell=True)
        gold_align = line.rstrip().split('|')[-1].split()

        self.goldRaw = gold_align
        self.gold = utils.getExpandedAlign(gold_align)
        self.goldSets = utils.getAllPossibleAlign(gold_align) 
        
        if self.debug:
            print "gold:", self.goldRaw, "gold sets:", self.goldSets

    def set_support_sentences(self): 
        support_sentences_keys = self._get_support_sentences_keys()
        self.supSents = SupportSentences(self.config, support_sentences_keys) 

        self._set_event_supArgs()
        self._set_contextScores()

        if self.debug:
            print "Support sentence extraction keys:\n\t%s" % ("\n\t".join(support_sentences_keys))
            print "Number of support sentences extracted: %d" % len(self.supSents.sids)
            print "context words:", ' '.join(self.context_words)
        
    def _get_support_sentences_keys(self):
        event_keys = [ev.get_eventKeys() for ev in self.events]
        support_sentence_keys = ["-".join(key_list) for key_list in itertools.product(*event_keys)]
        return support_sentence_keys

    def _set_event_supArgs(self):
        supArgs = self.supSents.get_supArgs()
        for ev, supArg in itertools.izip(self.events, supArgs):
            ev.set_supArgs(supArg)
    
    def _set_contextScores(self):
        self.context_words = self.supSents.get_context_words()

        self.set_contextArgScores()
        self.set_contextCaseScores()
        
    def set_contextArgScores(self, threshold=0):
        contextArgScores = {}

        for context_word, count in self.context_words.iteritems():
            if count <= threshold:
                continue

            score_dicts = []
            for ev in self.events:
                score_dict = ev.get_contextArgScore(context_word)
                if not score_dict:
                    break
                score_dicts.append(score_dict)
            else:
                contextArgScores[context_word] = score_dicts

        self.contextArgScores = contextArgScores

    def set_contextCaseScores(self, threshold=0):
        contextCaseScores = {}
        for context_word, count in self.context_words.iteritems():
            if count <= threshold:
                continue

            score_dicts = []
            for ev in self.events:
                score_dict = ev.get_contextCaseScore(context_word)
                if not score_dict:
                    break
                print context_word, score_dict
                score_dicts.append(score_dict)
            else:
                contextCaseScores[context_word] = score_dicts
        print contextCaseScores
        self.contextCaseScores = contextCaseScores
            
    def set_event_cfs(self):
        for ev in self.events:
            ev.set_cfs()

        if self.debug:
            if len(ev.cfs) == 0:
                print "No CaseFrame found for event-id: %s (%s)" % (self.id, ev.predRep)

    def getAllFeats(self, max_cf_num=10, combined_cf=False, get_contributors=False):
        all_features_dict, feature_contributors = {}, {}
        all_features_dict['general'], feature_contributors['general'] = self.getGeneralFeats(get_contributors=get_contributors)

        ev1, ev2 = self.events
        cfs1, cfs2 = ev1.cfs, ev2.cfs

        for i in xrange( min(max_cf_num, len(cfs1)) ):
            for j in xrange( min(max_cf_num, len(cfs2)) ):
                cf1 = CaseFrame(self.config, cf_id=cfs1[i])
                cf2 = CaseFrame(self.config, cf_id=cfs2[j])
                cf_nums = "%s_%s" % (i, j)
                all_features_dict[cf_nums], feature_contributors[cf_nums] = self.getCfFeats(cf1, cf2, get_contributors=get_contributors)

        # combined cf:
        return all_features_dict, feature_contributors

    def getGeneralFeats(self, get_contributors=False):
        general_dict, general_contributors = {}, {}
        general_dict['postPred'] = self.events[1].givenArgs.keys()
        general_dict['conflict'] = self.supSents.get_conflict_dict()
        general_dict['sup'] = self.getSupFeats()

        """
        general_dict['cArg'], general_contributors['cArg'] = self.get_context_features("contextArgScores", get_contributors=True)
        general_dict['cCase'], general_contributors['cCase'] = self.get_context_features("contextCaseScores", get_contributors=True)
        """
        return general_dict, general_contributors

    def getSupFeats(self):
        sup_feature_dict = {}
        sup1, sup2 = [ev.supArgs for ev in self.events]
        for c1, c2 in itertools.product(sup1.keys(), sup2.keys()):
            align = "%s-%s" % (c1, c2)
            sim = round(cosineSimilarity(sup1[c1], sup2[c2]), 3)
            if sim:
                sup_feature_dict[align] = sim
        return sup_feature_dict

    def getCfFeats(self, cf1, cf2, get_contributors=False):
        cf_dict, cf_contributors = {}, {}
        cf_dict['cfsim'], cf_contributors['cfsim'] = self.get_cfsim_features(cf1, cf2, get_contributors=get_contributors)
        cf_dict['core'] = self.get_core_features(cf1, cf2)
        #cf_dict['cfArg'], cf_contributors['cfArg'] = self.get_context_features(cf1, cf2, get_contributors=get_contributors)
        #cf_dict['cfCase'], cf_contributors['cfCase'] = self.get_context_features(cf1, cf2, get_contributors=get_contributors)

        return cf_dict, cf_contributors

    def get_cfsim_features(self, cf1, cf2, get_contributors=False):
        cfsim_feature_dict, cfsim_contributors = defaultdict(float), {}
        for c1, c2 in itertools.product(cf1.args.keys(), cf2.args.keys()):
            align = "%s-%s" % (c1, c2)
            if get_contributors:
                align_sim, contributors = cosineSimilarity(cf1.args[c1], cf2.args[c2], get_contributors=True)
            else:
                align_sim = cosineSimilarity(cf1.args[c1], cf2.args[c2])

            align_sim = round(align_sim, 3)
            if align_sim:
                cfsim_feature_dict[align] = align_sim 
                cfsim_feature_dict["%s-_" % c1] += align_sim
                cfsim_feature_dict["_-%s" % c2] += align_sim
                cfsim_contributors[align] = contributors

        cfsim_scores = {align : round(cfsim, 3) for align, cfsim in cfsim_feature_dict.iteritems()}

        return cfsim_scores, cfsim_contributors

    def get_core_features(self, cf1, cf2):
        core1, core2 = cf1.get_core_cases(), cf2.get_core_cases()
        return ["%s-%s" % (c1, c2) for c1, c2 in itertools.product(core1, core2)]

    def export(self):
        if len(self.supSents.sids) == 0:
            sys.stderr.write("discarding %s: no support sentences.\n" % self.id)
            return
        ev_dict, feat_dict = {}, {}
        ev_dict['supSents'] = self.supSents.sids
        ev_dict['events'] = []
        for ev in self.events:
            if len(ev.cfs) == 0:
                sys.stderr.write("discarding %s: no candidate cf for %s.\n" % (self.id, ev.predRep))
                return

            ev_dict['events'].append(ev.export())

        feat_dict['features'], ev_dict['feature_contributors'] = self.getAllFeats(get_contributors=True)
        feat_dict['goldRaw'] = self.goldRaw
        feat_dict['goldSets'] = self.goldSets

        # write to tmp-db
        export_db = "%s_%s" % (self.config.output_db, self.id)
        export_db = shelve.open(export_db)
        export_db['ev'] = ev_dict
        export_db['feat'] = feat_dict
        export_db.close()

