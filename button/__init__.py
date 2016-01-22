import yaml

import os
import time

import os.path
import random
from collections import defaultdict

from slugify import slugify

from button.audio import record, play_back, save_to_file, play_file

config_file = 'button.yml'


def is_subdir(path, directory):
    """ This is unlikely to be secure/robust """
    path = os.path.realpath(path)
    directory = os.path.realpath(directory)
    relative = os.path.relpath(path, directory)
    return relative.startswith(os.pardir)


def sequence_text_to_filename(seq_name, index, text):
    """
    >>> sequence_text_to_filename("blahabla", 21, "what's up fboraa?")
    blahabla-021-whats-up-fboraa.wav
    """
    fn = "%s-%03d-%s.wav" % (seq_name, index, slugify(text)[:20])
    return fn


def record_phrase(n, seq_name, seq, line):
    print "Please say \"%s\"..." % seq[line].get('text')
    need_audio = True
    while need_audio:
        raw_input("press any key when ready")
        sample_width, data = record()
        print("playing back sample...")
        play_back(data, sample_width)
        x = raw_input("Is this ok? [yn]")
        if x == 'y':
            need_audio = False
            # TODO generate filename with correct path
            fn = sequence_text_to_filename(seq_name, line, seq[line].get('text'))
            tmp_file = os.path.join(n.basedir, fn)
            save_to_file(tmp_file, sample_width, data)
            n.save_audio(seq_name, line, fn)

def report_missing(button):
    total = 0
    total_seq = 0
    for n, seq_name, missing in button.find_missing_audio():
        total_seq += 1
        total += len(missing)
        seq = n.get_sequence(seq_name)
        _report_missing(seq_name, seq, missing)

    print "Total sequences with missing phrases: %d" % total_seq
    print "Total phrases missing: %d" % total

def _report_missing(seq_name, seq, missing):
    print " * missing audio for these lines in sequence '%s'" % seq_name

    for line in missing:
        print "    - \"%s\"" % seq[line].get('text')


def do_recordings(button):
    for n, seq_name, missing in button.find_missing_audio():
        seq = n.get_sequence(seq_name)
        _report_missing(seq_name, seq, missing)

        for line in missing:
            record_phrase(n, seq_name, seq, line)


class PhraseOutput(object):
    def __init__(self):
        self.last_seq = None

    def __call__(self, phrase, seq=None):
        if self.last_seq != seq:
            print "New sequence selected %s" % seq
            self.last_seq = seq


class ConsolePhraseOutput(PhraseOutput):
    def __call__(self, phrase, seq=None):
        super(ConsolePhraseOutput, self).__call__(phrase)
        print "Mr Button says:", phrase.get("text", "")


class AudioPhraseOutput(ConsolePhraseOutput):
    def __call__(self, phrase, seq=None):
        super(AudioPhraseOutput, self).__call__(phrase)
        if phrase.get('audio'):
            play_file(phrase.get('audio'))
        else:
            print "No audio for %s" % phrase.get('text')

class ReportingOutput(PhraseOutput):

    def __init__(self):
        self.sequences = defaultdict(int)
        self.last_seq = None

    def __call__(self, phrase, seq=None):
        #t = phrase.get('text')
        #print phrase
        if seq and self.last_seq != seq:
            self.last_seq = seq
            self.sequences[seq] += 1

    def print_summary(self):
        for seq_name, count in sorted(self.sequences.items()):
            print seq_name, count


class MrButton(object):

    def __init__(self, data_dir='./data'):
        self.root_narrative = Narrative(os.path.join(data_dir, config_file))
        self.current_state = (self.root_narrative, None)
        self.recent_sequences = []
        self.phrase_handler = ConsolePhraseOutput()
        self.ignore_sleeps = False

    def push_button(self):
        n, seq = self.current_state
        self.trim_cache()
        phrase, self.current_state = n.next_phrase(
                seq, visited=[],
                cache=self.recent_sequences,
                trigger='button')
        self.phrase_handler(phrase, seq=self.current_state[1][0])
        if not self.ignore_sleeps: 
            time.sleep(phrase.get('pause', 0))

    def trim_cache(self):
        MAX_CACHE = 10
        if len(self.recent_sequences) > MAX_CACHE:
            self.recent_sequences = self.recent_sequences[-10:]

    def find_missing_audio(self):
        for n, (seq_name, seq) in self.root_narrative.all_sequences():
            missing = []
            for i, row in enumerate(seq):
                audio_file = row.get('audio')

                if audio_file is None:
                    missing.append(i)
                else:
                    fn = os.path.join(n.basedir, audio_file)
                    if not os.path.isfile(fn):
                        print "audio file for %s.%d is %s but missing" % (seq_name, i, fn)
                        missing.append(i)
            if missing:
                yield n, seq_name, missing

    def get_sequence(self, seq_name, with_narrative=False):
        return self.root_narrative.get_sequence(seq_name, with_narrative)

    def print_tree(self):
        print "BUTTON"
        self.root_narrative.print_tree(indent=2)


class Narrative(object):

    def __init__(self, yaml_file_or_dir, parent=None):
        self.parent = parent
        if os.path.isdir(yaml_file_or_dir):
            self.basedir = yaml_file_or_dir
            print yaml_file_or_dir, "is a dir?"
            self.yaml_file = os.path.join(yaml_file_or_dir, 'button.yml')
            self.sequences = {}
            self.transitions = { 'button': [], 'timeout': [] }
            if self.parent:
                self.transitions['button'].append({
                    'dir': '..',
                    'weight': 1,
                    'narrative': self.parent,
                    })
            # TODO: list all mp3 files, create a separate sequence for each
            for subf in os.listdir(yaml_file_or_dir):
                name, ext = subf.rsplit('.', 1)
                if ext == 'mp3':
                    self.sequences[name] = [{
                            'text': name,
                            'audio': subf,
                            }]
            self._add_sequences_to_transitions()
        else:
            self.basedir = os.path.dirname(yaml_file_or_dir)
            self.yaml_file = yaml_file_or_dir
            with open(self.yaml_file, 'r') as f:
                narrative = yaml.load(f)
                self.sequences = narrative.get('sequences', {})
                self.transitions = narrative.get(
                        'transitions',
                        { 'button': [], 'timeout': [] }
                        )

            self._load_children('button')
            self._load_children('timeout')
            self._add_sequences_to_transitions()

    def get_sequence(self, name, with_narrative=False):
        if name in self.sequences:
            if with_narrative:
                return self, self.sequences[name]
            else:
                return self.sequences[name]

        for _, transitions in self.transitions.iteritems():
            for t in transitions:
                if 'narrative' in t:
                    if t['narrative'] == self.parent:
                        continue
                    s = t['narrative'].get_sequence(name, with_narrative)
                    if s:
                        return s
    
    def all_sequences(self):
        for seq in self.sequences.iteritems():
            yield self, seq
        for _, transitions in self.transitions.iteritems():
            for t in transitions:
                if 'narrative' in t:
                    if t['narrative'] == self.parent:
                        continue
                    for n, seq in t['narrative'].all_sequences():
                        yield n, seq

    def print_tree(self, indent=2):
        #for seq in self.sequences.iteritems():
            #print " "*indent, seq[0]
        for t_type, transitions in self.transitions.iteritems():
            print " "*indent, t_type
            i2 = indent + 2
            for t in transitions:
                if 'narrative' in t:
                    if t['narrative'] == self.parent:
                        print " "*(i2), "PARENT"
                    else:
                        print " "*(i2), t['dir']
                        t['narrative'].print_tree(indent=indent+4)
                else:
                    print " "*i2, t['sequence']

    def _add_sequences_to_transitions(self):
        # gather sequences that are not explicitly mentioned in
        # transitions, give them weight 1
        for seq in self.sequences:
            if seq not in self.transitions['button'] and seq not in self.transitions['timeout']:
                seq_transition = {
                    'sequence': seq,
                    'weight': 1,
                }
                self.transitions['button'].append(seq_transition)


    def _load_children(self, transition_type):
        parent_found = False
        self.transitions.setdefault(transition_type, [])

        dirs_used = []

        for seq in self.transitions[transition_type]:
            if 'dir' in seq:
                p = os.path.join(self.basedir, seq['dir'])
                if is_subdir(self.basedir, p):
                    dirs_used.append(p)
                    seq['narrative'] = Narrative(os.path.join(p, config_file), self)
                elif seq['dir'] == '..':
                    # parent
                    parent_found = True
                    seq['narrative'] = self.parent
                else:
                    print p, "is not a subdir"

        # add transition back to parent if not explicitly defined
        if not parent_found and self.parent:
            self.transitions[transition_type].append({
                'dir': '..',
                'weight': 1,
                'narrative': self.parent,
                })

        if transition_type == 'button':

            # scan all subdirs for button.yml
            for f in os.listdir(self.basedir):
                if not os.path.isdir(os.path.join(self.basedir, f)):
                    continue
                if os.path.join(self.basedir, f) in dirs_used:
                    continue
                fn = os.path.join(self.basedir, f, 'button.yml')
                if os.path.isfile(fn):
                    seq = {
                        'dir': f,
                        'narrative': Narrative(fn, self),
                        'weight': 1,
                    }
                    print "Implicitly loading subdir %s with button.yml as %s" % (f, seq['narrative'])
                    self.transitions['button'].append(seq)
                else:
                    has_audio = False
                    # scan for mp3s to play
                    dirname = os.path.join(self.basedir, f)
                    for subf in os.listdir(dirname):
                        if subf.split('.')[-1] == 'mp3':
                            has_audio = True
                    if has_audio:
                        seq = {
                            'dir': f,
                            'narrative': Narrative(dirname, self),
                            'weight': 1,
                        }
                        print "Implicitly loading subdir %s with mp3s as %s" % (f, seq['narrative'])
                        self.transitions['button'].append(seq)
                        


    def next_phrase(self, sequence_phrase, visited, cache, trigger='button'):
        seq_name = None
        index = None
        visited.append(self)
        if sequence_phrase:
            seq_name, index = sequence_phrase
            index = int(index) + 1
            try:
                phrase = self.get_phrase(seq_name, index)
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
                return t['narrative'].next_phrase(None, visited, cache, trigger)
            elif 'sequence' in t:
                seq_name = t['sequence']
            index = 0
            phrase = self.get_phrase(seq_name, index)

        if len(cache) == 0 or cache[-1] != seq_name:
            cache.append(seq_name)
        return (phrase, (self, (seq_name, index)))

    def get_phrase(self, sequence_name, index):
        seq = self.sequences.get(sequence_name, [])
        phrase = dict(seq[index])
        if phrase.get('audio'):
            phrase['audio'] = os.path.join(self.basedir, phrase['audio'])
        return phrase

    def select_transition(self, visited, cache, trigger='button'):
        choices = {}
        parent = None
        # gather choices
        for c in self.transitions.get(trigger,[]):
            if 'sequence' in c:
                choices[c['sequence']] = c
            elif 'dir' in c:
                k = c['narrative']
                if k not in visited:
                    choices['__dir__' + c['dir']] = c
                if c['dir'] == '..':
                    parent = c


        for seq_name in reversed(cache):
            if seq_name in choices and len(choices) > 1:
                del choices[seq_name]
        
        if len(choices.keys()) == 0:
            # If no valid choices force explicit transition
            # to parent
            return parent.select_transition(visited, cache, trigger)
            #choices['__dir__' + parent['dir']] = parent
            
            
        keys = choices.keys()
        #print "choices are ", keys
        transition_index = random.randint(0, len(keys) - 1)
        return choices[keys[transition_index]]

    def save_audio(self, seq_name, line, fn):
        n = {}

        tmp_file = os.path.join(self.basedir, fn)
        result = os.system("lame --preset voice %s" % (tmp_file,))
        if result:
            print result
            raise Exception("Error encoding audio wave to mp3")

        (root, ext) = os.path.splitext(fn)
        fn = root + '.mp3'

        with open(self.yaml_file, 'r') as f:
            n = yaml.load(f)
            sequences = n['sequences']
            sequences[seq_name][line]['audio'] = fn 
            print "updating: ", sequences[seq_name][line]

        n['sequences'] = sequences
        with open(self.yaml_file, 'w') as f:
            print "saving yaml"
            yaml.dump(n, f)

