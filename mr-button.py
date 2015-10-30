import yaml

import os
import random
import os.path

config_file = 'button.yml'


def is_subdir(path, directory):
    """ This is unlikely to be secure/robust """
    path = os.path.realpath(path)
    directory = os.path.realpath(directory)
    relative = os.path.relpath(path, directory)
    return relative.startswith(os.pardir)


class MrButton(object):

    def __init__(self, data_dir='./data'):
        self.root_narrative = Narrative(os.path.join(data_dir, config_file))
        self.current_state = (self.root_narrative, None)
        self.recent_sequences = []

    def push_button(self):
        n, seq = self.current_state
        self.current_state = n.next_state(seq, visited=[], cache=self.recent_sequences, trigger='button')

    def trim_cache(self):
        MAX_CACHE = 10
        if len(self.recent_sequences) > MAX_CACHE:
            self.recent_sequences = self.recent_sequences[-10:]


class Narrative(object):

    def __init__(self, yaml_file, parent=None):
        self.basedir = os.path.dirname(yaml_file)
        self.parent = parent
        with open(yaml_file, 'r') as f:
            narrative = yaml.load(f)
            self.sequences = narrative.get('sequences', {})
            self.transitions = narrative.get(
                    'transitions',
                    { 'button': [], 'timeout': [] }
                    )

        self._load_children('button')
        self._load_children('timeout')


    def _load_children(self, transition_type):
        parent_found = False
        self.transitions.setdefault(transition_type, [])
        for seq in self.transitions[transition_type]:
            if 'dir' in seq:
                p = os.path.join(self.basedir, seq['dir'])
                if is_subdir(self.basedir, p):
                    seq['narrative'] = Narrative(os.path.join(p, config_file), self)
                elif seq['dir'] == '..':
                    # parent
                    parent_found = True
                    seq['narrative'] = self.parent
                else:
                    print p, "is not a subdir"
        if not parent_found and self.parent:
            # add transition back to parent if not explicitly defined
            self.transitions[transition_type].append({
                'dir': '..',
                'weight': 1,
                'narrative': self.parent,
                })


    def next_state(self, sequence_phrase, visited, cache, trigger='button'):
        seq_name = None
        index = None
        visited.append(self)
        if sequence_phrase:
            seq_name, index = sequence_phrase
            index = int(index) + 1
            try:
                self.run_phrase(seq_name, index)
            except IndexError:
                seq_name = None
                index = None

        if seq_name is None:
            # If no sequence, then we have finished and need to
            # work out what to do next. This might involve a new narrative
            t = self.select_transition(visited, cache)
            if t is None:
                return (self, (None, None))
            elif 'narrative' in t:
                return t['narrative'].next_state(None, visited, cache, trigger)
            elif 'sequence' in t:
                seq_name = t['sequence']
            index = 0
            self.run_phrase(seq_name, index)

        if len(cache) == 0 or cache[-1] != seq_name:
            cache.append(seq_name)
        return (self, (seq_name, index))

    def run_phrase(self, sequence_name, index):
        seq = self.sequences.get(sequence_name, [])
        phrase = seq[index]
        print "Mr Button says: ", phrase.get("text", "")

    def select_transition(self, visited, cache, trigger='button'):
        choices = {}
        for c in self.transitions.get(trigger,[]):
            if 'sequence' in c:
                choices[c['sequence']] = c
            elif 'dir' in c:
                k = c['narrative']
                if k not in visited:
                    choices['__dir__' + c['dir']] = c

        for seq_name in reversed(cache):
            if seq_name in choices and len(choices) > 1:
                del choices[seq_name]
        
        keys = choices.keys()
        transition_index = random.randint(0, len(keys) - 1)
        return choices[keys[transition_index]]


mr_button = MrButton()
mr_button.push_button()
mr_button.push_button()
mr_button.push_button()
mr_button.push_button()
mr_button.push_button()
mr_button.push_button()
mr_button.push_button()
mr_button.push_button()
mr_button.push_button()
