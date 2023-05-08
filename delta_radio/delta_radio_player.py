import os
import glob
import time
import errno
import random
import asyncio
import logging
import datetime
import threading
import fractions
from typing import Union, Generator, List, Optional, Set

import av
from av.container import Container
from av.audio.frame import AudioFrame
from aiortc import MediaStreamTrack
from aiortc.contrib.media import REAL_TIME_FORMATS, PlayerStreamTrack
from aiortc.mediastreams import AUDIO_PTIME
from dotenv import load_dotenv

load_dotenv()

AUDIO_GLOB = os.getenv('AUDIO_GLOB', '*.mp3')
INTERMISSION_TIMEOUT_HOURS = 1
INTERMISSION_TIMEOUT = datetime.timedelta(hours=INTERMISSION_TIMEOUT_HOURS)


class DeltaRadioMediaSource:
    def __init__(self, radio_root: str):
        self.root = radio_root
        self.current_track_name: str = None
        self.current_container: Container = None

        assert len(self.tracks) > 0, f"No tracks have been found in {self.root}, aborting..."

        self.last_intermission = datetime.datetime.now()
    
    @property
    def tracks(self) -> List[str]:
        '''
        Reason why this is a property is because we want to include newly added songs without 
        the need torestart the server
        '''
        return list(glob.glob(os.path.join(self.root, f'{AUDIO_GLOB}')))
    
    def media_container_generator(self):
        '''Infinite generator which delivers containers of audio'''
        while True:
            self.current_track_name = self.get_next_track()
            self.current_container = av.open(self.current_track_name)
            yield self.current_container
    
    def get_next_track(self) -> str:
        if (datetime.datetime.now() - self.last_intermission) > INTERMISSION_TIMEOUT:
            self.last_intermission = datetime.datetime.now()
            return self.get_random_intermission()
        else:
            return self.get_random_track()
    
    def get_random_track(self):
        return random.choice(list(filter(lambda x: not x.startswith('intermission_') and x != self.current_track_name, self.tracks)))
    
    def get_random_intermission(self) -> str:
        try:
            return random.choice(list(filter(lambda x: x.startswith('intermission_') and x != self.current_track_name, self.tracks)))
        except IndexError:
            return self.get_random_track()


class DeltaRadioPlayer(DeltaRadioMediaSource):
    def __init__(self, radio_root: str):
        super().__init__(radio_root)
        self.__containers = self.media_container_generator()
        self.__thread: Optional[threading.Thread] = None
        self.__thread_quit: Optional[threading.Event] = None

        # examine streams
        self.__started: Set[PlayerStreamTrack] = set()
        self.__audio = PlayerStreamTrack(self, kind="audio")
    
    @property
    def _throttle_playback(self) -> bool:
        container_format = set(self.current_container.format.name.split(","))
        return not container_format.intersection(REAL_TIME_FORMATS)

    @property
    def audio(self) -> MediaStreamTrack:
        """
        A :class:`aiortc.MediaStreamTrack` instance if the file contains audio.
        """
        return self.__audio

    def _start(self, track: PlayerStreamTrack) -> None:
        self.__started.add(track)
        if self.__thread is None:
            self.__thread_quit = threading.Event()
            self.__thread = threading.Thread(
                name="media-player",
                target=worker_decode_music_library,
                args=(
                    asyncio.get_event_loop(),
                    self.__containers,
                    self.__audio,
                    self.__thread_quit,
                ),
            )
            self.__thread.start()

    def _stop(self, track: PlayerStreamTrack) -> None:
        #self.__started.discard(track)

        if not self.__started and self.__thread is not None:
            self.__thread_quit.set()
            self.__thread.join(1)
            self.__thread = None


def worker_decode_music_library(loop, containers, audio_track, quit_event):
    audio_sample_rate = 48000
    audio_samples = 0
    audio_time_base = fractions.Fraction(1, audio_sample_rate)
    audio_resampler = av.AudioResampler(
        format="s16",
        layout="stereo",
        rate=audio_sample_rate,
        frame_size=int(audio_sample_rate * AUDIO_PTIME),
    )

    video_first_pts = None

    frame_time = None
    start_time = time.time()

    for container in containers:
        container_format = set(container.format.name.split(","))
        throttle_playback = not container_format.intersection(REAL_TIME_FORMATS)

        logging.info("Now playing %s", container.name)

        while not quit_event.is_set():
            try:
                frame = next(container.decode(container.streams[0]))
            except Exception as exc:
                if isinstance(exc, av.FFmpegError) and exc.errno == errno.EAGAIN:
                    time.sleep(0.01)
                    continue
            
                container.close()

                if isinstance(exc, StopIteration):
                    break

                if audio_track:
                    asyncio.run_coroutine_threadsafe(audio_track._queue.put(None), loop)
                
                break

            # read up to 1 second ahead
            if throttle_playback:
                elapsed_time = time.time() - start_time
                if frame_time and frame_time > elapsed_time + 1:
                    time.sleep(0.1)

            if isinstance(frame, AudioFrame) and audio_track:
                try:
                    for frame in audio_resampler.resample(frame):
                        # fix timestamps
                        frame.pts = audio_samples
                        frame.time_base = audio_time_base
                        audio_samples += frame.samples

                        frame_time = frame.time
                        asyncio.run_coroutine_threadsafe(audio_track._queue.put(frame), loop)
                except ValueError:
                    # ValueError: Frame does not match AudioResampler setup
                    logging.error("Track %s is not compatible with audio resampler", container.name)
                    break
        
        if quit_event.is_set():
            break