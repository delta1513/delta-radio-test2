import asyncio

from aiohttp import web

from delta_radio import app, pcs


async def on_shutdown(_):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


if __name__ == '__main__':
    _app = web.Application()
    _app.on_shutdown.append(on_shutdown)
    _app.router.add_get('/', app.index)
    _app.router.add_get('/client.js', app.javascript)
    _app.router.add_get('/play.svg', app.img)
    _app.router.add_get('/style.css', app.style)
    _app.router.add_post('/offer', app.offer)
    _app.router.add_post('/secrets', app.secrets)
    web.run_app(_app, access_log=None, host='0.0.0.0', port=8000)