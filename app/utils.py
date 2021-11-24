def agent_filepath(agent, filename):
    return f"{agent.owner.username}/{agent.name}/{filename}"


def replay_filepath(match, filename):
    return f"{match.tournament.id}/{match.id}/{filename}"
