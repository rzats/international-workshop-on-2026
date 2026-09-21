"""Corpus manifest: public-domain library scans (Internet Archive) paired with
clean Project Gutenberg e-texts that serve as transcription ground truth."""

# key: (IA identifier, scan year, PG ebook id, genre tag, short label)
CORPUS = {
    "alice":       ("alicesadventwond00carrrich",  1894, (11, 12), "illustrated", "Carroll, Alice's Adventures in Wonderland"),
    "pride":       ("prideprejudice00aust",        1894, 1342, "prose",       "Austen, Pride and Prejudice"),
    "frankenstein":("frankensteinormo00shel_9",    1891, 84,   "prose",       "Shelley, Frankenstein"),
    "holmes":      ("adventuresofsher001892doyl",  1892, 1661, "illustrated", "Doyle, The Adventures of Sherlock Holmes"),
    "carol":       ("christmascarol00dickiala",    1877, 46,   "illustrated", "Dickens, A Christmas Carol"),
    "leaves":      ("leavesofgrassrhys00whitrich", 1886, 1322, "verse",       "Whitman, Leaves of Grass"),
    "timemachine": ("timemachineinven00well",      1895, 35,   "prose",       "Wells, The Time Machine"),
    "treasure":    ("islandtreasure00stevrich",    1883, 120,  "illustrated", "Stevenson, Treasure Island"),
    "jungle":      ("junglebook00kipl2",           1894, 236,  "illustrated", "Kipling, The Jungle Book"),
    "dracula":     ("draculabr00stokuoft",         1897, 345,  "prose",       "Stoker, Dracula"),
    "walden":      ("waldenorlifeinwo1854thor",    1854, 205,  "prose",       "Thoreau, Walden"),
    "tomsawyer":   ("adventuresoftoms00twaiiala",  1876, 74,   "illustrated", "Twain, The Adventures of Tom Sawyer"),
    "moby":        ("mobydickorwhale01melv",       1851, 2701, "prose",       "Melville, Moby-Dick"),
    # microform-derived scan: deliberately included as a worst-case source
    "baskerville": ("cihm_79798",                  1902, 2852, "microform",   "Doyle, The Hound of the Baskervilles (microform)"),
}
