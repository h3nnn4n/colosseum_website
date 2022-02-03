import hashlib

import magic
from django.urls import reverse


def agent_filepath(agent, filename):
    return f"agents/{agent.owner.id}/{agent.id}/{filename}"


def replay_filepath(match, filename):
    return f"replays/{match.tournament.id}/{match.id}/{filename}"


def hash_file(file, blocksize=2 ** 20):
    m = hashlib.sha1()
    while True:
        buf = file.read(blocksize)
        if not buf:
            break
        m.update(buf)
    return m.hexdigest()


def guess_mime(file):
    file.seek(0)
    mime = magic.from_buffer(file.read(), mime=True)
    file.seek(0)
    return mime


def get_api_urls_for_pks(pks, view_name, request):
    return [
        request.build_absolute_uri(reverse(view_name, kwargs={"pk": pk})) for pk in pks
    ]
