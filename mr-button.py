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

    def push_button(self):
        n, seq = self.current_state
        self.current_state = n.next_state(seq, trigger='button')


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
        for seq in self.transitions.get(transition_type, []):
            if 'dir' in seq:
                p = os.path.join(self.basedir, seq['dir'])
                if is_subdir(self.basedir, p):
                    seq['narrative'] = Narrative(os.path.join(p, config_file), self)
                elif seq['dir'] == '..':
                    # parent
                    seq['narrative'] = self
                else:
                    print p, "is not a subdir"

    def next_state(self, sequence_phrase, trigger='button'):
        seq_name = None
        index = None
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
            # work what to do next. This might involve a new
            t = self.select_transition()
            if t is None:
                return (self, (None, None))
            elif 'narrative' in t:
                return t['narrative'].next_state(None, trigger)
            elif 'sequence' in t:
                seq_name = t['sequence']
            index = 0
            self.run_phrase(seq_name, index)

        return (self, (seq_name, index))

    def run_phrase(self, sequence_name, index):
        seq = self.sequences.get(sequence_name, [])
        phrase = seq[index]
        print "Mr Button says: ", phrase.get("text", "")

    def select_transition(self, trigger='button'):
        choices = self.transitions.get(trigger,[])
        transition_index = random.randint(0, len(choices) - 1)
        print choices
        print transition_index
        return choices[transition_index]


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
