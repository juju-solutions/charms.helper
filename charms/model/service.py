
from charms.model import unit


def name():
    """The name service group this unit belongs to"""
    return unit.name().split('/')[0]