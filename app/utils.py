def agent_filepath(agent, filename):
    return f"agents/{agent.owner.id}/{agent.id}/{filename}"


def replay_filepath(match, filename):
    return f"replays/{match.tournament.id}/{match.id}/{filename}"
