# Author brief 01 — zh -> en, arm `sentencewise`

Read `data/sentence_refs/resplit_2026-11-12/zh_en/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/resplit_2026-11-12/zh_en/sentence_refs/docs/<test_id>.en.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/resplit_2026-11-12/zh_en --tests 2ab9149f-c8d1-4eda-aa9d-1d2a31ccf3b3`
and fix until every test is `ok`.

## 2ab9149f-c8d1-4eda-aa9d-1d2a31ccf3b3 — 社区共建绿色家园：植树行动改变城市

Passage (for context, do not translate as a block unless the arm says so):

春天来了，社区里很多人开始一起种树。这个活动是居民自己组织的，大家自愿参加，没有人必须来。这种志愿服务让邻居们关系更好了。每天早上，人们带着小树苗和水桶来到公园，挖坑、种树、浇水。虽然有时候很累，但是大家都很开心。种树不只是让城市变漂亮，它对生态保护也很重要。树木可以净化空气，减少噪音，还能帮助小动物和小鸟找到家。一位老师说：“我们种的不只是树，是在恢复生物多样性。”她的意思是，不同种类的植物和动物可以一起生活，大自然才会健康。这个项目叫“绿色家园”，是一个本地行动的好例子。它从小小的一块空地开始，现在已经扩展到五个小区。每个参与的人都是社区建设的一部分。虽然城市发展的速度很快，但我们也能做一点事来保护环境。有一位老人说：“我小时候这里有很多树，现在我们正在把绿色还给城市。”年轻人和孩子也加入进来，他们学习自然知识，也学会了合作。虽然一个人的力量很小，但是大家一起努力，就能带来大的改变。这个植树项目告诉我们，保护地球可以从身边的小事做起。

Sentences:

- idx 0: 春天来了，社区里很多人开始一起种树。
- idx 1: 这个活动是居民自己组织的，大家自愿参加，没有人必须来。
- idx 2: 这种志愿服务让邻居们关系更好了。
- idx 3: 每天早上，人们带着小树苗和水桶来到公园，挖坑、种树、浇水。
- idx 4: 虽然有时候很累，但是大家都很开心。
- idx 5: 种树不只是让城市变漂亮，它对生态保护也很重要。
- idx 6: 树木可以净化空气，减少噪音，还能帮助小动物和小鸟找到家。
- idx 7: 一位老师说：“我们种的不只是树，是在恢复生物多样性。”
- idx 8: 她的意思是，不同种类的植物和动物可以一起生活，大自然才会健康。
- idx 9: 这个项目叫“绿色家园”，是一个本地行动的好例子。
- idx 10: 它从小小的一块空地开始，现在已经扩展到五个小区。
- idx 11: 每个参与的人都是社区建设的一部分。
- idx 12: 虽然城市发展的速度很快，但我们也能做一点事来保护环境。
- idx 13: 有一位老人说：“我小时候这里有很多树，现在我们正在把绿色还给城市。”
- idx 14: 年轻人和孩子也加入进来，他们学习自然知识，也学会了合作。
- idx 15: 虽然一个人的力量很小，但是大家一起努力，就能带来大的改变。
- idx 16: 这个植树项目告诉我们，保护地球可以从身边的小事做起。
