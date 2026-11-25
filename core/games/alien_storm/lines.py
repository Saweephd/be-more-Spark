"""Every spoken line in Alien Storm: Tom Cat Alley, in one place.

The three lines marked EXACT are used word for word, every time, and are never replaced by another line."""

HIT_KJ = "Come on man, do some of that pilot ish!"          # EXACT: KJ, on every hit player one takes
FLEX_ALEX = "I make this ish look good."                     # EXACT: Alex, grinning and flexing, in every cutscene
FLEX_KJ = "That's some cap, twin."                           # EXACT: KJ's answer

IMPROV_ALEX = "After I save the world, I gotta go do an improv show."
KILL_KJ = ("Nothing but net!", "Just like the team I coach!")
# More of Alex, by request: he was not getting enough screen time.
KILL_ALEX = ("Tell me somebody saw that.", "And... scene!", "Yes, and... another one!", "That one goes in the highlight reel.",
             "They should be paying to watch this.")
LOOP_ALEX = ("Watch this.", "Improv, baby.", "Hold my headset.")
CARD_ALEX = "Is this my good side? Trick question. They are both good."
STAGE_ALEX = ("So an alien walks onto an aircraft carrier...", "...and I said: sir, this is a no flying saucer zone.",
              "Thank you! I am here all week. Unless there is another invasion.")
SCREEN_TIME_HEATHER = "I hope Miles and Felix are minding their screen time."
SCREEN_TIME_STEPHEN = "I bet they are playing Soldiers vs Spies."
REEL_HEATHER = "I wonder if this would look good on a live reel."
OLD_MAN_STEPHEN = "Not bad for an old man."
HIT_HEATHER = "Honey, they are shooting at us!"

# Extra chatter in the same voices. (who, mood, line)
BOSS = {
    "lance": [("kj", "alarm", "Big contact dead ahead. That thing is shaped like a sword."),
              ("alex", "grin", "Then let's go break it.")],
    "thunderhead": [("kj", "alarm", "It's hiding in the storm. Watch for the lightning!"),
                    ("alex", "calm", "I see it. Hang on, twin.")],
    "leviathan": [("kj", "alarm", "That is not a bomber. That is a whole airport."),
                  ("alex", "grin", "Good. More to shoot at.")],
    "core": [("kj", "alarm", "That's the Red Star. That's what is running all of this."),
             ("alex", "calm", "One last game. Let's finish it.")],
}
LOW_HEALTH = {"kj": "We are leaking everything, Alex. Fly it gentle.", "heather": "Stephen, the jet is on fire a little bit."}
PICKUP = {"kj": "I'll take that.", "heather": "Ooh, presents."}
LOCK = {"kj": "Four locked. Fox three!", "heather": "Locked on. Sending it!"}
DOWN = {"kj": "We're going in! Eject, eject!", "heather": "This is why I wanted to drive!"}
STAGE_START = [
    [("kj", "calm", "Radar is full of them. Guns are hot.")],
    [("kj", "calm", "Weather is getting ugly. Stay out of the clouds.")],
    [("kj", "calm", "Islands below. They are coming up the channel.")],
    [("kj", "alarm", "We are flying over it. The whole thing is one ship.")],
]
