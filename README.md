# AI Reading List

A curated, searchable list of papers, essays and journalism about AI, with a focus on science and academia.

**Read it here: https://reading.nataliebhogg.com/**

## Adding a reading

Everything lives in [`data/readings.yaml`](data/readings.yaml). Add an entry (the field guide is at the top of that file), commit, and push. A GitHub Action validates the list, builds the site and deploys it to GitHub Pages within a minute or two.

You can do this straight from the GitHub website: open the file, click the pencil icon, add your entry and commit.

Tags are free-form: `field` is the authors' field of origin, `tags` are themes, and `start_here: true` marks an essential pick. Every tag is clickable on the site.

Things not yet read go in [`data/to-read.yaml`](data/to-read.yaml) (same format). The build checks it but doesn't publish it; once read, move the entry into `readings.yaml`.

If an entry has a mistake (a missing field, a typo in a field name, a duplicate link), the build fails with a message saying which entry and why, and the live site stays as it was.

## Previewing locally

```bash
pip install -r requirements.txt
python build.py
python -m http.server -d _site    # then open http://localhost:8000
```

## What gets built

- `index.html` — the full list, rendered in the HTML so it works without JavaScript and is readable by search engines; a small script adds search, tag filtering and sorting. Filtered views are shareable links, e.g. [`?tag=labour`](https://reading.nataliebhogg.com/?tag=labour).
- `feed.xml` — an Atom feed of new additions.
- `readings.json` — the whole list as data.

## Suggestions

Know something that belongs here? [Open an issue](https://github.com/nataliehogg/ai_reading_list/issues/new).
