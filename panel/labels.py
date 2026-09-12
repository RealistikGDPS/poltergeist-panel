from gdformat.enums import Difficulty
from gdformat.enums import Length
from gdformat.enums import Rating
from gdformat.enums import TimelyType
from gdformat.enums import Visibility
from poltergeist_core.resources import BanType
from poltergeist_core.resources import UserKind

DIFFICULTY = {
    int(Difficulty.NA): "N/A",
    int(Difficulty.AUTO): "Auto",
    int(Difficulty.EASY): "Easy",
    int(Difficulty.NORMAL): "Normal",
    int(Difficulty.HARD): "Hard",
    int(Difficulty.HARDER): "Harder",
    int(Difficulty.INSANE): "Insane",
    int(Difficulty.EASY_DEMON): "Easy demon",
    int(Difficulty.MEDIUM_DEMON): "Medium demon",
    int(Difficulty.HARD_DEMON): "Hard demon",
    int(Difficulty.INSANE_DEMON): "Insane demon",
    int(Difficulty.EXTREME_DEMON): "Extreme demon",
}
LENGTH = {
    int(Length.TINY): "Tiny",
    int(Length.SHORT): "Short",
    int(Length.MEDIUM): "Medium",
    int(Length.LONG): "Long",
    int(Length.XL): "XL",
    int(Length.PLATFORMER): "Platformer",
}
RATING = {
    int(Rating.NONE): "None",
    int(Rating.EPIC): "Epic",
    int(Rating.LEGENDARY): "Legendary",
    int(Rating.MYTHIC): "Mythic",
}
VISIBILITY = {
    Visibility.PUBLIC: "Public",
    Visibility.FRIENDS: "Friends",
    Visibility.UNLISTED: "Unlisted",
}
TIMELY = {
    TimelyType.DAILY: "Daily",
    TimelyType.WEEKLY: "Weekly",
    TimelyType.EVENT: "Event",
}
BAN = {ban_type: ban_type.value.title() for ban_type in BanType}
KIND = {kind: kind.value.title() for kind in UserKind}
GAUNTLET = {
    1: "Fire",
    2: "Ice",
    3: "Poison",
    4: "Shadow",
    5: "Lava",
    6: "Bonus",
    7: "Chaos",
    8: "Demon",
    9: "Time",
    10: "Crystal",
    11: "Magic",
    12: "Spike",
    13: "Monster",
    14: "Doom",
    15: "Death",
    16: "Forest",
    17: "Rune",
    18: "Force",
    19: "Spooky",
    20: "Dragon",
    21: "Water",
    22: "Haunted",
    23: "Acid",
    24: "Witch",
    25: "Power",
    26: "Potion",
    27: "Snake",
    28: "Toxic",
    29: "Halloween",
    30: "Treasure",
    31: "Ghost",
    32: "Spider",
    33: "Gem",
    34: "Inferno",
    35: "Portal",
    36: "Strange",
    37: "Fantasy",
    38: "Christmas",
    39: "Surprise",
    40: "Mystery",
    41: "Cursed",
    42: "Cyborg",
    43: "Castle",
    44: "Grave",
    45: "Temple",
    46: "World",
    47: "Galaxy",
    48: "Universe",
    49: "Discord",
    50: "Split",
    51: "NCS I",
    52: "NCS II",
}


def gauntlet(gauntlet_id: int) -> str:
    return GAUNTLET.get(gauntlet_id, f"Gauntlet {gauntlet_id}")
