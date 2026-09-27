# Adjudication instructions (given verbatim to every labeller)

You are an independent adjudicator. You will read ONE packet file. Do not open, list or read any
other file in `data/eval/entailment_adjudication_2026-09-27/` (or anywhere else); use only your packet.
You do not know, and must not try to find out, who or what wrote the candidates.

For every question (`## Q###`) and every candidate letter, decide whether the candidate is a correct
answer to the question, using ONLY the passage:

- `yes`     the passage states this answer explicitly, OR it is the uniquely inferable / correct answer.
            For "what does X mean in the passage" questions: yes if the candidate correctly conveys the
            meaning of X as used in the passage (a reasonable paraphrase counts).
- `no`      the passage does not support it: merely on the same topic, unsupported, contradicted, wrong
            meaning, or the question cannot be answered from the passage at all (e.g. it asks about a
            phrase the passage never uses).
- `unclear` genuinely partial or arguable — a careful native reader could go either way. Use sparingly:
            prefer yes/no whenever a careful native reader would commit.

Judge each candidate INDEPENDENTLY. Several candidates may be `yes`; there may be none.
Do not reward a candidate for being the "best of the four" — reward it only if it is correct.

Output: write a JSON file (with the Write tool) to the path you are given, exactly:
{"questions": {"Q012": {"A": {"label": "yes", "reason": "<=20 words"}, "B": {...}}, "Q013": {...}}}
Include EVERY question and EVERY candidate letter in the packet. Then reply with one line:
"done <n questions> <m candidates>".
