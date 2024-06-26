from genericpath import isdir
from operator import sub
import sys
import argparse
import json
import os.path
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
import pysrt
from datetime import timedelta
import subprocess
import tempfile
from pydub import AudioSegment, effects

args = sys.argv

def getArguments():
    parser = argparse.ArgumentParser(description="Read a videoconfig json file and output a concatenated video file",formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('videoconfig', help="The videoconfig json file to use")
    parser.add_argument('-d', '--dryrun', help="Dry run, do not actually write anything", action="store_true")
    parser.add_argument('--subtitles', help="Process subtitle files", default=True)
    parser.add_argument('--no-subtitles', help="Don't process subtitle files", dest='subtitles', action='store_false')
    parser.add_argument('--subtitles_only', help='Generate subtitles but not video', action='store_true')
    parser.add_argument('--normalize', help='Normalize audio', default=True)
    parser.add_argument('--no-normalize', help='Don\'t normalize audio', dest='normalize', action='store_false')
    parser.add_argument('--audiofile', help='Write an audio file for debug purposes', action='store_true')
    return parser.parse_args()

arguments = getArguments()

def is_file(path):
    return os.path.isfile(path)

def load_videoconfig():
    if is_file(arguments.videoconfig):
        f = open(arguments.videoconfig)
        return json.load(f)
    else:
        print('Invaid videoconfig file')

def load_video(path):
    video_clip = VideoFileClip(path)
    if arguments.normalize:
        clip = ffmpeg_normalize(video_clip)
    else:
        clip = video_clip
    # print("Clip loaded:",path)
    return clip



def ffmpeg_normalize(video):
    if video.audio: #Don't try to normalize a clip without audio!
        if not cache_dir: #Cache dir is not present, use temporary files
            temp_input = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_input_path = temp_input.name
            temp_output = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_output_path = temp_output.name
        
            audio = video.audio
            audio.write_audiofile(temp_input_path)

            temp_audio = AudioSegment.from_file(temp_input_path)
            normalized_audio = effects.normalize(temp_audio)
            normalized_audio.export(temp_output_path, format='mp3')

            normalized_audio_import = AudioFileClip(temp_output_path)
            video = video.set_audio(normalized_audio_import)
            
            temp_input.close()
            temp_output.close()
        
        else:
            video_file_name = os.path.splitext(os.path.split(video.filename)[1])[0]
            norm_audio_file = os.path.join(cache_dir,video_file_name+"_normalized.mp3")

            if not os.path.isfile(norm_audio_file) or is_newer(norm_audio_file,video.filename):
                print("Updating cache for normalized audio:",video_file_name)
                raw_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                raw_audio_file = raw_audio.name
                audio = video.audio
                audio.write_audiofile(raw_audio_file)

                temp_audio = AudioSegment.from_file(raw_audio_file)
                normalized_audio = effects.normalize(temp_audio)
                normalized_audio.export(norm_audio_file, format='mp3')

                raw_audio.close()
            else:
                print('Using cached audio for',video.filename)
            
            normalized_audio_import = AudioFileClip(norm_audio_file)
            video = video.set_audio(normalized_audio_import)
                    
    return video

def validate_clipslist(clipslist):
    for c in clipslist:
        path = os.path.join(config_dir,c)
        if not is_file(path):
            raise Exception('Invalid path: %r'%(path))
    return True

def validate_subtitle_languages(subtitle_languages):
    available_subtitle_languages = []
    if subtitle_languages:
        for l in subtitle_languages:
            subtitle_path = os.path.join(config_dir,"subtitles_"+l)
            if os.path.isdir(subtitle_path):
                available_subtitle_languages.append(l)
    return available_subtitle_languages

def sum_time_to(clipname):
    sum = 0
    for key,value in clip_lengths.items():
        if not key == clipname:
            sum += value
        else:
            break
    return sum

def is_newer(file_a,file_b): #Returns False if A is newer, True if B is newer
    file_a_mod_time = os.path.getmtime(file_a)
    file_b_mod_time = os.path.getmtime(file_b)
    return file_b_mod_time > file_a_mod_time



#print(arguments)

videoconfig = load_videoconfig()
config_path = os.path.abspath(arguments.videoconfig)
config_dir = os.path.split(config_path)[0]
cache_dir = os.path.join(config_dir,"cache") if os.path.isdir(os.path.join(config_dir,"cache")) else False
title = videoconfig['Title']

output_file = os.path.join(config_dir,title+".mp4")
clipslist = videoconfig['Clips']
chapters = videoconfig.get('Chapters')
clips = []
clip_lengths = {}
print(config_path,config_dir)

if validate_clipslist(clipslist):
    for c in clipslist:
        clip = load_video(os.path.join(config_dir,c))
        if clip:
            clips.append(clip)
            clip_lengths[c] = clip.duration
        else:
            print('Invalid file:',c)

if chapters:
    chapter_file_name = title+"_chapters.txt"
    chapter_file_path = os.path.join(config_dir,chapter_file_name)
    with open(chapter_file_path, 'w') as f:
        line = 1
        for key, value in chapters.items():
            time = sum_time_to(value)
            timestamp = str(timedelta(seconds=round(time)))
            f.write(str(line)+". "+key+" - "+timestamp+"\n")
            line+=1

if arguments.subtitles:
    subtitle_languages = validate_subtitle_languages(videoconfig.get('Subtitles'))
    if subtitle_languages:
        for l in subtitle_languages:
            subs = pysrt.SubRipFile() #Create a container for the concatenated subtitles
            subs_output = os.path.join(config_dir,title+"_"+l+".srt")
            print('Generating subtitle file:',subs_output)
            # Collect available subtitle files
            subtitle_dir = os.path.join(config_dir,"subtitles_"+l)
            for c in clipslist:
                clipname = os.path.splitext(c)[0]
                subtitlename = clipname + ".srt"
                subtitlepath = os.path.join(config_dir,subtitle_dir,subtitlename)
                if os.path.isfile(subtitlepath): #Find out if there is a subtitle file for this clip
                    clip_subs = pysrt.open(subtitlepath) #Open it
                    displacement = sum_time_to(c) #Find out when this clip starts in the concatenated video
                    clip_subs.shift(seconds=displacement) #Shift the subtitle timecodes to the start of the clip
                    subs = subs + clip_subs 
            if subs and not arguments.dryrun:
                for index, subtitle in enumerate(subs): #pysrt doesn't automatically update the subtitle indices so we have to do it manually
                    subtitle.index = index + 1
                subs.save(subs_output, encoding='utf-8')

if len(clips) > 0:
    cat_video = concatenate_videoclips(clips)

    if arguments.audiofile:
            audiofile_path = os.path.join(config_dir,title+'.mp3')
            audio = cat_video.audio
            audio.write_audiofile(audiofile_path,fps=44100)

    if not arguments.dryrun and not arguments.subtitles_only:
        cat_video.write_videofile(output_file, codec="libx264")

if arguments.dryrun:
    print("Dry run complete.")
else:
    print("Process complete.")