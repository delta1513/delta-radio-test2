#!/bin/bash


# Takes an input audio file (arg1) and converts it to the output file (arg 2) ensuring it complies with delta radio standards


#DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $1)
#FRAMES=$(echo "($DURATION * 48000 - 1000) / 1" | bc)

#SECONDS=$(echo $(ffprobe -i $1 -show_entries format=duration -v quiet -of csv="p=0") - 1 | bc)
SECONDS_F=$(soxi -D $1)
SECONDS=$(echo "($SECONDS_F - 1) / 1" | bc)

BASE=$(basename -s .wav "$1")


#ffmpeg -i $1 -af "atrim=0:$FRAMES" -ac 2 -c:a pcm_s16le -f s16le -ar 48000 "$BASE.fix.wav"
#ffmpeg -i $1 -af "aresample=resampler=soxr:ochl=stereo:osr=48000;atrim=0:$FRAMES" -ac 2 -c:a pcm_s16le -f s16le -ar 48000 "$BASE.fix.wav"
#ffmpeg -i $1 -to $SECONDS $2

ffmpeg -i $1 -af aformat=s16:48000 -compression_level 8 -to $SECONDS $2

#echo $FRAMES
#echo $SECONDS

# for i in delta_radio/*.wav; do /home/mark/prog/delta-radio/wavfix.sh $i ${i/.wav/.flac}; done;