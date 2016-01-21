import argparse
import sys
import time

try:
    import RPi.GPIO as GPIO
    have_gpio = True
except ImportError:
    have_gpio = False

from button import MrButton, AudioPhraseOutput, do_recordings, report_missing, record_phrase, ReportingOutput

BUTTON_PIN = 18
AMP_PIN = 23

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
    parser.add_argument("-b", "--benchmark", action="store_true",
                        help="run through the state machine and report stats")

    args = parser.parse_args()


    mr_button = MrButton()

    if args.list_sequences:
        seqs = mr_button.root_narrative.all_sequences()
        sequence_names = []
        for n, s in seqs:
            print n, s[0]
            sequence_names.append(s[0])
        print "--"

        #for i in sorted(sequence_names):
            #print '%s' % i
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
    elif args.benchmark:
        mr_button.print_tree()
        reporter = ReportingOutput()
        mr_button.phrase_handler = reporter
        mr_button.ignore_sleeps = True
        for i in range(0,10000):
            mr_button.push_button()

        reporter.print_summary()
    else:
        report_missing(mr_button)

        mr_button.phrase_handler = AudioPhraseOutput()

        if have_gpio:
            def call_on_me(channel):
                mr_button.push_button()
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down = GPIO.PUD_UP)
            GPIO.setup(AMP_PIN, GPIO.OUT, initial=0)
            GPIO.output(AMP_PIN, GPIO.LOW)
            #GPIO.add_event_detect(BUTTON_PIN,
                #GPIO.FALLING, callback=call_on_me, bouncetime=300)
            #while(1):
                #time.sleep(5)
            try:
                while(1):
                    try:
                        GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
                        GPIO.output(AMP_PIN, GPIO.HIGH)
                        call_on_me(BUTTON_PIN)
                        GPIO.output(AMP_PIN, GPIO.LOW)
                    except RuntimeError, e:
                        print e
            except KeyboardInterrupt:
                pass
            finally:
                GPIO.cleanup()
        else:
            while(1):
                mr_button.push_button()

    sys.exit(0)
