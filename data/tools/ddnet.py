from collections import namedtuple

Player = namedtuple('Player', ['maps', 'servers'])
PlayerMap = namedtuple('PlayerMap', ['team_rank', 'rank', 'nrFinishes', 'firstFinish', 'time'])

