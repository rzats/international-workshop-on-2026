"""Search Internet Archive for public-domain scans of Project Gutenberg titles."""
import requests, json, sys, time

CANDIDATES = [
    # (key, PG id, IA search title, author surname, genre)
    ("alice",      11,   "Alice's adventures in Wonderland", "Carroll", "prose-illustrated"),
    ("pride",      1342, "Pride and prejudice",              "Austen",  "prose"),
    ("frank",      84,   "Frankenstein",                      "Shelley", "prose"),
    ("holmes",     1661, "The adventures of Sherlock Holmes", "Doyle",   "prose-illustrated"),
    ("carol",      46,   "A Christmas carol",                 "Dickens", "prose-illustrated"),
    ("leaves",     1322, "Leaves of grass",                   "Whitman", "verse"),
    ("timemachine",35,   "The time machine",                  "Wells",   "prose"),
    ("treasure",   120,  "Treasure Island",                   "Stevenson","prose-illustrated"),
    ("jungle",     236,  "The jungle book",                   "Kipling", "prose-illustrated"),
    ("dracula",    345,  "Dracula",                           "Stoker",  "prose"),
    ("rubaiyat",   246,  "Rubaiyat of Omar Khayyam",           "Fitzgerald","verse"),
    ("walden",     205,  "Walden",                            "Thoreau", "prose"),
    ("gulliver",   829,  "Gulliver's travels",                "Swift",   "prose"),
    ("baskerville",2852, "The hound of the Baskervilles",     "Doyle",   "prose"),
    ("innocence",  1934, "Songs of innocence and of experience","Blake", "verse"),
    ("moby",       2701, "Moby Dick",                         "Melville","prose"),
    ("tomsawyer",  74,   "The adventures of Tom Sawyer",      "Twain",   "prose-illustrated"),
    ("wuthering",  768,  "Wuthering heights",                 "Bronte",  "prose"),
]

def search(title, author):
    q = (f'title:("{title}") AND creator:("{author}") AND mediatype:texts '
         f'AND format:"hOCR" AND date:[1850-01-01 TO 1929-12-31]')
    r = requests.get("https://archive.org/advancedsearch.php", params={
        'q': q, 'fl[]': ['identifier', 'year', 'title', 'creator', 'downloads',
                         'collection', 'imagecount'],
        'sort[]': 'downloads desc', 'rows': 8, 'page': 1, 'output': 'json'},
        timeout=90)
    return r.json()['response']['docs']

if __name__ == '__main__':
    out = {}
    for key, pg, title, author, genre in CANDIDATES:
        try:
            docs = search(title, author)
        except Exception as e:
            print(key, 'ERR', e); continue
        print(f"--- {key} (pg{pg}, {genre}): {len(docs)} hits")
        for d in docs[:5]:
            print("   ", d.get('identifier'), d.get('year'), d.get('imagecount'),
                  d.get('downloads'), str(d.get('title'))[:60])
        out[key] = dict(pg=pg, genre=genre, docs=docs)
        time.sleep(1)
    json.dump(out, open('data/corpus/ia_search.json', 'w'), indent=1)
