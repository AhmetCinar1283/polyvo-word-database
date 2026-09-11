"""
Kademe 0 — ELLE TOHUM katalog (~65 kural, A1-B1 agirlikli).

Bu dosya LLM URUNU DEGILDIR: model kural id'si UYDURAMAZ, yalnizca burada
listelenenden secer. Katalog buyudukce (Kademe 1 adaylarindan) buraya ELLE
satir eklenir; hicbir satir SILINMEZ, birlestirme `merged_into` ile yapilir.

`trivial=True` satirlar HER cumlede vardir ve `rank=1`de asla gorunmez
(kopula, tanimlik, cogul -s gibi) — bunlar cumle hakkinda bilgi tasimaz.
"""

from __future__ import annotations

from polyvo.modules.grammar.catalog.model import GrammarRule

#: id -> GrammarRule, id'ye gore ARANABILIR olsun diye sozluk.
RULES: dict[str, GrammarRule] = {
    rule.id: rule for rule in (
        # -- TENSE ----------------------------------------------------
        GrammarRule("EN.TENSE.BE_PRESENT_FORMS",
                    "Present tense of 'be' (am/is/are)",
                    "The verb 'be' changes form with the subject in the "
                    "present tense: I am, you/we/they are, he/she/it is.",
                    level="A1", assume_known_from="A1", trivial=True),
        GrammarRule("EN.TENSE.PRESENT_SIMPLE_3SG",
                    "Third-person -s in the present simple",
                    "A present-simple verb takes -s/-es when the subject is "
                    "he/she/it or a singular noun.",
                    level="A1", assume_known_from="A1", trivial=True),
        GrammarRule("EN.TENSE.PRESENT_SIMPLE", "Present simple",
                    "Used for habits, facts and routines.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.TENSE.PRESENT_CONTINUOUS", "Present continuous",
                    "Used for an action happening right now or around now.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.TENSE.PAST_SIMPLE", "Past simple",
                    "Used for a completed action at a specific past time.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.TENSE.PAST_CONTINUOUS", "Past continuous",
                    "Used for an action in progress at a moment in the "
                    "past, often interrupted by another action.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.TENSE.PRESENT_PERFECT", "Present perfect",
                    "Links a past action or state to the present moment "
                    "(has/have + past participle).",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.TENSE.PRESENT_PERFECT_CONTINUOUS",
                    "Present perfect continuous",
                    "Emphasizes the duration of an action that started in "
                    "the past and continues (has/have been + -ing).",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.TENSE.PAST_PERFECT", "Past perfect",
                    "Marks an action that happened before another past "
                    "action (had + past participle).",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.TENSE.FUTURE_WILL", "Future with 'will'",
                    "Used for predictions, spontaneous decisions and "
                    "promises about the future.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.TENSE.FUTURE_GOING_TO", "Future with 'going to'",
                    "Used for plans and intentions decided before the "
                    "moment of speaking.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.TENSE.PRESENT_FOR_FUTURE",
                    "Present continuous for a fixed future arrangement",
                    "The present continuous can describe a scheduled future "
                    "event, not only the present moment.",
                    level="A2", assume_known_from="B1"),

        # -- ASPECT -----------------------------------------------------
        GrammarRule("EN.ASPECT.STATIVE_VERB_NO_CONTINUOUS",
                    "Stative verbs avoid the continuous form",
                    "Verbs of state (know, want, believe, own) are not "
                    "normally used in the -ing form.",
                    level="A2", assume_known_from="B1"),

        # -- MODAL --------------------------------------------------------
        GrammarRule("EN.MODAL.CAN_ABILITY", "'Can' for ability",
                    "'Can' expresses present ability or possibility.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.MODAL.BE_ABLE_TO", "'Be able to' for ability",
                    "'Be able to' expresses ability, and is the only option "
                    "where 'can' has no form (e.g. after 'to', in the "
                    "future or perfect).",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.MODAL.MUST_OBLIGATION", "'Must' for obligation",
                    "'Must' expresses strong obligation, often from the "
                    "speaker's own judgement.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.MODAL.HAVE_TO_OBLIGATION", "'Have to' for obligation",
                    "'Have to' expresses obligation that comes from an "
                    "outside rule or authority.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.MODAL.SHOULD_ADVICE", "'Should' for advice",
                    "'Should' gives advice or a recommendation.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.MODAL.MIGHT_POSSIBILITY", "'Might/may' for possibility",
                    "'Might' or 'may' expresses that something is possible "
                    "but not certain.",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.MODAL.WOULD_HYPOTHETICAL",
                    "'Would' for hypothetical situations",
                    "'Would' expresses what happens in an imagined or "
                    "unreal situation.",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.MODAL.MUST_HAVE_DEDUCTION",
                    "'Must have' for a past deduction",
                    "'Must have + past participle' expresses a confident "
                    "guess about the past.",
                    level="B1", assume_known_from="B2"),

        # -- VOICE --------------------------------------------------------
        GrammarRule("EN.VOICE.PASSIVE_PRESENT", "Present passive",
                    "'Is/are + past participle' shifts focus from the doer "
                    "of the action to the thing acted upon.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.VOICE.PASSIVE_PAST", "Past passive",
                    "'Was/were + past participle' — the past-tense form of "
                    "the passive voice.",
                    level="A2", assume_known_from="B1"),

        # -- INF (mastar) ---------------------------------------------------
        GrammarRule("EN.INF.TO_INFINITIVE", "To-infinitive",
                    "'To' + base verb, used after many verbs and "
                    "adjectives to express purpose or a following action.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.INF.VERB_PLUS_INFINITIVE",
                    "Verb followed by a to-infinitive",
                    "Certain verbs (want, decide, hope, need) are always "
                    "followed by 'to' + base verb, never by -ing.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.INF.BARE_INFINITIVE_AFTER_MODAL",
                    "Bare infinitive after a modal verb",
                    "A modal verb (can, must, should) is followed by the "
                    "base form of the verb, with no 'to'.",
                    level="A1", assume_known_from="A2"),

        # -- GER (ulac/-ing isim) --------------------------------------------
        GrammarRule("EN.GER.VERB_PLUS_GERUND",
                    "Verb followed by a gerund",
                    "Certain verbs (enjoy, avoid, finish, suggest) are "
                    "always followed by the -ing form, never by 'to'.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.GER.PREP_PLUS_GERUND",
                    "Preposition followed by a gerund",
                    "A verb after a preposition takes the -ing form, not "
                    "the infinitive.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.GER.SUBJECT_GERUND",
                    "Gerund as the subject of a sentence",
                    "An -ing form can act as the subject of a sentence, "
                    "functioning like a noun.",
                    level="B1", assume_known_from="B2"),

        # -- PART (ortac) -----------------------------------------------------
        GrammarRule("EN.PART.PAST_PARTICIPLE_ADJECTIVE",
                    "Past participle used as an adjective",
                    "A past participle (bored, interested, excited) "
                    "describes how someone FEELS.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.PART.PRESENT_PARTICIPLE_ADJECTIVE",
                    "Present participle used as an adjective",
                    "A present participle (boring, interesting, exciting) "
                    "describes what CAUSES the feeling.",
                    level="A2", assume_known_from="B1"),

        # -- COND (kosul) -----------------------------------------------------
        GrammarRule("EN.COND.ZERO_CONDITIONAL", "Zero conditional",
                    "'If + present, present' expresses a general truth "
                    "or fact that is always true.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.COND.FIRST_CONDITIONAL", "First conditional",
                    "'If + present, will + base verb' expresses a real, "
                    "likely future result.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.COND.SECOND_CONDITIONAL", "Second conditional",
                    "'If + past simple, would + base verb' expresses an "
                    "unreal or unlikely present/future situation.",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.COND.THIRD_CONDITIONAL", "Third conditional",
                    "'If + past perfect, would have + past participle' "
                    "expresses an unreal past situation and its result.",
                    level="B1", assume_known_from="B2"),

        # -- CLAUSE -------------------------------------------------------
        GrammarRule("EN.CLAUSE.TIME_CLAUSE_WHEN",
                    "Time clause with 'when'",
                    "'When' introduces a clause that tells the time an "
                    "action happens, and never takes 'will' in that clause.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.CLAUSE.REASON_BECAUSE",
                    "Reason clause with 'because'",
                    "'Because' introduces a clause that gives the reason "
                    "for the main clause.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.CLAUSE.CONTRAST_ALTHOUGH",
                    "Contrast clause with 'although'",
                    "'Although' introduces a clause that contrasts with "
                    "the main clause.",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.CLAUSE.REPORTED_SPEECH",
                    "Reported (indirect) speech",
                    "Reporting what someone said shifts the tense one step "
                    "back and changes pronouns/time words.",
                    level="B1", assume_known_from="B2"),

        # -- REL (ilgi cumlesi) -----------------------------------------------
        GrammarRule("EN.REL.DEFINING_WHO_WHICH",
                    "Defining relative clause with who/which/that",
                    "A defining relative clause identifies WHICH person or "
                    "thing is meant, using who, which or that.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.REL.OMITTED_OBJECT_PRONOUN",
                    "Omitted object relative pronoun",
                    "The relative pronoun can be dropped when it is the "
                    "object of the relative clause.",
                    level="B1", assume_known_from="B2"),

        # -- QUES (soru) --------------------------------------------------
        GrammarRule("EN.QUES.YES_NO_AUXILIARY_INVERSION",
                    "Yes/no question with auxiliary inversion",
                    "A yes/no question moves the auxiliary verb (do/does/"
                    "is/have) before the subject.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.QUES.WH_QUESTION", "Wh-question word order",
                    "A wh-question starts with a question word, followed "
                    "by the auxiliary and then the subject.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.QUES.TAG_QUESTION", "Question tag",
                    "A short tag (isn't it?, don't you?) is added to a "
                    "statement to check or confirm it.",
                    level="B1", assume_known_from="B2"),

        # -- NEG (olumsuzluk) -------------------------------------------------
        GrammarRule("EN.NEG.DO_SUPPORT", "'Do'-support in negation",
                    "A present/past simple verb needs 'do/does/did + not' "
                    "to form the negative, except for 'be' and modals.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.NEG.DOUBLE_NEGATIVE_AVOIDED",
                    "No double negatives",
                    "English uses only ONE negative word per clause "
                    "(never 'not... no...' together).",
                    level="A2", assume_known_from="B1"),

        # -- ART (tanimlik) ---------------------------------------------------
        GrammarRule("EN.ART.A_AN", "Indefinite article a/an",
                    "'A' or 'an' introduces a singular countable noun "
                    "mentioned for the first time.",
                    level="A1", assume_known_from="A1", trivial=True),
        GrammarRule("EN.ART.THE_DEFINITE",
                    "Definite article 'the'",
                    "'The' refers to a specific thing already known to "
                    "speaker and listener.",
                    level="A1", assume_known_from="A1", trivial=True),
        GrammarRule("EN.ART.ZERO_ARTICLE_PLURAL_GENERAL",
                    "Zero article for general plural/uncountable nouns",
                    "No article is used before a plural or uncountable "
                    "noun when speaking generally.",
                    level="A2", assume_known_from="B1"),

        # -- NOUN -----------------------------------------------------------
        GrammarRule("EN.NOUN.PLURAL_S", "Regular plural -s",
                    "A regular plural noun is formed by adding -s or -es.",
                    level="A1", assume_known_from="A1", trivial=True),
        GrammarRule("EN.NOUN.IRREGULAR_PLURAL", "Irregular plural noun",
                    "Some nouns (child/children, person/people) form the "
                    "plural in an irregular way.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.NOUN.COUNTABLE_UNCOUNTABLE",
                    "Countable vs. uncountable noun",
                    "An uncountable noun (money, information) has no "
                    "plural form and takes singular agreement.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.NOUN.POSSESSIVE_S", "Possessive 's",
                    "'-'s' attaches to a noun to show possession "
                    "(the dog's toy).",
                    level="A1", assume_known_from="A2"),

        # -- PRON -----------------------------------------------------------
        GrammarRule("EN.PRON.PERSONAL_SUBJECT",
                    "Personal subject pronoun",
                    "A subject pronoun (I, you, he, she, it, we, they) "
                    "replaces the subject noun.",
                    level="A1", assume_known_from="A1", trivial=True),
        GrammarRule("EN.PRON.REFLEXIVE", "Reflexive pronoun",
                    "A reflexive pronoun (myself, himself, themselves) is "
                    "used when the subject and object are the same person.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.PRON.POSSESSIVE", "Possessive pronoun",
                    "A possessive pronoun (mine, yours, his, hers) stands "
                    "alone in place of a possessive noun phrase.",
                    level="A2", assume_known_from="B1"),

        # -- ADJ ------------------------------------------------------------
        GrammarRule("EN.ADJ.ORDER_BEFORE_NOUN",
                    "Adjective order before a noun",
                    "Multiple adjectives before a noun follow a fixed "
                    "order (opinion, size, age, shape, color, origin, "
                    "material).",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.ADJ.PARTICIPLE_VS_PLAIN",
                    "Participial adjective vs. plain adjective",
                    "A participial adjective (-ed/-ing) is chosen based on "
                    "whether the noun feels or causes the quality.",
                    level="A2", assume_known_from="B1"),

        # -- ADV ------------------------------------------------------------
        GrammarRule("EN.ADV.FLAT_ADVERB", "Flat (irregular) adverb",
                    "A few adverbs (fast, hard, high, late) keep the same "
                    "form as the adjective, with no -ly ending.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.ADV.MANNER_LY", "Manner adverb with -ly",
                    "Most manner adverbs are formed by adding -ly to the "
                    "adjective (careful -> carefully).",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.ADV.FREQUENCY_MID_POSITION",
                    "Mid-position frequency adverb",
                    "A frequency adverb (always, often, never) goes before "
                    "the main verb but after 'be'.",
                    level="A2", assume_known_from="B1"),

        # -- COMP (karsilastirma) ---------------------------------------------
        GrammarRule("EN.COMP.COMPARATIVE_ER",
                    "Comparative with -er/more",
                    "A short adjective adds -er, a long adjective uses "
                    "'more', to compare two things.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.COMP.SUPERLATIVE_EST",
                    "Superlative with -est/most",
                    "A short adjective adds -est, a long adjective uses "
                    "'most', to mark the extreme of a group.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.COMP.AS_AS", "'As...as' equal comparison",
                    "'As + adjective + as' expresses that two things are "
                    "equal in some quality.",
                    level="A2", assume_known_from="B1"),

        # -- PREP -----------------------------------------------------------
        GrammarRule("EN.PREP.TIME_AT_IN_ON",
                    "Time preposition at/in/on",
                    "'At' a precise time, 'in' a longer period, 'on' a day "
                    "or date.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.PREP.PLACE_AT_IN_ON",
                    "Place preposition at/in/on",
                    "'At' a point, 'in' an enclosed space, 'on' a surface.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.PREP.DEPENDENT_ADJECTIVE",
                    "Preposition dependent on an adjective",
                    "Certain adjectives are always followed by one fixed "
                    "preposition (afraid OF, good AT, interested IN).",
                    level="A2", assume_known_from="B1"),

        # -- CONJ -----------------------------------------------------------
        GrammarRule("EN.CONJ.COORDINATING_FANBOYS",
                    "Coordinating conjunction",
                    "'And, but, or, so' join two independent clauses or "
                    "equal items.",
                    level="A1", assume_known_from="A2"),

        # -- QUANT ----------------------------------------------------------
        GrammarRule("EN.QUANT.MUCH_MANY", "'Much' vs. 'many'",
                    "'Many' quantifies countable nouns, 'much' quantifies "
                    "uncountable nouns.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.QUANT.SOME_ANY", "'Some' vs. 'any'",
                    "'Some' is used in affirmative sentences, 'any' in "
                    "negatives and questions.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.QUANT.A_FEW_A_LITTLE",
                    "'A few' vs. 'a little'",
                    "'A few' quantifies countable nouns, 'a little' "
                    "quantifies uncountable nouns, both meaning a small "
                    "amount.",
                    level="A2", assume_known_from="B1"),

        # -- ORDER (sozdizimi) -------------------------------------------------
        GrammarRule("EN.ORDER.SVO", "Basic subject-verb-object order",
                    "A statement follows subject, then verb, then object.",
                    level="A1", assume_known_from="A1", trivial=True),
        GrammarRule("EN.ORDER.INDIRECT_DIRECT_OBJECT",
                    "Indirect before direct object",
                    "With verbs like 'give' or 'send', the indirect object "
                    "(person) can come before the direct object (thing), "
                    "with no preposition.",
                    level="A2", assume_known_from="B1"),

        # -- PHRASAL (obek fiil) -----------------------------------------------
        GrammarRule("EN.PHRASAL.GIVE_UP", "Phrasal verb 'give up'",
                    "'Give up' means to stop trying or to quit something.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.PHRASAL.LOOK_FOR", "Phrasal verb 'look for'",
                    "'Look for' means to search for something.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.PHRASAL.TURN_ON_OFF", "Phrasal verb 'turn on/off'",
                    "'Turn on/off' means to start/stop a device or "
                    "supply, and can split around a pronoun object.",
                    level="A1", assume_known_from="A2"),
        GrammarRule("EN.PHRASAL.PUT_UP_WITH", "Phrasal verb 'put up with'",
                    "'Put up with' means to tolerate something unpleasant "
                    "without complaining.",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.PHRASAL.RUN_OUT_OF", "Phrasal verb 'run out of'",
                    "'Run out of' means to have no more of something left.",
                    level="A2", assume_known_from="B1"),

        # -- COLLOC ---------------------------------------------------------
        GrammarRule("EN.COLLOC.MAKE_VS_DO",
                    "Fixed collocation with 'make' vs. 'do'",
                    "'Make' and 'do' pair with fixed sets of nouns "
                    "(make a decision, do homework) that do not follow a "
                    "predictable rule.",
                    level="A2", assume_known_from="B1"),
        GrammarRule("EN.COLLOC.TAKE_A_BREAK",
                    "Fixed collocation 'take a break'",
                    "'Take' pairs with certain fixed nouns (a break, a "
                    "look, a seat) as a set phrase.",
                    level="A2", assume_known_from="B1"),

        # -- DISC (soylem) ------------------------------------------------
        GrammarRule("EN.DISC.LINKING_HOWEVER",
                    "Discourse linker 'however'",
                    "'However' signals a contrast with the previous "
                    "sentence, usually followed by a comma.",
                    level="B1", assume_known_from="B2"),
        GrammarRule("EN.DISC.LINKING_THEREFORE",
                    "Discourse linker 'therefore'",
                    "'Therefore' signals a result or conclusion drawn from "
                    "the previous sentence.",
                    level="B1", assume_known_from="B2"),
    )
}


def all_rules() -> tuple[GrammarRule, ...]:
    """Katalogdaki HER kural, id sirasinda (deterministik)."""
    return tuple(RULES[key] for key in sorted(RULES))
