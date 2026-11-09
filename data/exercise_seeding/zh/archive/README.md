# zh fat-seed records

JSON records of every run: `wf2/` (first pass: author documents, Haiku review records and reviewed documents) and
`wf3/` (Opus/low second review: review records and reviewed documents), plus each run's `senses.csv`.
The archive is split into parts under 50 MB. Rejoin and extract with:

```bash
cat zh_fatseed_records.tar.gz.part_* > zh_fatseed_records.tar.gz
tar -xzf zh_fatseed_records.tar.gz
```
