"""
"Need help" content for every exercise: how to do it (steps), example answers / a model to listen to.

  steps     3-4 plain-language steps per exercise type
  examples  model answers the learner can read and hear (browser speech synthesis):
              picture / conversation / advanced picture   written here, one per prompt, age-appropriate
              role-plays + extra picture scenes           their own `examples` (extra_exercises.py)
              reading / pacing / clear speech / loudness  the passage itself is the model
              sound drills, word rounds                   the items / words
  model     the text a "Listen to a model" button reads aloud

help_for(ex) never changes scoring or the plan - it is attached to each exercise in plan._decorate.
"""
from __future__ import annotations

STEPS: dict[str, list[str]] = {
    "reading": ["Press 🔊 Listen to hear the passage read slowly first.",
                "Press Start and read aloud, keeping pace with the highlighted word.",
                "Take a soft breath at each full stop or comma - pausing is good.",
                "Press I'm done, then tell us how it felt."],
    "pacing": ["Listen to the model once.", "Press Start and follow the highlight - don't rush ahead of it.",
               "Start each sentence gently, with an easy breath.", "Press I'm done when you reach the end."],
    "clear_speech": ["Listen to the model.", "Give every syllable its own beat - move your lips and tongue a bit more than usual.",
                     "Breathe before each sentence and finish every word clearly.", "Press I'm done at the end."],
    "loudness": ["Take a deep breath from your tummy.", "Press Start and say each phrase in a strong, healthy voice.",
                 "Keep the loudness meter in the green zone - strong, not shouting.", "Press I'm done at the end."],
    "sustained_vowel": ["Sit up straight and breathe in slowly through your nose.",
                        "Press Start and say a steady 'ahh' for as long as is comfortable.",
                        "Keep the sound smooth - no pushing or straining.", "Rest, then repeat up to three times before pressing I'm done."],
    "sound_drill": ["Listen to each item first.", "Press Start and say each item slowly, focusing on the target sound.",
                    "Tap the items that came out clearly.", "Press I'm done when you have said them all."],
    "picture": ["Look at the whole picture for a few seconds first.",
                "Press Start and describe it in your own words - who, what, where and why.",
                "Use the questions as a guide; answer them one by one.",
                "Stuck? Read or listen to the example answers below, then try again in your own words."],
    "conversation": ["Read or listen to the situation.", "Think for a moment about what you would really do.",
                     "Press Start and answer each question out loud in full sentences.",
                     "There are no wrong answers - the examples below show one way to answer."],
    "roleplay": ["Read the situation and imagine you are really there.",
                 "Press Start and answer each line out loud, one at a time.",
                 "Breathe before each answer and start softly.", "Peek at the example answers if you get stuck."],
    "daf": ["Put on headphones so you hear the delayed voice and not an echo.",
            "Press Start and read the passage at a calm pace.",
            "Let the delay slow you down - stretch your words a little.", "Press I'm done at the end."],
    "words": ["Look at the picture and the word.", "Press 🔊 Listen to hear the word, then say it slowly.",
              "A grown-up taps 😊 if it came out smoothly, 😐 if it was nearly there, 😟 if it was hard.",
              "Keep going until all the cards are done."],
}

# exercise id -> one model answer per prompt
EXAMPLES: dict[str, list[str]] = {
    # ---------------- bracket pictures ----------------
    "b1-picture": ["The girl is flying a kite.", "The kite is red.", "She is in the park.", "It is windy, so the kite goes up high."],
    "b2-picture": ["I can see lots of children and a teacher with a whistle.", "One child is going down the slide, one is on the swing and some children are playing ball.",
                   "I would like to join the ball game.", "The teacher is blowing a whistle to keep everyone safe."],
    "b3-picture": ["The water in the pot is boiling over.", "The fire is too high and the lid is on, so the bubbles push out.",
                   "The water could spill on the stove and put the flame out, or burn someone.",
                   "He should step back and ask an adult to turn the fire down."],
    "b4-picture": ["The stalls sell fresh vegetables and fruit.", "A vendor is weighing beans, and shoppers are choosing vegetables and carrying bags.",
                   "The street is crowded and a tuk-tuk is waiting to take shoppers home.",
                   "At the pola you talk to the sellers and bargain, but in a supermarket the prices are fixed."],
    "b5-picture": ["The runners are racing towards the finish line.", "One runner has fallen, so another runner has stopped to help him up.",
                   "The crowd is cheering, the winner is proud and the fallen runner is probably hurt but grateful.",
                   "It shows that helping others matters more than winning."],
    "b6-picture": ["One river is clean with fish and trees, but the other is dirty with rubbish and dark water.",
                   "A factory and people throwing waste have polluted the second river.",
                   "Fishermen, farmers and families who use the water are affected.",
                   "The community could stop dumping waste, plant trees and report the factory to the authorities."],
    "b7-picture": ["The bars show iced-drink sales each month and the line shows the temperature.",
                   "April had the highest sales, probably because it was the hottest month.",
                   "When the temperature rises, iced-drink sales rise too - they move together.",
                   "I would advise the owner to stock more iced drinks and hire extra staff before the hot months."],
    "b8-picture": ["The screen shows a project plan, so the team is probably planning the next steps of a project.",
                   "The presenter is pointing at the plan, one colleague is taking notes and another is checking a phone.",
                   "Not everyone is engaged - the person on the phone is not listening, but the note-taker is paying attention.",
                   "I would ask each person for one idea and agree on clear action points before ending."],
    # ---------------- bracket conversations ----------------
    "b1-conversation": ["I will choose hopscotch.", "I like it because I can jump high.", "I will play with my friend Nimmi.",
                        "If it rains, we can play a clapping game inside."],
    "b2-conversation": ["I feel worried because the test starts soon.", "I will look in my pencil case and under my desk first.",
                        "I could ask my friend or my teacher to lend me a pencil.", "I can keep my pencils in one place and check my bag every night."],
    "b3-conversation": ["We could have short eats, cake and games like musical chairs.",
                        "We will plan it during interval when our friend is not there and tell everyone to keep it secret.",
                        "We can give everyone a job, like decorating or bringing food.",
                        "I would say, thank you for being a great friend, and we will miss you."],
    "b4-conversation": ["First I would message the group and make a clear plan of who does what.",
                        "I would talk to them politely and ask if something is stopping them from helping.",
                        "If they still don't help, I would tell the teacher, because it is unfair to the rest of the group.",
                        "The fairest solution is to share the remaining work and let the teacher know who did each part."],
    "b5-conversation": ["No, I would not share it, because it has no source and might be false.",
                        "I would check the school's official page or ask a teacher.",
                        "False posts can cause panic, make people miss school and spread mistrust.",
                        "Always check where a post comes from before you share it."],
    "b6-conversation": ["I oppose a full-day ban.", "Phones help us contact parents in an emergency, and we use them for research in breaks.",
                        "Some say phones distract students, but we could ban them in class and allow them at break.",
                        "In conclusion, a sensible rule is better than a total ban - it teaches responsibility."],
    "b7-conversation": ["I would feel frustrated, but I would take a breath and wait until I was calm.",
                        "I would say privately, I noticed my schedule idea was presented - I'd like us to mention who suggested it.",
                        "If it happened again, I would explain to the manager politely and show my notes.",
                        "In future I would share my ideas by email so there is a written record."],
    "b8-conversation": ["I'm an accountant with five years of experience, and I enjoy working with numbers and people.",
                        "I want this job because it matches my skills, and I admire how your company supports its staff.",
                        "Good morning, my name is Nadeesha Perera, and I would like to book a dental check-up.",
                        "Is Tuesday at ten o'clock available? Thank you - so that's Tuesday the fourteenth at ten."],
    # ---------------- advanced pictures ----------------
    "b1-picture-advanced": ["The boy is blowing out the candles on the cake.", "The girl is holding a big balloon.",
                            "The dog wants a piece of the cake.", "After the candles go out, everyone claps and eats cake."],
    "b2-picture-advanced": ["The paint pot fell off the table and spilled on the floor.", "The girl is running to get a cloth.",
                            "The cat is walking away and leaving paw prints of paint behind.",
                            "We can wipe the floor together and keep the paint pots in the middle of the table."],
    "b3-picture-advanced": ["The road flooded because heavy rain could not go down the blocked drain.",
                            "The tuk-tuk is stuck in the water, and a man is helping to push it.",
                            "Plastic bags and rubbish are blocking the drain - people threw them on the road.",
                            "The neighbourhood could clean the drains and stop throwing rubbish on the street."],
    "b4-picture-advanced": ["A dansala is a stall that gives free food at Vesak - here they are serving rice and curry and drinks.",
                            "The volunteers are cooking and serving, and the child is handing out cups.",
                            "People give free food at Vesak to share kindness and to make merit.",
                            "I would make one line for food and another for drinks, with a volunteer guiding people."],
    "b5-picture-advanced": ["The student is explaining her solar-panel project to the judges.",
                            "He might be nervous because the judges are coming to his table next.",
                            "The volcano project erupted too early and the foam spilled over the table.",
                            "I would give first prize to the solar project, because it solves a real problem and is well explained."],
    "b6-picture-advanced": ["The volunteers are picking up plastic and sorting it into bags to keep the beach clean.",
                            "The turtle is caught in a plastic net and needs to be freed.",
                            "The tourist is dropping a bottle on the sand, which shows that some people still don't care.",
                            "Banning single-use plastic and putting more bins on beaches would reduce the waste over time."],
    "b7-picture-advanced": ["May and June had the most rain, and the early months had much less.",
                            "The reservoir level rises about one month after the rain, because water takes time to flow down from the hills.",
                            "From July the level falls, probably because of less rain and more water being used for farming.",
                            "I would advise the water board to store water during the monsoon months and plan for the dry season."],
    "b8-picture-advanced": ["The receptionist is answering a phone call while the display shows that number forty-seven is being served.",
                            "The elderly man needs help filling in a form, and the mother needs help calming her child.",
                            "The mother might feel tired and stressed, and the child is upset because he is unwell.",
                            "I would add a help desk for forms and an SMS system so people know when their number is near."],
}


def help_for(ex: dict, techniques: list[str] | None = None) -> dict:
    """Steps + examples + the text a 'Listen to a model' button reads, for one exercise."""
    t = ex.get("type", "")
    steps = list(STEPS.get(t, STEPS["picture"]))
    examples = list(EXAMPLES.get(ex.get("id", "")) or ex.get("examples") or [])
    if t == "sound_drill":
        examples = list(ex.get("items") or [])
    elif t == "words":
        examples = [w["text"] for w in ex.get("words") or []]
    if examples:
        model = " ".join(examples)
    elif ex.get("passage"):
        model = ex["passage"]
    elif t == "sustained_vowel":
        model = "Ahhhhhhhhhhhhhhhhhhhh."
    else:
        model = ex.get("description", "")
    return {"steps": steps, "examples": examples, "model": model, "techniques": list(techniques or [])}
