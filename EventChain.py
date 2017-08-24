# -*- coding: utf-8 -*-
import sys
import re
import itertools
from Event import Event
from SupportSentences import SupportSentences

class EventChain(object):
    input_pattern = r"(.+) {(.+)} => {(.+)} .*"
    def __init__(self, config, arg_str):
        self.config = config
        self._init_events(arg_str)

    def _init_events(self, arg_str):
        regex = re.compile(EventChain.input_pattern)
        ID, ev1, ev2 = regex.search(arg_str).groups()

        self.ID = ID
        self.events = []
        self.add_events([ev1, ev2])

    def add_events(self, ev_strs):
        raw_preds, raw_args = [], []
        for ev_str in ev_strs:
            ev_elements = re.sub(r"[{{}}]", "", ev_str).split(':')

            raw_preds.append(ev_elements.pop(0))
            raw_args.append(ev_elements)

        pred_key = "-".join(raw_preds)
        for raw_pred, raw_arg in zip(raw_preds, raw_args): 
            ev = Event(raw_pred, raw_arg, pred_key, self.config)
            self.events.append(ev)

    def set_support_sentences(self): 
        support_sentences_keys = self._get_support_sentences_keys()
        self.supSents = SupportSentences(self.config, support_sentences_keys) 
        self._set_event_supArgs()
        
    def _get_support_sentences_keys(self):
        event_keys = [ev.get_eventKeys() for ev in self.events]
        support_sentence_keys = ["-".join(key_list) for key_list in itertools.product(*event_keys)]
        return support_sentence_keys

    def _set_event_supArgs(self):
        supArgs = self.supSents.get_supArgs()
        for ev, supArg in itertools.izip(self.events, supArgs):
            ev.set_supArgs(supArg)
    
    def set_event_cfs(self):
        for ev in self.events:
            ev.set_cfs()

    def export(self):
        pass

