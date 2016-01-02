import argparse
import sys

from button import MrButton, AudioPhraseOutput, do_recordings, report_missing, record_phrase


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")

    parser.add_argument("-r", "--record-missing", action="store_true",
                        help="record missing phrases")
    parser.add_argument("--record-phrase", action="store",
                        help="record (and overwrite) specific phrase")

    parser.add_argument("-l", "--list-sequences", action="store_true",
                        help="show all sequences in data directory")
    parser.add_argument("-p", "--list-phrases", action="store",
                        help="show all phrases for sequence")

    args = parser.parse_args()


    mr_button = MrButton()

    if args.list_sequences:
        seqs = mr_button.root_narrative.all_sequences()
        for n, s in seqs:
            print 'Sequence', s[0]
            for i, phrase in enumerate(s[1]):
                print ' %d - %s' % (i, phrase.get('text'))
    elif args.list_phrases:
        seq = mr_button.get_sequence(args.list_phrases)
        for i, phrase in enumerate(seq):
            print ' %d - %s' % (i, phrase.get('text'))
    elif args.record_phrase:
        seq_name, index = args.record_phrase.split('.')
        n, seq = mr_button.get_sequence(seq_name, with_narrative=True)
        record_phrase(n, seq_name, seq, int(index))
    elif args.record_missing:
        do_recordings(mr_button)
    else:
        report_missing(mr_button)

        mr_button.phrase_handler = AudioPhraseOutput()

        while(1):
            mr_button.push_button()

    sys.exit(0)
