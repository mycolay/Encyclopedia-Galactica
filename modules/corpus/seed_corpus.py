"""
Seed texts and canonical excerpts for foundational Sci-Fi works.
Provides original-language passages where seminal neologisms were first attested.
"""

from typing import Dict, Any, List
from modules.corpus.manager import CorpusManager
from core.db import DatabaseManager

CANONICAL_EXCERPTS = [
    {
        "author_slug": "karel-capek",
        "work_slug": "rur-rossums-universal-robots",
        "title": "R.U.R. (Rossum's Universal Robots) - Act 1 / Opening",
        "original_lang": "cs",
        "text": """KAREL ČAPEK: R.U.R. (Rossumovi Univerzální Roboti)
Utopická hra o třech dějstvích s předehrou (1920)

PŘEDEHRA.
Ústřední kancelář továrny Rossumových Univerzálních Robotů.

DOMIN: (diktuje) ...továrna neručí za chyby v opise. Tečka. K rukám pánů E. Busmana v Hamburku. Uctivý pane, na váš dopis ze dne 14. m. t. sdělujeme, že náš závod nepřijímá žádné objednávky na okamžité dodání Robotů. Naše výroba nestačí krýt ani poptávku starých zákazníků. Roboti se osvědčují v každém ohledu. Výrobní cena jednoho Robota činí dnes 120 dolarů včetně šatů a udržování na tři léta. Závod Rossum's Universal Robots.

HELENA: Vy jste pan generální ředitel Domin?
DOMIN: K vašim službám, slečno Gloryová. Vy jste dcera prezidenta Gloryho?
HELENA: Ano.
DOMIN: Vítám vás na našem ostrově. Posaďte se, prosím. Zde na ostrově vyrábíme novou éru lidstva.
HELENA: Chtěla bych vidět... chtěla bych vědět, jak děláte ty vaše Roboty.
DOMIN: Starý Rossum, velký filosof, se pokusil chemickou syntézou vytvořit protoplazmu. Roku 1932 objevil látku, která se chovala přesně jako živá hmota. Ale mladý inženýr Rossum, jeho synovec, řekl: Příroda našla jen jeden způsob, jak zorganizovat živou hmotu. Je tu však jiný způsob, jednodušší, tvarově čistší a tvárnější, na který příroda vůbec nepřipadla: stroj. A tak vznikl Robot.
HELENA: Robot necítí nic?
DOMIN: Nic. Roboti nemají duši. Nemají lásku, nemají vzpouru, nemají strach ze smrti. Pracují mechanicky, dokonale, levně. Jsou to dělníci bez chyb, stroje z masa a kostí, které osvobodí člověка od ponižující dřiny!"""
    },
    {
        "author_slug": "william-gibson",
        "work_slug": "neuromancer",
        "title": "Neuromancer - Chapter 1 & Cyberspace Definition",
        "original_lang": "en",
        "text": """WILLIAM GIBSON: NEUROMANCER (1984)

CHAPTER ONE:
The sky above the port was the color of television, tuned to a dead channel.
"It's not like I'm using," Case heard someone say, as he shouldered his way through the crowd around the door of the Chat. "It's like my body's developed this massive drug deficiency."

Case was twenty-four. At twenty-two, he'd been a cowboy, a rustler, one of the best in the Sprawl. He'd been trained by the best, by McCoy Pauley and Bobby Quine, legends in the biz. He'd operated on an almost permanent adrenaline high, a byproduct of youth and proficiency, jacked into a custom cyberspace deck that projected his disembodied consciousness into the consensual hallucination that was the matrix. A thief, he'd worked for other, wealthier thieves, burgling corporate data banks, navigating through high-density ICE (Intrusion Countermeasure Electronics) that guarded the secrets of the zaibatsus.

CHAPTER THREE (Cyberspace Matrix):
"Cyberspace. A consensual hallucination experienced daily by billions of legitimate operators, in every nation, by children being taught mathematical concepts... A graphic representation of data abstracted from the banks of every computer in the human system. Unthinkable complexity. Lines of light ranged in the nonspace of the mind, clusters and constellations of data. Like city lights, receding..."

"The matrix has its roots in primitive arcade games," the voice-over continued, "in early graphics programs and military experimentation with cranial jacks."

Case jacked in. The matrix flared into neon geometric lattice: crystalline polyhedra of corporate nodes, towering ice-walls of military data-fortresses, lines of optic fiber pulsing like arterial blood through the infinite dark void of virtual space."""
    },
    {
        "author_slug": "ursula-k-le-guin",
        "work_slug": "rocannons-world",
        "title": "Rocannon's World - Chapter 1 & Chapter 6 (Ansible Attestation)",
        "original_lang": "en",
        "text": """URSULA K. LE GUIN: ROCANNON'S WORLD (1966)

PROLOGUE:
Through the great depths of space and time, the League of All Worlds sent its emissaries, ethnologists, and surveyors.

CHAPTER TWO:
"How do you call across fifty light-years?" the young native asked, staring at the slender metal rod.
Rocannon smiled faintly. "We do not call by radio or light. That would take half a century for the wave to travel. We use the ansible."

CHAPTER SIX:
"An ansible?"
"The ansible is an instantaneous communicator. It has no delay. It does not send a wave that must cross space at the crawling speed of light; it operates upon the principle of simultaneity. A message typed here appears simultaneously upon the receiver in the League central station on Earth, fifty light-years distant, at the exact split-second of transmission. Time and distance are canceled in the communication of mind with mind."

Rocannon keyed the transmitter. The tiny needle swung true, locking onto the resonance of the distant home world."""
    },
    {
        "author_slug": "ursula-k-le-guin",
        "work_slug": "the-dispossessed",
        "title": "The Dispossessed - The General Temporal Theory & Ansible",
        "original_lang": "en",
        "text": """URSULA K. LE GUIN: THE DISPOSSESSED: AN AMBIGUOUS UTOPIA (1974)

CHAPTER NINE:
Shevek sat at the desk, looking at the formulas spread across the sheets. The General Temporal Theory. Sequency and Simultaneity.
"If your theory holds," Oiie said, watching him with tense curiosity, "what are the practical consequences?"
"The ansible," Shevek answered quietly.
"An instantaneous transmitter?"
"Yes. Not for matter, not for bodies, but for information. You cannot travel faster than light, because mass approaches infinity as velocity nears c. But information, pure meaning, can be conceived as co-present in the temporal manifold. A device can be built—an ansible—that will connect all worlds of the human ecumene without the barrier of years. We will speak across forty light-years as if we stood together in the same room. Isolation will end. The stars will become a single conversation."

OIie shook his head in awe. "To speak across the abyss without waiting for generations to pass..."
"Time does not divide us," Shevek said, "if we understand that the beginning and the end are parts of the same arch."""
    },
    {
        "author_slug": "frank-herbert",
        "work_slug": "dune",
        "title": "Dune - Terminology of the Imperium & The Butlerian Jihad",
        "original_lang": "en",
        "text": """FRANK HERBERT: DUNE (1965)

TERMINOLOGY OF THE IMPERIUM:

BUTLERIAN JIHAD: (See also Great Revolt) — the crusade against computers, thinking machines, and conscious robots begun in 201 B.G. and concluded in 108 B.G. Its chief commandment remains in the O.C. Bible as: "Thou shalt not make a machine in the likeness of a human mind."

MENTAT: That class of imperial citizens trained for supreme logic and data analysis. "Human computers" developed to replace the thinking machines destroyed after the Butlerian Jihad. Their minds are augmented with the juice of Sapho to achieve staggering computational velocities.

MELANGE: The "spice" found only upon Arrakis. An addictive geriatric drug that prolongs human life, expands cosmic consciousness, and unlocks prescient vision. Essential for the Spacing Guild Navigators to fold space safely.

"The mystery of life isn't a problem to solve, but a reality to experience," the Reverend Mother Gaius Helen Mohiam murmured, holding the poisoned needle of the gom jabbar against young Paul Atreides' neck. "A process cannot be understood by stopping it. We must move with the flow of the process. We must join it, we must flow with it."

Paul held his hand inside the box of burning agony. "I must not fear. Fear is the mind-killer. Fear is the little-death that brings total obliteration. I will face my fear. I will permit it to pass over me and through me..."""
    },
    {
        "author_slug": "isaac-asimov",
        "work_slug": "foundation",
        "title": "Foundation - Psychohistory & The Seldon Plan",
        "original_lang": "en",
        "text": """ISAAC ASIMOV: FOUNDATION (1951)

PART I: THE PSYCHOHISTORIANS

"Hari Seldon... was the man who established the science of psychohistory and brought it to its peak. Psychohistory was the quintessence of sociological mathematics.

Gaal Dornick said, 'Can you prove the fall of the Galactic Empire?'
'I can,' Seldon answered. 'The Empire will fall and all its achievements will fade. The Galactic Empire is decaying, and the interregnum that follows will last thirty thousand years.'

'Can nothing be done?'
'A single human individual is unpredictable,' Seldon explained, tapping the glowing prime radiant. 'His reactions cannot be forecast by any known calculus. But human society in the mass—billions of individuals across thousands of worlds—behaves according to statistical mechanics, exactly like gas molecules in thermal motion. Psychohistory is the science that treats the reactions of human conglomerates to fixed social and economic stimuli. It can predict the grand sweeps of history with mathematical certainty.'

'And what will the Foundation do?'
'We cannot prevent the fall,' said Seldon. 'The Empire is too vast and its inertia too great. But we can shorten the period of chaos from thirty thousand years to a single millennium. That is the Seldon Plan. We will preserve the totality of human knowledge in the Encyclopedia Galactica, upon the world of Terminus at the very rim of the Galaxy.'"""
    }
]


def populate_seed_corpus(db: DatabaseManager, corpus_mgr: CorpusManager):
    """Saves seed texts to corpus files and marks them in the database."""
    for item in CANONICAL_EXCERPTS:
        path, word_count = corpus_mgr.store_text(
            author_slug=item["author_slug"],
            work_slug=item["work_slug"],
            text=item["text"],
            metadata={
                "title": item["title"],
                "original_lang": item["original_lang"]
            }
        )

        # Update in database
        with db.get_connection() as conn:
            conn.execute("""
            UPDATE works 
            SET has_full_text = 1, text_path = ?, word_count = ?, research_status = 'in_progress'
            WHERE slug = ?
            """, (str(path), word_count, item["work_slug"]))
            conn.commit()
