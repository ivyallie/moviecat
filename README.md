# moviecat
MovieCat is a Python utility that concatenates movie clips into single movie files.
This is useful for making things like video tutorials, because you can keep the various
clips that make up your video in separate files, then replace or rearrange them in the 
future, if the content of your tutorial needs to be modified. It's video editing
without the video editor!

## Features

### JSON definition
The contents of the output file are defined in a JSON file to allow you to easily
modify the parameters of the project.

### Subtitle integration
Supports the concatenation of subtitle files that correspond to the individual movie clips.

### Chapter index
Outputs a text file with time stamps indicating the start of user-defined "chapters".

### Audio normalization
Supports normalization of audio for the entire video. (This relies on ffmpeg.exe currently... to be improved later.)

## Format support
MovieCat uses moviepy to read and write video clips, so it supports any formats that moviepy
supports.

## Usage

### Creating a video definition
All MovieCat projects are defined by JSON files. Here is an
example:
```json
{
    "Title": "CoolVideo",
    "Clips": [
       "Intro.mkv",
       "Chapter1_start.mp4",
       "Chapter1_end.mp4",
       "Chapter2.mp4",
       "End.mp4"
    ],
    "Chapters": {
        "Introduction": "Intro.mkv",
        "Chapter 1: The Beginning": "Chapter1_start.mp4",
        "Chapter 2: The continuation": "Chapter2.mp4",
        "The End": "End.mp4"
    },
    "Subtitles": ["english","spanish"]

}
```

Title
    defines the name of the output video file.

Clips
    is a list of the clips, in sequence, which will be 
    concatenated to build your video. By default, these
    clips are expected to be in the same directory as the 
    definition file.

Chapters
    defines the chapter titles and the clips that they
    correspond to. In this case, Chapter 1 is composed
    of two video clips, so the Chapters definitions refer
    only to the clip which _begins_ Chapter 1. The 
    appropriate chapter timestamps will be output to a 
    TXT file after the video is compiled. (In this case,
    it will be named CoolVideo_chapters.txt.)

Subtitles
    is a list of one or more subdirectories in which there are 
    subtitle SRT files for the clips that make up the video. 
    The names of these files should correspond to the clips 
    which they accompany. MovieCat will concatenate the subtitle
    files and adjust the timestamps to match the concatenated video,
    outputting one new SRT file for each of the named subdirectories.

### Running the utility
To build a video from a definition file, simply run with that
definition file as an argument:
```
python MovieCat.py VideoDefinition.json
```
To see additional command-line options:
```
python MovieCat.py --help
```

