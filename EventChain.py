# -*- coding: utf-8 -*-
import re
import sys
import shelve
import itertools
from subprocess import check_output
from collections import defaultdict

import utils
from Event import Event
from CaseFrame import CaseFrame
from SupportSentences import SupportSentences

class EventChain(object):
    input_pattern = r"(.+) {(.+)} => {(.+)} .*"
    def __init__(self, config, arg_str, debug=False):
        self.config = config
        self.debug = debug

        self._init_events(arg_str)
        self._init_gold()
        # may move to somewhere else
        self.set_supSents()
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
        pred_key = "-".join(ev_str.split(':')[0] for ev_str in ev_strs)

        for ev_str in ev_strs:
            raw_pred, raw_arg = ev_str.split(':')[0], ev_str.split(':')[1:]
            ev = Event(raw_pred, raw_arg, pred_key, self.config, self.debug)
            self.events.append(ev)

    def _init_gold(self):
        if self.config.gold_file == 'None':
            self.goldRaw, self.goldExpansion, self.goldSets = None, None, []
            return

        command = 'grep \"^%s\" %s' % (self.id, self.config.gold_file)
        line = check_output(command, shell=True)
        self.goldRaw = line.rstrip().split('|')[-1].split()

        self.goldExpansion = utils.getExpandedAlign(self.goldRaw)
        self.goldSets = utils.getAllPossibleAlign(self.goldRaw) 
        
        if self.debug:
            print "gold:", self.goldRaw, "gold sets:", self.goldSets

    def set_supSents(self): 
        support_sentences_keys = self._get_support_sentences_keys()
        self.supSents = SupportSentences(self.config, support_sentences_keys) 
        self._set_event_supArgs()

        if self.debug:
            print "Support sentence extraction keys:\n\t%s" % ("\n\t".join(support_sentences_keys))
            print "Number of support sentences extracted: %d" % len(self.supSents.sents)

        self._set_contextWords()
        
    def _get_support_sentences_keys(self):
        event_keys = [ev.get_eventKeys() for ev in self.events]
        support_sentence_keys = ["-".join(key_list) for key_list in itertools.product(*event_keys)]
        return support_sentence_keys

    def _set_event_supArgs(self):
        supArgs = self.supSents.get_supArgs()
        for ev, supArg in itertools.izip(self.events, supArgs):
            ev.set_supArgs(supArg)
    
    def _set_contextWords(self):
        self.context_words = self.supSents.get_context_words()

        if self.debug:
            print "context words:", ' '.join(self.context_words)
        
    def set_event_cfs(self):
        for ev in self.events:
            ev.set_cfs()

        if self.debug:
            if len(ev.cfs) == 0:
                print "No CaseFrame found for event-id: %s (%s)" % (self.id, ev.predRep)

    def getAllFeats(self, max_cf_num=10, combined_cf=False, get_contributors=False):
        all_features_dict, feature_contributors = {}, {}
        all_features_dict['general'], feature_contributors['general'] = self.getGeneralFeats(get_contributors=get_contributors)

        cfs1, cfs2 = [ev.cfs for ev in self.events]

        for i in xrange( min(max_cf_num, len(cfs1)) ):
            for j in xrange( min(max_cf_num, len(cfs2)) ):
                cf_nums = "%s_%s" % (i, j)

                cf1 = CaseFrame(self.config, cf_id=cfs1[i].cf_id)
                cf2 = CaseFrame(self.config, cf_id=cfs2[j].cf_id)
                all_features_dict[cf_nums], feature_contributors[cf_nums] = self.getCfFeats(cf1, cf2, get_contributors=get_contributors)

        # combined cf:
        return all_features_dict, feature_contributors

    def getGeneralFeats(self, get_contributors=False):
        general_dict, general_contributors = {}, {}

        general_dict['postPred'] = self.getPostPredCases()
        general_dict['conflict'] = self.supSents.getConflictScores()
        general_dict['sup'] = self.getSupFeats()
        general_dict['cArg'] = self.getContextArgScores()
        general_dict['cCase'] = self.getContextCaseScores()

        return general_dict, general_contributors

    def getPostPredCases(self):
        return self.events[1].givenArgs.keys()

    def getSupFeats(self):
        sup_feature_dict = {}
        sup1, sup2 = [ev.supArgs for ev in self.events]
        for c1, c2 in itertools.product(sup1.keys(), sup2.keys()):
            align = "%s-%s" % (c1, c2)
            sim = round(utils.cosineSimilarity(sup1[c1], sup2[c2]), 3)
            if sim:
                sup_feature_dict[align] = sim
        return sup_feature_dict

    def getContextArgScores(self, threshold=0):
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
                #print context_word, score_dicts[0], score_dicts[1]

        return contextArgScores

    def getContextCaseScores(self, threshold=0):
        contextCaseScores = {}
        for context_word, count in self.context_words.iteritems():
            if count <= threshold:
                continue

            score_dicts = []
            for ev in self.events:
                score_dict = ev.get_contextCaseScore(context_word)
                if not score_dict:
                    break
                score_dicts.append(score_dict)
            else:
                contextCaseScores[context_word] = score_dicts
                #print context_word, score_dicts[0], score_dicts[1]

        return contextCaseScores
            
    def getCfFeats(self, cf1, cf2, get_contributors=False):
        cf_dict, cf_contributors = {}, {}

        cf_dict['cfsim'], cf_contributors['cfsim'] = self.getCfsimFeats(cf1, cf2, get_contributors=get_contributors)
        cf_dict['core'] = self.getCoreFeats(cf1, cf2)
        ### cfArg
        ### cfCase

        return cf_dict, cf_contributors

    def getCfsimFeats(self, cf1, cf2, get_contributors=False):
        cfsim_feature_dict, cfsim_contributors = defaultdict(float), {}
        for c1, c2 in itertools.product(cf1.args.keys(), cf2.args.keys()):
            align = "%s-%s" % (c1, c2)
            if get_contributors:
                align_sim, contributors = utils.cosineSimilarity(cf1.args[c1], cf2.args[c2], get_contributors=True)
            else:
                align_sim = utils.cosineSimilarity(cf1.args[c1], cf2.args[c2])

            align_sim = round(align_sim, 3)
            if align_sim:
                cfsim_feature_dict[align] = align_sim 
                cfsim_feature_dict["%s-_" % c1] += align_sim
                cfsim_feature_dict["_-%s" % c2] += align_sim
                cfsim_contributors[align] = contributors

        cfsim_scores = {align : round(cfsim, 3) for align, cfsim in cfsim_feature_dict.iteritems()}

        return cfsim_scores, cfsim_contributors

    def getCoreFeats(self, cf1, cf2):
        core1, core2 = cf1.get_core_cases(), cf2.get_core_cases()
        return ["%s-%s" % (c1, c2) for c1, c2 in itertools.product(core1, core2)]

    def export(self):
        if len(self.supSents.sents) == 0:
            sys.stderr.write("discarding %s: no support sentences.\n" % self.id)
            return

        if any(len(ev.cfs) == 0 for ev in self.events):
            sys.stderr.write("discarding %s: no candidate cf for %s.\n" % (self.id, ev.predRep))
            return

        ev_dict, feat_dict = {}, {}
        ev_dict['supSents'] = self.supSents.export()
        ev_dict['context_words'] = self.context_words
        ev_dict['events'] = [ev.export() for ev in self.events]

        feat_dict['goldRaw'] = self.goldRaw
        feat_dict['goldSets'] = self.goldSets
        feat_dict['features'], ev_dict['feature_contributors'] = self.getAllFeats(get_contributors=True)

        if self.debug:
            return

        # write to tmp-db
        export_db = "%s_%s" % (self.config.output_db, self.id)
        export_db = shelve.open(export_db)
        export_db['ev'] = ev_dict
        export_db['feat'] = feat_dict
        export_db.close()

