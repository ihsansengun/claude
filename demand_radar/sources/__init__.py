from . import appstore, github, hackernews, producthunt, reddit

REGISTRY = {m.NAME: m for m in (hackernews, reddit, github, appstore, producthunt)}
