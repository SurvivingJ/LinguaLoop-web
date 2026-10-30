import csv,glob
ex={r['lemma'] for r in csv.DictReader(open('existing_ja_senses.csv'))}
c=[l.split('\t')[0] for f in sorted(glob.glob('candidates/*.tsv')) for l in open(f) if l.strip()]
c=[x for x in c if not (x.endswith('する') and x[:-2] in ex|set(c))]
new=[x for x in dict.fromkeys(c) if x not in ex];print(len(c),len(new))
