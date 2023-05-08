import os
from typing import Set

from aiortc import RTCPeerConnection
from aiortc.contrib.media import MediaRelay
from dotenv import load_dotenv

from delta_radio.delta_radio_player import DeltaRadioPlayer

load_dotenv()

stream_player = DeltaRadioPlayer(os.getenv('RADIO_MUSIC_DIR', '/'))
stream_relay = MediaRelay()
pcs: Set[RTCPeerConnection] = set()