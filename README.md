# do-not-push

An art project for Kiwiburn 2015

## Rough plan.

Types of output can be:

- "text"
- "audio"
- "speech synthesis" (might just be on osx)

Have core application and three modes:

- run as a website (static site can be put on github-pages?), either showing
text or playing audio. large animated button.

- run on the command line, pushing enter and using any of the outputs.

- run on raspberry pi. should show text to log file, play to audio, and take
input from gpio

## Narratives

The idea is that they'll be combination of sequential and random phrase
sequences.

The data will be arranges in a tree, with each directory having an optional
yaml configuration.

By default, the audio files will be played in name ordered sequence.
e.g. 001-hello.mp3, 002-stop-it.mp3, 003-stop-it-again.mp3 etc. Directories will be interpolated, so
that if there were a 002/ with files, it would be processed after 001-hello.mp3

The yaml file can override this behaviour for any directory.


```yaml
sequences:
    - sequence_id: greeting 
        - id: 1 # so id would be sequence.1
          audio: 001-hello.mp3 # relative to current dir
          text: "Hello there"
        - id: 2
          audio: 002-hello.mp3
          text: "I am a button"
transitions:
    button:
        - sequence: greeting 
          weight: 10 # can be any positive number, all options are normalised 0-1
        - dir: subdir
          weight: 10
    timeout:
        - sequence: where_are_you 
          weight: 1 # 
          interval: 60 # seconds
        - dir: ..  # This is the default 60 seconds after last button press
          weight: 1 # 
```

What situations do I want to support?

- A sequence of phrases one after the other responding to button presses.
- Random selection of the next sequence of phrases influenced by how long
  people have been interacting with it.
- Spontaneous sequences for when there are no button presses for a long time
  (5 - 30 minutes), which keep going until the sequence is over. But if button
  is pushed it will start a alternate sequence ("yay you pushed the button").

Variables to influence phrases as result of button press:
- number of presses in a row
- time since last button press
- the same sequence shouldn't be possible for some period of time, if there are
  no options available, the least recent sequence should be picked.

