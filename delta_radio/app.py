import os
import uuid
import json
import logging

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, PlayerStreamTrack

from delta_radio import pcs, stream_relay, stream_player
from delta_radio.delta_radio_player import DeltaRadioPlayer

logger = logging.getLogger("pc")
logging.basicConfig(level=logging.INFO)


ROOT = os.path.dirname(__file__)

def fetch_static_content(static_path: str):
    with open(os.path.join(ROOT, 'static/', static_path)) as f:
        content = f.read()
    return content


async def index(request):
    return web.Response(content_type='text/html', text=fetch_static_content('index.html'))

async def javascript(request):
    return web.Response(content_type='application/javascript', text=fetch_static_content('client.js'))

async def style(request):
    return web.Response(content_type='text/css', text=fetch_static_content('style.css'))

async def img(request):
    return web.Response(content_type='image/svg+xml', text=fetch_static_content('play.svg'))

async def ping(request):
    return web.Response(content_type='text/html', text='pong')


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])

    pc = RTCPeerConnection()
    pc_id = f'PeerConnection({uuid.uuid4()})'
    pcs.add(pc)

    proxy_player = stream_relay.subscribe(stream_player.audio)

    @pc.on('iceconnectionstatechange')
    async def on_iceconnectionstatechange():
        if pc.connectionState in ('failed', 'disconnected', 'closed'):
            stream_relay._stop(proxy_player)
            await pc.close()
            pcs.discard(pc)

    @pc.on('track')
    def on_track(track):
        pc.addTrack(proxy_player)

    # handle offer
    await pc.setRemoteDescription(offer)

    # send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type='application/json',
        text=json.dumps(
            {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}
        ),
    )