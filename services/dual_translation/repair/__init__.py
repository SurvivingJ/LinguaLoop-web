"""Guided self-repair for Dual Translation (wiki/features/dt-guided-self-repair.tech.md).

After a single-call grade, each flagged sentence becomes one step: the learner
fixes their own sentence with a hint ladder (where -> kind -> clue -> answer), and
each revision is re-checked by one call of the single-call grader on that sentence
only. Unresolved items return in daily practice.

Modules (tech section 3): ``settings`` (env-read knobs), ``hints`` (templates +
leak filter), ``sentences`` (sentence model), ``planner`` (eligibility + steps),
``recheck`` (the only model boundary), ``classify`` (fixed / no_issue_found /
still_flagged), ``scheduling`` (daily-practice rules), ``budget`` (cost caps),
``store`` (every DB read/write), ``service`` (orchestration) and ``hooks``
(called by the submit route).
"""
