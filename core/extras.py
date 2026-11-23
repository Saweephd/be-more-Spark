"""Small pieces of everyday behavior that do not need the model:
which game was asked for, the spoken shutdown, and the night clock hours.
Everything here is plain logic so it can be tested without BMO's hardware."""
import datetime
import re

GAME_TITLES = {"mazee_run": "Mazee Run", "bmo_catch": "BMO Catch", "angry_poppa": "Angry Poppa",
               "uncle_t": "Uncle T's Big Adventure", "scary_babies": "Scary Babies",
               "soldiers_vs_spies": "Soldiers vs Spies", "black_warrior": "Black Warrior",
               "big_move": "The Big Move", "air_hockey": "Air Hockey",
               "alien_storm": "Alien Storm: Tom Cat Alley",
               "music_teacher": "Music Teacher's Pet", "vampires": "Vampires, Oh Well..."}

# Speech to text rarely spells the names right, so each game lists the ways it is heard.
_GAME_WORDS = {
    "mazee_run": r"(ma[yi]?[sz]+(e+|y|ie|ey)|mazy|maisie|maisy|daisy|doggy|dog|puppy) ?(run|ron|runner)|the dog game|the running game",
    "bmo_catch": r"(bmo|beemo|bemo|bimo|be more)('?s)? ?(catch|cash|ketch)|catch game|the catching game|\bcatch\b",
    "angry_poppa": r"angry ?(poppa|papa|pop|poppy|pappa|puppet|papas?)|the gnat game|the bug game|gnat(s)? game",
    "soldiers_vs_spies": r"soldiers? ?(vs|versus|v|and|against|verses)? ?(the )?spies|soldiers? game|spy game|army game|the war game",
    "scary_babies": r"(scary|scarey|scared|scarry) ?bab(y|ies|e?s)|the baby game|bab(y|ies) game|big baby",
    "black_warrior": r"black ?(warrior|worrier|warriors|water)|the (fighting|karate|kung fu|street fighting) game|quick'?s game",
    "big_move": r"(the )?big move|moving (day )?game|the moving game|whitney'?s game",
    "air_hockey": r"air ?hockey|hockey|(momma|mama|mom|mother) rose'?s? game|rose'?s game",
    "alien_storm": r"alien ?storm|tom ?cat( ?alley)?|the (jet|plane|airplane|fighter|flying|f ?14) game|alex'?s game|k ?j'?s game",
    "music_teacher": r"music ?teacher'?s? ?pet|teacher'?s? ?pet|the (music|piano|note|notes|keyboard) game|heather'?s game|piano lessons?|music lessons?",
    "vampires": r"vampires?( oh well)?|oh well|the (vampire|monster|zombie|werewolf|spooky|scary monster) game|lucas'?s? game|day ?walker|monster hunter",
    "uncle_t": r"uncle ?(t|tee|tea|tease|ts|t's)\b|big adventure|the (driving|car|racing|chase|cop) game|driving game",
}
_PLAY = r"\b(play|start|launch|open|run|load|i want to play|let'?s play|can we play)\b"
_MENU = (r"\b(what|which) games\b|\bgames? (menu|list)\b|\b(show|list)( me)?( the| your)? games\b|"
         r"\blet'?s play a game\b|\bplay a (video )?game\b|\bplay (some )?games\b|\bi want to play a game\b|\bgame time\b")


def _norm(text):
    return re.sub(r"[^a-z0-9' ]+", " ", (text or "").lower()).strip()


def match_game(text):
    """Return a game name, "menu", or None for anything that is not a game request."""
    t = _norm(text)
    if not t:
        return None
    for name, words in _GAME_WORDS.items():
        if re.search(words, t) and (re.search(_PLAY, t) or len(t.split()) <= 4):
            return name
    if re.search(_MENU, t):
        return "menu"
    return None


_SHUTDOWN = (r"\b(shut ?down|power (off|down)|turn (yourself )?off|switch (yourself )?off)\b|"
             r"\bgo to sleep for the night\b|\bshut yourself (down|off)\b")
_NOT_SHUTDOWN = r"\b(how|why|what|when|should|can you explain|computer|laptop|tv|television|light|lights|lamp|music|screen)\b"


def match_shutdown(text):
    t = _norm(text)
    return bool(re.search(_SHUTDOWN, t)) and not re.search(_NOT_SHUTDOWN, t)


_TV = r"\b(tv|television|big screen)\b"
_TV_ON = r"\b(show|put|cast|mirror|send|go|get)\b"
_TV_OFF = (r"\b(come back|stop (showing|casting|mirroring)|get off|go off|off the (tv|television|big screen)|"
           r"take (yourself|bmo|it) off|turn off the (tv|television) (mirror|cast))\b")


def match_tv(text):
    """'on' for "BMO, show me on the TV", 'off' for "come back" or "get off the TV", else None."""
    t = _norm(text)
    if re.search(r"\bcome back\b", t) and len(t.split()) <= 5:
        return "off"
    if not re.search(_TV, t):
        return None
    if re.search(_TV_OFF, t):
        return "off"
    if re.search(_TV_ON, t) and re.search(r"\bon (the |my |our )?(tv|television|big screen)\b", t):
        return "on"
    return None


_PHONE = r"\b(hot ?spots?|my (i ?)?phone|your phone|the phone|phone'?s? (wi ?fi|internet|network))\b"
_HOME_NET = r"\b(home|house|regular|normal) (wi ?fi|network|internet)\b"
_MOVE = r"\b(switch|connect|change|go|hop|jump|move|get|use|join|shift|swap)\w*\b"


def match_wifi(text):
    """'hotspot' for "switch to my phone hotspot", 'home' for "go back to the home wifi",
    'status' for "what wifi are you on", else None."""
    t = _norm(text)
    if re.search(r"\b(what|which) (wi ?fi|network|internet)\b.*\b(you|bmo)\b|\bare you (online|connected|on (the )?(wi ?fi|internet))\b", t):
        return "status"
    if not re.search(_MOVE, t):
        return None
    if re.search(_HOME_NET, t):
        return "home"
    if re.search(r"\bhot ?spots?\b", t) or (re.search(_PHONE, t) and re.search(r"\b(wi ?fi|internet|network|online|connect\w*)\b", t)):
        return "hotspot"
    return None


def match_tv_mode(text):
    """'on' for "TV mode on" or "let's play on the TV", 'off' for "TV mode off" or "play on BMO", else None."""
    t = _norm(text)
    big = r"(tv|television|big screen)"
    if re.search(r"\b%s mode (is )?off\b|\b(turn|switch) off (the )?%s mode\b|\bstop (playing|the games?) on (the )?%s\b" % (big, big, big), t):
        return "off"
    if re.search(r"\bplay\w* (\w+ ){0,3}on (bmo|you|your (own |little )?screen|the little screen)\b|\bplay (right )?here\b", t):
        return "off"
    if re.search(r"\b%s mode\b" % big, t):
        return "on"
    if re.search(r"\b(play|games?|gaming)\b.*\bon (the |my |our )?%s\b" % big, t):
        return "on"
    return None


def match_screensaver(text):
    t = _norm(text)
    return bool(re.search(r"\b(start|show|turn on|put on|go to|play)\b.*\bscreen ?saver\b|\bscreen ?saver (on|now|please)\b", t))


def match_yes(text):
    return bool(re.search(r"\b(yes|yeah|yep|yup|sure|do it|please do|go ahead|i'?m sure|affirmative|correct|ok|okay)\b", _norm(text)))


def match_no(text):
    return bool(re.search(r"\b(no|nope|nah|don'?t|do not|cancel|never ?mind|stop|wait|not now|stay)\b", _norm(text)))


# ---------- night clock ----------
def night_clock_active(now=None, start_hour=22, end_hour=7):
    """True during the hours when an idle BMO shows the clock, not its face."""
    hour = (now or datetime.datetime.now()).hour
    if start_hour == end_hour:
        return False
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def clock_text(now=None, twelve_hour=True):
    """(time, date) strings for the clock face, for example ("10:42", "Mon 16 Nov")."""
    now = now or datetime.datetime.now()
    if twelve_hour:
        hour = now.hour % 12 or 12
        t = "%d:%02d" % (hour, now.minute)
    else:
        t = "%02d:%02d" % (now.hour, now.minute)
    return t, now.strftime("%a %d %b").replace(" 0", " ")


def spoken_result(result):
    """One sentence BMO says after a game."""
    if not result or not result.get("played"):
        return "Okay! We can play another time."
    title = result.get("title") or "that game"
    score = int(result.get("score", 0))
    if result.get("new_best") and score > 0:
        return "You scored %d in %s. That is a new best score!" % (score, title)
    return "You scored %d in %s. Your best is %d." % (score, title, int(result.get("best", 0)))
