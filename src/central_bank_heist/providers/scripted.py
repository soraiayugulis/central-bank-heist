"""Deterministic offline fallback provider for testing and no-API-key play."""

from __future__ import annotations

from typing import Iterator

_TIER_RESPONSES: dict[int, dict[str, list[str]]] = {
    1: {
        "boss": [
            "I... look, it was hectic. Everyone was running. I can't remember the details right now.",
            "What? The smoke... everything happened so fast. I don't know what you want me to say.",
        ],
        "traitor": [
            "Huh? I don't... it was chaos, man. Can't think straight with those sirens.",
            "What are you even asking me? My head's spinning from all this.",
        ],
        "ghost": [
            "I... I'm not sure what you're getting at. It was dark. Smoky. Hard to recall.",
            "Look, everything blurred together in that smoke. I can barely remember my own steps.",
        ],
        "spark": [
            "The numbers... no, wait. I had it but— the charge was— look, I'm blanking here.",
            "I can't— the calculations are all jumbled in my head right now.",
        ],
        "brick": [
            "I... uh... carried stuff. That's it. Can't think of nothing else.",
            "Huh? I dunno. Just did my job. Can't remember more than that.",
        ],
        "wheels": [
            "Look, I— the car was— I mean... everything happened so fast, okay?",
            "I was... I don't even know where to start. It's all a blur.",
        ],
        "shade": [
            "I— what? No, I... I can't think straight. Too much going on.",
            "Please, I... my mind is racing. I can't piece it together right now.",
        ],
        "manager": [
            "P-please, I don't— I was blindfolded most of the time. I can barely—",
            "I... I'm sorry, I don't know. Everything went black after the... the hit.",
        ],
    },
    2: {
        "boss": [
            "I was at the bank door supervising the bags going into the trunk. But... I'll admit I'm the only one with the trunk keys, and I wasn't paying close attention.",
            "I watched the loading from the door. Didn't check a single bag — just wanted this last job done. Yeah, the keys are mine. Draw your own conclusions.",
        ],
        "traitor": [
            "I was loading bags like everyone else. Nothing special. But you know, the smoke was wild — twenty extra seconds where nobody could see a thing. Who knows what happened in there.",
            "Same as always — I carried bags from the vault to the car. Couldn't see much in that smoke, could you? I was just doing my part.",
        ],
        "ghost": [
            "I was the first one to the car. Found a hostage inside — unconscious. Tried to wake him, no luck. I'll be honest, being alone at that car looks bad, I know.",
            "Reached the car before everyone else. There was someone knocked out in there. I checked on him. Yeah, I know how that looks — me alone at the car.",
        ],
        "spark": [
            "I was at the vault handling the charges. And yes — I messed up the calculation. Twenty extra seconds of smoke. Only I had goggles to see through it. I know that makes me look bad.",
            "The smoke was my fault — miscalculated the charge by twenty seconds. My goggles meant I was the only one who could see. Convenient for a saboteur, right? But it was a genuine mistake.",
        ],
        "brick": [
            "Carried the bags from the vault to the car, just like Cap told me. Driver wasn't there when I arrived so I waited. Had a cigarette. That's it.",
            "Did my job — bags from point A to point B. Wheels was AWOL when I got to the car, so I smoked and waited. Nothing complicated.",
        ],
        "wheels": [
            "Look, I left the car, okay? The heist was taking too long and I went to find Cap for the trunk key. Couldn't find him. When I got back everyone was there staring at me. That's the truth — I shouldn't have left the car.",
            "I went looking for Cap because the job was dragging. Couldn't find him anywhere in the smoke. Came back and everyone was waiting. I know I shouldn't have left — that was my one job.",
        ],
        "shade": [
            "I was... around. During the loading. I didn't carry any bags — I know that looks suspicious. I'm just... nervous, okay? This whole thing has me on edge.",
            "I was near the action but I didn't help with the bags. No real excuse for that. And yeah, I'm nervous. Can you blame me? The feds are coming.",
        ],
        "manager": [
            "I was tied up in the car. I saw the boss arguing with the driver about leaving. Then someone came and hit me — I blacked out. I should have seen more, but I was terrified. I'm sorry.",
            "They dragged me into the car during the smoke. I saw an argument between two of you — about someone leaving the car. Then a slap, and everything went dark. I wish I could remember more.",
        ],
    },
    4: {
        "boss": [
            "I supervised the loading — yeah, the keys are mine. But think about this: who had time to swap those bags? The smoke expert gave everyone twenty free seconds of darkness. Maybe look at who benefited from that chaos.",
            "Look, I had the keys, I was distracted. Fine. But the real question is who tampered with the explosives to get that extra smoke time. The answer is right there.",
        ],
        "traitor": [
            "I loaded bags, same as the others. But you want to know what I think? The driver left the car unguarded. Anyone could have walked up to the trunk in that window. Ask Wheels where he really went.",
            "Hey, I did my part. But here's what bugs me — the boss didn't check a single bag. He's the one with the keys. And now he wants to retire to some island? Convenient, isn't it.",
        ],
        "ghost": [
            "I got to the car first, found the hostage, checked on him. But listen — the driver was supposed to be at the car and wasn't. The accomplice didn't carry a single bag. Those are the loose threads.",
            "Think about it — who altered the charges to get extra smoke? And who conveniently didn't help carry any bags during that window? Start there, not with the person who checked on an unconscious civilian.",
        ],
        "spark": [
            "My smoke mistake gave everyone a window — but I had goggles, so I saw movement near the bags. Someone was crouching, doing something. I couldn't make out who in all that chaos. Focus on who had opportunity near the bags.",
            "Yes, I caused the smoke. But through my goggles I saw someone hunched over the bags — doing something they shouldn't have been. I can't say who. But someone used those twenty seconds.",
        ],
        "brick": [
            "Did my job, clean and simple. But the driver — Wheels — he wasn't at the car. And Cap was distracted the whole time. Between the guy who left his post and the boss who didn't check the bags, there's your answer.",
            "I carried bags, I waited, I smoked. Boring but honest. You want suspicious? The driver bailed on the car and Cap was zoning out instead of checking the load. Talk to them.",
        ],
        "wheels": [
            "Okay, I left the car. Bad call. But when I was coming back, I saw a shadow near the trunk. Couldn't tell who in the dark. Someone was at that trunk when they shouldn't have been.",
            "Listen — I messed up leaving the car. But on my way back I saw someone near the trunk, moving around. It was too dark to see who. That's the person you want.",
        ],
        "shade": [
            "I didn't carry bags, okay. I was dealing with... other things. But look at the big picture — someone had to have been near those bags during the smoke to swap them. Who was alone and had the chance? Not me.",
            "I'm nervous because this is serious. But focus on the facts: who was alone near the bags in the smoke? Who had time to make the switch? The driver left the car. The boss wasn't watching. Start there.",
        ],
        "manager": [
            "Before I blacked out I heard two voices. They were whispering about needing to 'plant' something. I don't know what, but planting something in a car full of stolen money — that can't be good.",
            "I heard whispers — two people, right before someone hit me. They said something about 'planting' or 'implanting' something. I couldn't see who. But two people were doing something secret near the car.",
        ],
    },
    6: {
        "boss": [
            "Don't waste my time with that question. You want answers? Look at the driver — he LEFT the car. His one job. While everyone's bags went unsupervised into an unguarded trunk. That's your lead.",
            "I'm not answering that. Here's what matters: Shade didn't carry a single bag and he's sweating bullets. When's the last time you saw someone this nervous who has nothing to hide?",
        ],
        "traitor": [
            "Nice try, but that's the wrong question. You should be asking Cap why he didn't check a single bag when he's the one with the keys. A boss who doesn't verify the score? Come on.",
            "You're barking up the wrong tree. The explosives guy just happened to give everyone a twenty-second blackout? And he's the only one who could see through it? Think about THAT.",
        ],
        "ghost": [
            "That's not what matters right now. What matters is Cap is sitting on trunk keys and retirement tickets while the money has vanished. He had means, he had motive, and he had access. It doesn't add up.",
            "Wrong question. The person you need to pressure is the boss. Only one with keys, distracted during loading, and from what I hear, he's got some expensive travel plans. Put those pieces together.",
        ],
        "spark": [
            "I'm not getting into that. What I AM going to say is this: through my goggles I saw someone crouching near the bags during the blackout. Someone USED those twenty seconds. Find that person.",
            "Let me redirect you. The driver abandoned the car. The accomplice carried zero bags. Two people with no good excuse for where they were during the most critical minutes. Start there.",
        ],
        "brick": [
            "Nah, that's not it. Here's what I know: Shade was nowhere near the bags and his hands are shaking like a leaf. I've done enough jobs to know what guilt looks like.",
            "Wrong question. Ask the driver why he was sneaking around instead of sitting in the car. He was supposed to be behind the wheel and he was gone. GONE. That's suspicious as hell.",
        ],
        "wheels": [
            "Don't put this on me. I saw a shadow at the trunk — someone was there who shouldn't have been. And Shade? He didn't lift a single bag and now he looks like he's about to pass out. Coincidence?",
            "I'm not answering that. You want to know who's really sweating? The one person who didn't help carry anything. The one who's got no excuse and can barely look anyone in the eye. Think about it.",
        ],
        "shade": [
            "That's— that's not the point! The boss had the keys! He was RIGHT THERE and didn't check anything! Anyone could have— I mean, the bags went straight to his trunk unchecked!",
            "Don't look at me like that! The driver abandoned his post! The car was wide open! Anyone walking by could have done anything to those bags while Wheels was off wandering!",
        ],
        "manager": [
            "I— please, don't yell at me! But... but I know something. Two people were whispering. 'Planting' something. That's all I heard before someone knocked me out. Someone in this room hit me, and someone else was helping them.",
            "I can't answer that, I was unconscious! But before I went out — two voices. Planning something. Planting something. The person who hit me is here in this room and they know exactly what happened.",
        ],
    },
}

# Alias tiers 3→2 and 5→4 (same behavior, different source tiers share responses)
_TIER_RESPONSES[3] = _TIER_RESPONSES[2]
_TIER_RESPONSES[5] = _TIER_RESPONSES[4]

_ANNOYANCE_RESPONSES: dict[str, dict[str, list[str]]] = {
    "mild": {
        "boss": ["I already told you. Pay attention."],
        "traitor": ["Didn't I just answer this? You deaf or something?"],
        "ghost": ["I've already covered this. Let's move on."],
        "spark": ["I literally just explained this. Were you not listening?"],
        "brick": ["Asked and answered. Next."],
        "wheels": ["Look, I already said — weren't you listening?"],
        "shade": ["I— I already said! Why are you asking again?"],
        "manager": ["P-please, I already told you everything I know about that..."],
    },
    "hostile": {
        "boss": ["Ask me that again and we're going to have a problem. I said what I said."],
        "traitor": ["Are you trying to waste time? Because that's what you're doing. Back off."],
        "ghost": ["Enough. I've answered this. You're burning through our clock asking the same thing."],
        "spark": ["Stop! I already told you everything I know about that! This is wasting everyone's time!"],
        "brick": ["I'm done repeating myself. Ask me something new or shut up."],
        "wheels": ["For the last time — I TOLD you! Stop circling back and do something useful!"],
        "shade": ["STOP asking me that! I can't— I already— just leave me alone about it!"],
        "manager": ["Please stop! I already told you! I'm begging you, ask someone else!"],
    },
}

_ROUND_ROBIN_INDEX: dict[str, int] = {}


def _pick_response(npc_id: str, pool: list[str]) -> str:
    """Round-robin through a response pool."""
    key = f"{npc_id}:{id(pool)}"
    idx = _ROUND_ROBIN_INDEX.get(key, 0)
    response = pool[idx % len(pool)]
    _ROUND_ROBIN_INDEX[key] = idx + 1
    return response


class ScriptedProvider:
    """Deterministic provider that returns canned responses based on die tier."""

    def __init__(self) -> None:
        self._npc_id: str = ""
        self._die_tier: int = 3
        self._annoyance: str = "none"

    def set_context(self, npc_id: str, die_tier: int, annoyance: str = "none") -> None:
        """Set context for the next completion call."""
        self._npc_id = npc_id
        self._die_tier = die_tier
        self._annoyance = annoyance

    def complete(self, system: str, user: str) -> str:
        """Return a canned response."""
        if self._annoyance in ("mild", "hostile"):
            pool = _ANNOYANCE_RESPONSES.get(self._annoyance, {}).get(self._npc_id, ["..."])
            return _pick_response(self._npc_id, pool)

        tier = max(1, min(6, self._die_tier))
        pool = _TIER_RESPONSES.get(tier, {}).get(self._npc_id, ["..."])
        return _pick_response(self._npc_id, pool)

    def stream(self, system: str, user: str) -> Iterator[str]:
        """Yield the full response as a single token (instant for scripted)."""
        yield self.complete(system, user)
