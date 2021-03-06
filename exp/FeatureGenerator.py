# -*- coding: utf-8 -*-
import sys
import shelve
import random
import itertools
from collections import defaultdict
from utils import ALL_ALIGN

class FeatureGenerator(object):
    allFeats = {'Binary': ("get_binary", 'bin'), \
                'PostPred': ("get_postPred", 'post'), \
                'Conflict': ("get_conflict", 'conf'), \
                'Cfsim': ("get_cfsim", 'cfsim'), \
                'Core': ("get_core", 'core'), \
                'ContextArg': ("get_contextArg", 'cArg'), \
                'ContextCase': ("get_contextCase", 'cCase'), \
                'SupportArg': ("get_supportArg", 'cArg'), \
                'SupportCase': ("get_supportCase", 'cCase'), \
                'EmbedSim': ("get_embedSim", 'emb'), \
                'EmbedSmall': ("get_embedSmall", 'embs')
                }

    def __init__(self, config):
        self.feat_db = config.feat_db

        self.normalFeats = config.normalFeats
        self.rivalFeats = config.rivalFeats
        self.combFeats = config.combFeats

        self.neg_sample_size = config.neg_sample_size
        self.without_impossible = config.without_impossible
    
    def get_test_features(self, ev_id, only_gold=False):
        goldRaw, goldSets, feat_dict, impossible_aligns = self._get_eventchain_data(ev_id)

        # begin of file & comment line. 
        feature_strs = []
        feature_strs.append("@boi")
        feature_strs.append("# %s %s" % (ev_id, goldRaw))

        #
        if only_gold:
            allAlign = goldSets
        elif self.without_impossible and impossible_aligns:
            allAlign = [x for x in ALL_ALIGN if not set.intersection(set(x), set(impossible_aligns))]
        else:
            allAlign = ALL_ALIGN

        for cf_pair in feat_dict.keys():
            if cf_pair == 'general':
                continue
            for alignment in allAlign:
                if only_gold:
                    gold_index = allAlign.index(alignment)
                    classStr = "%s_%s_%s" % (ev_id, cf_pair, gold_index) 
                else:
                    classStr = self.get_classStr(ev_id, cf_pair, alignment)

                testFeatStr = self.get_featStr(feat_dict, alignment, cf_pair)
                feature_strs.append("-%s %s" % (classStr, testFeatStr))

        # end of file
        feature_strs.append("@eoi\n")
        return feature_strs

    def get_train_features(self, key):
        ev_id, cf1, cf2, gold_num = key.split('_')
        cf_pair = "%s_%s" % (cf1, cf2)
        goldRaw, goldSets, feat_dict, impossible_aligns = self._get_eventchain_data(ev_id)
        goldAlign = goldSets[int(gold_num)]

        # begin of file & comment line. 
        feature_strs = []
        feature_strs.append("@boi")
        feature_strs.append("# %s %s" % (ev_id, goldRaw))

        # print positive instance.
        classStr = self.get_classStr(ev_id, cf_pair, goldAlign)
        posFeatStr = self.get_featStr(feat_dict, goldAlign, cf_pair)
        feature_strs.append("+%s %s" % (classStr, posFeatStr))

        # print negative instances.
        for alignment in random.sample(ALL_ALIGN, self.neg_sample_size):
            if alignment == goldAlign:
                continue

            classStr = self.get_classStr(ev_id, cf_pair, alignment)
            negFeatStr = self.get_featStr(feat_dict, alignment, cf_pair)
            feature_strs.append("-%s %s" % (classStr, negFeatStr))

        # end of file
        feature_strs.append("@eoi\n")

        return feature_strs

    def _get_eventchain_data(self, ev_id):
        data_dict = shelve.open(self.feat_db, flag='r')[ev_id]
        if data_dict['goldRaw'] == None:
            goldRaw, goldSets = "", None
        else:
            goldRaw = " ".join(data_dict['goldRaw'])
            goldSets = data_dict['goldSets']
        feat_dict = data_dict['features']
        impossible_aligns = data_dict['impossibleAlign']

        return goldRaw, goldSets, feat_dict, impossible_aligns

    def get_classStr(self, ev_id, cf_pair, alignment):
        alignStr = "null" if alignment == [] else "_".join(alignment)
        classStr = "%s_%s_%s" % (ev_id, cf_pair, alignStr)
        return classStr

    def get_featStr(self, feat_dict, align, cf_pair):
        allFeats = []

        for feat in self.normalFeats:
            if feat not in FeatureGenerator.allFeats.keys():
                continue
            fx, postfix = FeatureGenerator.allFeats[feat]
            allFeats.append(getattr(self, fx)(align, cf_pair, postfix, feat_dict))

        for feat in self.rivalFeats:
            rivType = feat.rstrip('Riv')
            allFeats.append(self.get_rival(align, cf_pair, rivType, feat_dict))

        allFeats = filter(None, allFeats)
        return " ".join(allFeats)

    ### general features.
    def get_binary(self, align, cf_pair, postfix, feat_dict):
        binaryFeats = []
        for a in align:
            binaryFeats.append("%s_%s" % (a, postfix))

        return " ".join(binaryFeats) 

    def get_postPred(self, align, cf_pair, postfix, feat_dict):
        c2s = set(map(lambda x: x.split('-')[1], align))
        posts = set(feat_dict['general']['postPred'])
        postFeats = ["%s_%s" % (c2, postfix) for c2 in c2s & posts]

        return " ".join(postFeats)

    def get_conflict(self, align, cf_pair, postfix, feat_dict):
        confFeats = []

        conflictScores = feat_dict['general']['conflict']
        for a in set(align) & set(conflictScores.keys()):
            c1, c2 = a.split('-')
            score = float(conflictScores[a]) / conflictScores["%s2" % (c2)]
            confFeats.append("%s_%s:%.3f" % (a, postfix, score))

        return " ".join(confFeats)

    def get_contextArg(self, align, cf_pair, postfix, feat_dict):
        cArgFeats = []

        cArgDict = feat_dict['general']['cArg']
        for a in set(align) & set(cArgDict.keys()):
            score = cArgDict[a]
            cArgFeats.append("%s_%s:%.3f" % (a, postfix, score))

        return " ".join(cArgFeats)

    def get_contextCase(self, align, cf_pair, postfix, feat_dict):
        cCaseFeats = []

        cCaseDict = feat_dict['general']['cCase']
        for a in set(align) & set(cCaseDict.keys()):
            score = cCaseDict[a]
            cCaseFeats.append("%s_%s:%.3f" % (a, postfix, score))

        return " ".join(cCaseFeats)

    def get_supportArg(self, align, cf_pair, postfix, feat_dict):
        sArgFeats = []

        sArgDict = feat_dict['general']['sArg']
        for a in set(align) & set(sArgDict.keys()):
            score = sArgDict[a]
            sArgFeats.append("%s_%s:%.3f" % (a, postfix, score))

        return " ".join(sArgFeats)


    def get_supportCase(self, align, cf_pair, postfix, feat_dict):
        sCaseFeats = []

        sCaseDict = feat_dict['general']['sCase']
        for a in set(align) & set(sCaseDict.keys()):
            score = sCaseDict[a]
            sCaseFeats.append("%s_%s:%.3f" % (a, postfix, score))

        return " ".join(sCaseFeats)

    def get_embedSim(self, align, cf_pair, postfix, feat_dict):
        embedFeats = []

        embedDict = feat_dict['general']['embed']
        for a in set(align) & set(embedDict.keys()):
            score = embedDict[a]
            embedFeats.append("%s_%s:%.3f" % (a, postfix, score))

        return " ".join(embedFeats)

    def get_embedSmall(self, align, cf_pair, postfix, feat_dict):
        embedFeats = []

        embedDict = feat_dict['general']['embed_s']
        for a in set(align) & set(embedDict.keys()):
            score = embedDict[a]
            embedFeats.append("%s_%s:%.3f" % (a, postfix, score))

        return " ".join(embedFeats)

    ### cf-related features.
    def get_cfsim(self, align, cf_pair, postfix, feat_dict):
        cfsimFeats = []
        
        cfsimScores = feat_dict[cf_pair]['cfsim']
        for a, cfsim in cfsimScores.iteritems():
            if '_' in a or '-' not in a:    # items used for normalization.
                continue

            cfsim = cfsim if a in align else (-1) * cfsim
            cfsimFeats.append("%s_%s:%.3f" % (a, postfix, cfsim))

        return " ".join(cfsimFeats)

    def get_core(self, align, cf_pair, postfix, feat_dict):
        coreFeats = []

        coreAligns = feat_dict[cf_pair]['core']
        for a in set(align) & set(coreAligns):
            coreFeats.append("%s_%s" % (a, postfix))

        return " ".join(coreFeats)

    ###
    def get_rival(self, align, cf_pair, rivType, feat_dict):
        # threshold could be added.
        rivFeats = []
        if rivType == 'Cfsim':
            rivScores, postfix = feat_dict[cf_pair]['cfsim'], 'cfsimRiv'
        else:
            return ""

        for a in set(align) & set(rivScores.keys()):
            c1, c2 = a.split('-')
            score = float(rivScores[a])
            ratio1 = score / rivScores["%s-_" % c1]
            ratio2 = score / rivScores["_-%s" % c2]
            rivFeats.append("%s_%s:%.3f" % (a, postfix, ratio1 * ratio2))
        return " ".join(rivFeats)

