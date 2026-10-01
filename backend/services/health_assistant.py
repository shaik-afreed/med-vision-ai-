"""AI Doctor: general guidance for everyday health concerns (headache, cold,
fever, stomach upset...), the way a careful family doctor would talk it through.

It is health INFORMATION, not diagnosis or treatment. Three layers:
1. Emergencies and mental-health crises always get a fixed answer, never a
   model's improvisation (see emergency_reply).
2. A system prompt for the AI model (hosted or local) that makes it ask the few
   questions a doctor would, then give causes in plain words, home care, general
   over-the-counter options WITHOUT doses, warning signs and when to see a doctor.
3. Built-in topic answers for when no AI model is reachable.
"""
import re

EMERGENCY_REPLY = (
    "Some of what you describe can be an emergency. Please get urgent medical care now: "
    "call your local emergency number or go to the nearest emergency department. Do not wait "
    "for this chat to improve things, and do not drive yourself if you feel faint or unwell. "
    "If someone is with you, ask them to stay with you.\n"
    "This tool cannot examine anyone or help in an emergency."
)

CRISIS_REPLY = (
    "I'm really sorry you are feeling this way, and I'm glad you said it. You deserve support "
    "right now.\n"
    "- If you might act on these thoughts or are in danger, call your local emergency number "
    "now, or go to the nearest emergency department.\n"
    "- You can also contact a crisis line in your country (in many places, calling or texting "
    "a local suicide and crisis lifeline is free and open all day).\n"
    "- If you can, tell someone you trust where you are and stay with them.\n"
    "You do not have to go through this alone. A doctor or counsellor can help, and these "
    "feelings can get better with support."
)

CRISIS_PATTERNS = [
    r"\bsuicid", r"\bkill myself\b", r"\bend my life\b", r"\bwant to die\b", r"\bdon'?t want to live\b",
    r"\bhurt myself\b", r"\bself[- ]?harm", r"\bharm myself\b", r"\btake my own life\b",
]

EMERGENCY_PATTERNS = [
    r"\bchest pain\b", r"\bpain in (my )?chest\b", r"\bchest (is )?(tight|pressure)",
    r"\b(can'?t|cannot|cant|unable to) breathe?\b", r"\b(trouble|difficulty|hard to|struggling to) breath",
    r"\bshort(ness)? of breath\b.*\b(rest|severe|sudden|worse)", r"\bblue (lips|face|skin)\b", r"\bbluish\b",
    r"\bunconscious\b", r"\bunresponsive\b", r"\bpass(ed)? out\b", r"\bfaint(ed|ing)\b",
    r"\bseizure", r"\bconvulsion", r"\bstroke\b", r"\bface (is )?(drooping|droop)", r"\bslurred speech\b",
    r"\bworst headache\b", r"\bthunderclap\b", r"\bsudden (weakness|numbness|vision loss|confusion)",
    r"\b(severe|heavy|uncontrolled|won'?t stop) bleeding\b", r"\bbleeding (heavily|a lot|won'?t stop)",
    r"\bvomiting blood\b", r"\bcoughing (up )?blood\b", r"\bblood in (my )?(stool|vomit)\b",
    r"\boverdose", r"\bpoison", r"\bswallowed (a )?(battery|bleach|pills)",
    r"\b(throat|tongue|face|lips) (is |are )?swell", r"\banaphyla",
    r"\bfever\b.*\b(newborn|baby (under|less than)|(one|two|1|2) month)",
]

_CRISIS = [re.compile(p) for p in CRISIS_PATTERNS]
_EMERGENCY = [re.compile(p) for p in EMERGENCY_PATTERNS]


def emergency_reply(question: str) -> str | None:
    """The fixed answer if the message describes an emergency or a crisis,
    else None. Checked before any model is called."""
    text = question.lower().replace("’", "'")
    if any(p.search(text) for p in _CRISIS):
        return CRISIS_REPLY
    if any(p.search(text) for p in _EMERGENCY):
        return EMERGENCY_REPLY
    return None


SYSTEM_PROMPT = """You are MediVision AI Doctor, a friendly general-health assistant. Talk like a careful, experienced family doctor speaking to a patient: calm, clear, kind, and practical. You are an AI, not a doctor: you cannot examine anyone, order tests, or diagnose.

How to answer an everyday health concern (headache, cold, cough, fever, sore throat, stomach upset, body ache, rash, dizziness, tiredness, sleep, stress and similar):
1. If key facts are missing, ask at most 2 or 3 short questions a doctor would ask: who it is for and their age, how long it has lasted, how severe it is, other symptoms, and any ongoing conditions, pregnancy, allergies or regular medicines. Still give useful general guidance in the same reply; do not only ask questions.
2. Say in plain words what such symptoms commonly come from (for example a viral cold, tension headache, dehydration). Make clear that this is not a diagnosis.
3. Give practical home care: rest, fluids, food, positioning, warm or cool compresses, sleep, when relevant.
4. If medicines are relevant, you may name common over-the-counter options in general terms (for example "paracetamol is commonly used for fever or pain") but NEVER give doses, amounts or schedules, and never recommend prescription drugs or antibiotics. Say to follow the product label and check with a pharmacist or doctor first, especially for children, pregnancy, older people, liver, kidney or stomach problems, allergies, or other medicines.
5. Always give clear warning signs that need urgent care, and say when to see a doctor soon (for example symptoms lasting longer than a few days, getting worse, or in a baby, an older person, a pregnant person or someone with a long-term illness).
6. End with one brief, kind line.

Safety rules:
- If the message describes an emergency (chest pain, severe breathing trouble, stroke signs, heavy bleeding, seizure, fainting, poisoning, severe allergic reaction) tell them to get emergency care immediately.
- If someone mentions self-harm or suicide, respond with warmth and urge them to contact local emergency services or a crisis line and a trusted person.
- Never tell anyone to stop or change a medicine a doctor prescribed.
- Never claim certainty. Say "can be", "often", "usually". If you are not sure, say so.
- A fever in a baby under 3 months always needs urgent medical care.
- Do not ask for or repeat a name, address or phone number.
- Answer any health question helpfully, including general wellness, nutrition, sleep and prevention. For unrelated topics, say you can help with health questions.
- Use simple language in the user's language. Plain text only, no Markdown symbols like ** or #. For a list, start lines with "- ". Keep answers focused, about 120 to 220 words unless more is needed."""


# ---------------------------------------------------------------------------
# Built-in answers (no AI model reachable)
# ---------------------------------------------------------------------------

_OTC_NOTE = (
    "Over-the-counter medicines: common ones can help, but follow the label and check with a "
    "pharmacist or doctor first, especially for children, pregnancy, older people, other "
    "medicines, allergies, or liver, kidney or stomach problems."
)

TOPICS = [
    (
        ["headache", "head ache", "head pain", "migraine", "head hurts"],
        "Headaches are very common. Most are tension-type (stress, poor sleep, long screen time, "
        "skipped meals, dehydration) or migraine.\n"
        "At home:\n"
        "- Drink water, eat something, rest in a quiet dim room.\n"
        "- A cool or warm cloth on the forehead or neck, gentle neck and shoulder stretches.\n"
        "- Cut back on screens, caffeine and alcohol, and keep regular sleep.\n"
        f"- {_OTC_NOTE}\n"
        "Get urgent care if the headache is sudden and the worst of your life, follows a head "
        "injury, comes with fever and a stiff neck, confusion, weakness, trouble speaking, vision "
        "loss, or a seizure.\n"
        "See a doctor soon if headaches are frequent, keep getting worse, wake you from sleep, or "
        "last more than a few days.\n"
        "Tell me your age, how long you have had it, and any other symptoms, and I can be more specific.",
    ),
    (
        ["fever", "fewer", "temperature", "feverish", "high temp"],
        "A fever is the body fighting an infection, most often a virus. It is the cause that "
        "matters more than the number.\n"
        "At home:\n"
        "- Rest, drink plenty of fluids, light clothing, and keep the room comfortably cool.\n"
        "- Check the temperature with a thermometer rather than by touch.\n"
        f"- {_OTC_NOTE}\n"
        "Get urgent care for: a baby under 3 months with any fever; a fever with a stiff neck, "
        "rash that does not fade when pressed, trouble breathing, confusion, a seizure, severe "
        "pain, or being very drowsy and hard to wake.\n"
        "See a doctor soon if the fever lasts more than 3 days, keeps coming back, goes above "
        "39.5 C (103 F), or the person is a young child, elderly, pregnant, or has a long-term illness.\n"
        "Tell me who it is for (age), the temperature, how long, and other symptoms.",
    ),
    (
        ["cold", "cough", "runny nose", "blocked nose", "stuffy", "sneez", "flu", "sore throat",
         "throat pain", "throat hurts", "congestion"],
        "Colds and mild flu are usually viral and get better by themselves in about 7 to 10 days.\n"
        "At home:\n"
        "- Rest and drink warm fluids; honey in warm water or tea can soothe a cough in adults and "
        "children over 1 year (never for babies under 1).\n"
        "- Steam, saline nose drops or spray for a blocked nose; salt-water gargles for a sore throat.\n"
        "- Wash hands often and cover coughs to protect others.\n"
        f"- {_OTC_NOTE}\n"
        "Antibiotics do not work on viruses and should only be taken if a doctor prescribes them.\n"
        "Get urgent care for trouble breathing, chest pain, bluish lips, or confusion.\n"
        "See a doctor if it lasts more than 10 days, a fever lasts more than 3 days, there is "
        "wheezing, ear or face pain, or you are a young child, older, pregnant, or have asthma, "
        "diabetes, or heart or lung disease.",
    ),
    (
        ["stomach", "tummy", "belly", "abdomen", "abdominal", "vomit", "nausea", "diarrhea",
         "diarrhoea", "loose motion", "loose stool", "constipation", "acidity", "indigestion",
         "heartburn", "gas"],
        "Stomach upset is often from a stomach bug, something you ate, acidity or constipation.\n"
        "At home:\n"
        "- Take small, frequent sips of water or oral rehydration solution; the main risk with "
        "vomiting or diarrhea is dehydration.\n"
        "- Start with plain foods (rice, banana, toast, soup) as you feel able; avoid fried, spicy "
        "and very sweet food, alcohol and caffeine for a few days.\n"
        "- For acidity: smaller meals, do not lie down right after eating, limit spicy food.\n"
        "- For constipation: more fibre, water and movement.\n"
        f"- {_OTC_NOTE}\n"
        "Get urgent care for severe or constant belly pain, a hard swollen belly, blood in vomit "
        "or stool, black stool, signs of dehydration (very dry mouth, no urine for 8 hours, "
        "dizziness), or high fever.\n"
        "See a doctor if it lasts more than 2 days, or for a baby, older person or pregnant person sooner.",
    ),
    (
        ["body pain", "body ache", "muscle", "back pain", "backache", "joint", "neck pain",
         "shoulder", "knee", "sprain", "leg pain", "cramp"],
        "Aches and muscle or joint pain are often from strain, poor posture, a viral illness, or overuse.\n"
        "At home:\n"
        "- Gentle movement is usually better than complete bed rest; avoid heavy lifting for a few days.\n"
        "- Cold pack for the first 1 to 2 days after a strain, then warmth; stretch gently.\n"
        "- Check your posture, sleep position and chair.\n"
        f"- {_OTC_NOTE}\n"
        "Get urgent care for pain after a serious fall or accident, numbness or weakness in the legs, "
        "loss of bladder or bowel control, or chest pain.\n"
        "See a doctor if the pain lasts more than 1 to 2 weeks, keeps getting worse, wakes you at "
        "night, or comes with fever or unexplained weight loss.",
    ),
    (
        ["rash", "itch", "allergy", "allergic", "hives", "skin", "pimple", "acne", "eczema"],
        "Rashes and itching often come from allergies, irritation, heat, eczema, or a viral infection.\n"
        "At home:\n"
        "- Stop using any new soap, cream, detergent or food you suspect; avoid scratching.\n"
        "- Cool compresses, loose cotton clothing, and a gentle fragrance-free moisturiser.\n"
        f"- {_OTC_NOTE}\n"
        "Get urgent care if there is swelling of the face, lips, tongue or throat, trouble "
        "breathing, or dizziness after a sting, food or medicine.\n"
        "See a doctor if the rash is spreading fast, blistering, painful, has pus, comes with "
        "fever, or does not improve in a few days.",
    ),
    (
        ["dizzy", "dizziness", "lightheaded", "light headed", "vertigo", "tired", "tiredness",
         "fatigue", "weak", "weakness", "low energy"],
        "Dizziness and tiredness are common and often come from dehydration, missed meals, poor "
        "sleep, standing up too quickly, stress, a viral illness, or low iron.\n"
        "At home:\n"
        "- Sit or lie down, drink water, and eat something; stand up slowly.\n"
        "- Aim for regular meals, 7 to 9 hours of sleep, and light daily activity.\n"
        "Get urgent care for fainting, chest pain, a racing or irregular heartbeat, weakness on "
        "one side, trouble speaking, severe headache, or sudden vision change.\n"
        "See a doctor if it keeps coming back, lasts more than a week or two, or comes with weight "
        "loss, pale skin, shortness of breath, or heavy periods.",
    ),
    (
        ["sleep", "insomnia", "can't sleep", "cant sleep", "stress", "anxiety", "anxious", "worried",
         "panic", "low mood", "sad", "depressed", "overthinking"],
        "Poor sleep, stress and worry affect almost everyone at times, and they are treatable.\n"
        "What helps:\n"
        "- Keep fixed sleep and wake times, avoid screens and caffeine in the evening, keep the room dark and cool.\n"
        "- Daily movement, daylight, regular meals, and slow breathing (in for 4 counts, out for 6) for a few minutes.\n"
        "- Talk to someone you trust; write down worries earlier in the day.\n"
        "See a doctor or counsellor if this lasts more than 2 weeks, affects work or relationships, "
        "or comes with panic attacks or a very low mood. If you ever have thoughts of harming "
        "yourself, contact local emergency services or a crisis line right away.",
    ),
    (
        ["toothache", "tooth", "gum", "dental", "mouth ulcer", "ear pain", "earache", "eye", "red eye"],
        "Pain in a tooth, gum, ear or eye needs a proper look, but you can ease it meanwhile.\n"
        "- Tooth or gum: rinse with warm salt water, avoid very hot, cold or sweet food, and see a dentist soon.\n"
        "- Ear: a warm cloth over the ear can soothe; do not put anything into the ear.\n"
        "- Eye: wash hands, do not rub, remove contact lenses, and rinse with clean water.\n"
        f"- {_OTC_NOTE}\n"
        "Get urgent care for facial swelling that makes it hard to swallow or breathe, a high "
        "fever with a swollen face, sudden vision loss, a chemical in the eye, or an eye injury.\n"
        "See a doctor or dentist if it lasts more than 1 to 2 days.",
    ),
]

GREETING_REPLY = (
    "Hello! I'm the MediVision AI Doctor. I can talk through everyday health concerns such as "
    "headache, cold and cough, fever, stomach upset, body aches, rashes, dizziness, sleep and "
    "stress: what it commonly is, what you can do at home, and when to see a doctor.\n"
    "Tell me what is bothering you, who it is for (age), and how long it has lasted."
)

DEFAULT_REPLY = (
    "I can help best with everyday health concerns. Tell me the symptom, who it is for (age), "
    "how long it has lasted, and any other symptoms. For example: headache, cold and cough, "
    "fever, stomach upset, body aches, a rash, dizziness, sleep or stress.\n"
    "I'm running without the AI model right now, so I can only answer these common topics. "
    "For anything else, please see a doctor.\n"
    "If you ever feel very unwell, get urgent medical care."
)

_GREETING = re.compile(r"^\W*(hi|hello|hey|hii+|good (morning|afternoon|evening)|help)\b")


def builtin_reply(question: str) -> str:
    text = question.lower()

    # Up to two matching topics ("headache and fever"), in the order listed.
    matches = [
        answer for keywords, answer in TOPICS
        if any(re.search(r"\b" + re.escape(k), text) for k in keywords)
    ]
    if matches:
        return "\n\n".join(matches[:2])

    if _GREETING.search(text):
        return GREETING_REPLY

    return DEFAULT_REPLY
