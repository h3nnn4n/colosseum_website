import hashlib


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
