"""Source of the Japanese particle-drill catalog.

Run ``python scripts/particle_drill_catalog.py --apply`` to rewrite
``data/particle_drill/ja/catalog.json`` (a bare run prints the totals only).
The catalog is the fixed list of stages, particle groups and skills that the
guides, the exercise bank and the pattern packs are authored against.

A skill is one function of one particle ("に: point in time"). Row format:
  (skill_id, particle, title, jlpt_level, target_items, confusables, packs)
``confusables`` is the default wrong-answer pool; ``packs`` is how many
infinite pattern packs to author for the skill.
"""
import argparse
import json
import os

OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'particle_drill', 'ja', 'catalog.json')
TARGET_TOTAL = 10000

# (stage_id, stage_title, stage_blurb, [(group_id, display, name, [skill rows])])
STAGES = [
 ('core1', 'Core case particles', 'Who, what, where, when: the particles every sentence needs.', [
  ('wa', 'は', 'Topic marker', [
   ('wa-topic', 'は', 'Topic: "as for X"', 5, 150, 'が を に も', 3),
   ('wa-contrast', 'は', 'Contrast: "X (but not Y)"', 5, 100, 'が を も に', 2),
   ('wa-negative', 'は', 'は with negatives and limits', 4, 60, 'が を も で', 1),
  ]),
  ('ga', 'が', 'Subject marker', [
   ('ga-subject', 'が', 'Subject / new information', 5, 150, 'は を に の', 3),
   ('ga-question', 'が', 'Question words and their answers', 5, 80, 'は を に も', 2),
   ('ga-existence', 'が', 'Existence with ある / いる', 5, 100, 'は を に で', 3),
   ('ga-stative', 'が', 'Object of 好き・上手・分かる・欲しい・できる', 5, 150, 'を は に で', 3),
   ('ga-sub-clause', 'が', 'Subject inside a sub-clause', 4, 80, 'は を の に', 1),
   ('ga-sense', 'が', 'Perception and spontaneous states (見える・聞こえる・音がする)', 4, 70, 'を は に で', 2),
  ]),
  ('o', 'を', 'Object marker', [
   ('o-object', 'を', 'Direct object', 5, 200, 'が に は で', 3),
   ('o-path', 'を', 'Path travelled (道を歩く・公園を散歩する)', 5, 90, 'で に が へ', 2),
   ('o-departure', 'を', 'Point left (家を出る・電車を降りる)', 4, 80, 'に から で が', 2),
  ]),
  ('ni', 'に', 'Point of contact: time, place, target', [
   ('ni-time', 'に', 'Point in time', 5, 120, 'で を は が', 3),
   ('ni-destination', 'に', 'Destination of movement', 5, 110, 'で を が と', 3),
   ('ni-location', 'に', 'Where something is (ある・いる・住む)', 5, 140, 'で を が へ', 3),
   ('ni-recipient', 'に', 'Recipient / indirect object', 5, 110, 'を が で と', 3),
   ('ni-target', 'に', 'Target of contact (会う・乗る・入る・触る)', 5, 140, 'を で が と', 3),
   ('ni-purpose', 'に', 'Purpose of going (食べに行く)', 5, 70, 'を で へ が', 2),
   ('ni-frequency', 'に', 'Per unit (週に二回)', 5, 50, 'で を は が', 2),
   ('ni-change', 'に', 'Result of change (～になる・～にする)', 5, 100, 'を が で と', 3),
   ('ni-source', 'に', 'Source with もらう・借りる・習う', 4, 70, 'を が で へ', 2),
   ('ni-reason', 'に', 'Cause of emotion (驚く・困る・感動する)', 3, 50, 'を で が と', 1),
  ]),
  ('e', 'へ', 'Direction marker', [
   ('e-direction', 'へ', 'Direction "towards"', 5, 70, 'を で が と', 2),
   ('e-no', 'への', 'への before a noun (友達への手紙)', 3, 40, 'にの での との から', 1),
  ]),
  ('de', 'で', 'Setting: place of action, means, cause', [
   ('de-place', 'で', 'Place where an action happens', 5, 190, 'に を が へ', 3),
   ('de-means', 'で', 'Means, tool, transport, language', 5, 140, 'に を が と', 3),
   ('de-material', 'で', 'Material / ingredients', 5, 50, 'に を から が', 2),
   ('de-cause', 'で', 'Cause or reason', 4, 80, 'に を が から', 2),
   ('de-scope', 'で', 'Scope and totals (世界で一番・三人で・全部で)', 5, 90, 'に を が の', 2),
   ('de-time-limit', 'で', 'Time or amount needed / end point (一時間で・これで)', 4, 60, 'に を まで が', 2),
  ]),
 ]),
 ('core2', 'Linking, listing and limits', 'Joining nouns, marking start and end points, comparing, and ending a sentence.', [
  ('no', 'の', 'Noun linker', [
   ('no-possessive', 'の', 'Possession and noun modification', 5, 140, 'は が を に', 3),
   ('no-nominalizer', 'の', 'Turning a verb into a noun (のが好き・のは)', 4, 110, 'こと を が に', 2),
   ('no-pronoun', 'の', 'の as "one" (赤いの)', 5, 50, 'もの こと が を', 2),
   ('no-subject', 'の', 'の as subject in a relative clause', 3, 40, 'は を に で', 1),
   ('no-explanatory', 'のだ', 'Explanatory んです / のです', 4, 80, 'です だ か よ', 1),
  ]),
  ('to', 'と', 'And, with, quote', [
   ('to-and', 'と', 'Complete list "A and B"', 5, 70, 'や も か に', 2),
   ('to-with', 'と', 'Together with', 5, 90, 'に を で が', 3),
   ('to-quote', 'と', 'Quoting speech and thought', 4, 110, 'を に が で', 2),
   ('to-reciprocal', 'と', 'Reciprocal and comparison (と結婚する・と同じ・と違う)', 4, 80, 'に を が で', 2),
  ]),
  ('mo', 'も', 'Also / even', [
   ('mo-also', 'も', 'Also, too', 5, 110, 'は が を と', 3),
   ('mo-both', 'も', 'AもBも "both / neither"', 5, 50, 'と や は が', 2),
   ('mo-total-negation', 'も', 'Question word + も + negative (何も・誰も)', 5, 70, 'か が を は', 2),
   ('mo-emphasis', 'も', 'Emphasis on amounts (三時間も・一つも)', 4, 70, 'は が を で', 2),
  ]),
  ('ya', 'や', 'Partial list', [
   ('ya-list', 'や', 'Incomplete list "A, B and so on"', 5, 70, 'と も か に', 2),
  ]),
  ('ka', 'か', 'Question / or', [
   ('ka-question', 'か', 'Question marker', 5, 50, 'よ ね も が', 2),
   ('ka-or', 'か', 'A or B', 5, 50, 'と や も に', 2),
   ('ka-indefinite', 'か', 'Question word + か (何か・誰か・どこか)', 5, 70, 'も が を は', 2),
   ('ka-embedded', 'か', 'Embedded questions (か・かどうか)', 4, 90, 'と を が の', 2),
  ]),
  ('kara', 'から', 'From', [
   ('kara-from', 'から', 'Starting point in place or time', 5, 110, 'まで に で を', 3),
   ('kara-source', 'から', 'From a person or source / made from', 4, 60, 'に で を が', 2),
  ]),
  ('made', 'まで', 'Until / as far as', [
   ('made-until', 'まで', 'End point in place or time', 5, 100, 'から に で までに', 3),
   ('madeni-deadline', 'までに', 'Deadline "by"', 4, 80, 'まで に で から', 2),
  ]),
  ('yori', 'より', 'Than', [
   ('yori-comparison', 'より', 'Comparison "than"', 5, 90, 'ほど から まで と', 3),
   ('yori-formal-from', 'より', 'Formal "from" (午後一時より)', 2, 30, 'から まで に で', 0),
  ]),
  ('final-basic', 'ね・よ', 'Basic sentence endings', [
   ('ne-agreement', 'ね', 'Seeking agreement / shared feeling', 5, 60, 'よ か が を', 1),
   ('yo-assertion', 'よ', 'Telling the listener something new', 5, 60, 'ね か が を', 1),
   ('yone-confirm', 'よね', 'Confirming "right?"', 4, 40, 'よ ね か な', 1),
  ]),
 ]),
 ('clinic', 'Contrast clinics', 'Minimal pairs for the choices learners get wrong most. Pure drilling.', [
  ('clinic-wa-ga', 'は vs が', 'Topic or subject?', [
   ('x-wa-ga', 'は／が', 'は or が', 5, 320, 'は が', 4),
  ]),
  ('clinic-ni-de', 'に vs で', 'Being somewhere or doing something there?', [
   ('x-ni-de', 'に／で', 'に or で (place)', 5, 220, 'に で', 4),
  ]),
  ('clinic-o-ga', 'を vs が', 'Object or the thing that is liked, wanted, possible?', [
   ('x-o-ga', 'を／が', 'を or が', 5, 160, 'を が', 3),
   ('x-trans-intrans', 'を／が', 'Transitive / intransitive pairs (開ける・開く)', 4, 220, 'を が', 4),
  ]),
  ('clinic-o-ni', 'を vs に', 'Which verbs take に, not を?', [
   ('x-o-ni', 'を／に', 'を or に with verbs', 5, 160, 'を に', 3),
  ]),
  ('clinic-ni-e-made', 'に・へ・まで', 'Destination, direction or limit?', [
   ('x-ni-e-made', 'に／へ／まで', 'に, へ or まで', 5, 70, 'に へ まで', 2),
  ]),
  ('clinic-to-ni', 'と vs に', 'Mutual or one-way?', [
   ('x-to-ni', 'と／に', 'と or に (会う・話す・相談する)', 4, 80, 'と に', 2),
  ]),
  ('clinic-to-ya-ka', 'と・や・か', 'Which kind of list?', [
   ('x-to-ya-ka', 'と／や／か', 'と, や or か', 5, 60, 'と や か', 2),
  ]),
  ('clinic-kara-made', 'から・まで・までに', 'Start, end or deadline?', [
   ('x-made-madeni', 'まで／までに', 'まで or までに', 4, 90, 'まで までに', 2),
  ]),
  ('clinic-mo-wa', 'も vs は', 'Adding or contrasting?', [
   ('x-mo-wa', 'も／は', 'も or は', 5, 60, 'も は', 2),
  ]),
  ('clinic-mixed-n5', 'Mixed N5', 'Every core particle in one sentence.', [
   ('x-mixed-n5', '混合', 'Mixed core particles', 5, 300, 'は が を に で と も の', 6),
  ]),
 ]),
 ('focus', 'Focus and limit particles', 'Only, even, about, such as: particles that add an attitude to a word.', [
  ('dake', 'だけ', 'Only', [
   ('dake-only', 'だけ', 'Only / just', 4, 80, 'しか ばかり も ほど', 2),
   ('dake-extent', 'だけ', 'As much as (できるだけ・好きなだけ)', 3, 40, 'ほど しか ばかり まで', 1),
  ]),
  ('shika', 'しか', 'Nothing but', [
   ('shika-nai', 'しか', 'しか + negative "only"', 4, 100, 'だけ も ばかり は', 2),
  ]),
  ('bakari', 'ばかり', 'Nothing but / just did', [
   ('bakari-only', 'ばかり', 'Nothing but, always', 4, 70, 'だけ しか ほど も', 2),
   ('bakari-just', 'ばかり', 'Just did (～たばかり)', 4, 50, 'ところ だけ まで ながら', 1),
  ]),
  ('hodo', 'ほど', 'Extent', [
   ('hodo-extent', 'ほど', 'To the extent that / about', 3, 60, 'くらい だけ より まで', 1),
   ('hodo-nai', 'ほど', 'Not as … as (ほど～ない)', 4, 70, 'より だけ くらい しか', 2),
   ('ba-hodo', 'ほど', 'The more … the more (～ば～ほど)', 3, 40, 'より だけ まで くらい', 1),
  ]),
  ('kurai', 'くらい', 'About', [
   ('kurai-about', 'くらい', 'Approximately (くらい・ぐらい)', 5, 60, 'ごろ ほど だけ まで', 2),
   ('kurai-extent', 'くらい', 'To the extent / at least', 3, 50, 'ほど だけ しか まで', 1),
  ]),
  ('goro', 'ごろ', 'Around a time', [
   ('goro-time', 'ごろ', 'Around (a point in time)', 5, 40, 'くらい に まで ほど', 2),
  ]),
  ('nado', 'など', 'Such as', [
   ('nado-etc', 'など', 'And so on / such as', 4, 50, 'とか や も だけ', 1),
   ('nanka-nante', 'なんか', 'なんか・なんて: belittling or surprise', 3, 70, 'など こそ さえ だけ', 1),
  ]),
  ('toka', 'とか', 'Things like', [
   ('toka-list', 'とか', 'Casual examples', 4, 50, 'や と など も', 1),
  ]),
  ('demo', 'でも', 'Even / or something', [
   ('demo-even', 'でも', 'Even', 4, 60, 'も さえ は が', 1),
   ('demo-suggestion', 'でも', 'Or something (お茶でも)', 4, 50, 'を も が や', 1),
   ('demo-any', 'でも', 'Question word + でも (何でも・いつでも)', 4, 70, 'も か が は', 2),
  ]),
  ('sae', 'さえ', 'Even / if only', [
   ('sae-even', 'さえ', 'Even', 3, 50, 'も でも こそ だけ', 1),
   ('sae-ba', 'さえ', 'If only (～さえ～ば)', 3, 40, 'だけ こそ でも しか', 1),
  ]),
  ('koso', 'こそ', 'Precisely', [
   ('koso-emphasis', 'こそ', 'This very one', 3, 60, 'さえ も は だけ', 1),
  ]),
  ('made-even', 'まで', 'Even (extreme case)', [
   ('made-even', 'まで', 'Even, as far as', 3, 40, 'さえ も だけ こそ', 0),
  ]),
  ('zutsu', 'ずつ', 'Each', [
   ('zutsu-each', 'ずつ', 'Each / at a time', 4, 50, 'だけ ごと も ほど', 2),
  ]),
  ('tte', 'って', 'Casual quote / topic', [
   ('tte-quote', 'って', 'Casual と / という', 4, 60, 'と は を が', 1),
   ('tte-topic', 'って', 'Casual topic "what about X"', 3, 40, 'は が を と', 1),
  ]),
  ('toiu', 'という', 'Called / that', [
   ('toiu-called', 'という', 'Called, named, the fact that', 4, 70, 'の と って が', 1),
  ]),
  ('goto', 'ごと', 'Every', [
   ('goto-every', 'ごとに', 'Every / each time (ごとに・おきに)', 3, 40, 'ずつ まで ほど だけ', 1),
  ]),
  ('nomi', 'のみ', 'Only (formal)', [
   ('nomi-only', 'のみ', 'Formal "only"', 2, 30, 'だけ しか ばかり こそ', 0),
  ]),
  ('kiri', 'きり', 'Only / since', [
   ('kiri-only', 'きり', 'Only; since then (～たきり)', 2, 40, 'だけ まで ばかり しか', 0),
  ]),
  ('sura', 'すら', 'Even (formal)', [
   ('sura-even', 'すら', 'Even', 1, 30, 'さえ こそ も だけ', 0),
  ]),
  ('yara-dano', 'やら', 'Listing with feeling', [
   ('yara-list', 'やら', 'AやらBやら', 2, 30, 'とか や だの も', 0),
   ('dano-list', 'だの', 'AだのBだの (complaining)', 1, 25, 'やら とか や も', 0),
  ]),
 ]),
 ('clause', 'Connecting clauses', 'Because, although, while, if: particles that join one clause to the next.', [
  ('kara-reason', 'から', 'Because', [
   ('kara-because', 'から', 'Reason "because"', 5, 110, 'ので のに けど と', 2),
   ('te-kara', 'てから', 'After doing', 5, 60, 'まえに ながら たら と', 2),
  ]),
  ('node', 'ので', 'Since', [
   ('node-because', 'ので', 'Reason (soft, objective)', 4, 90, 'のに から けど ても', 2),
  ]),
  ('noni', 'のに', 'Although / in order to', [
   ('noni-although', 'のに', 'Even though (unexpected)', 4, 100, 'ので から ても けど', 2),
   ('noni-purpose', 'のに', 'For the purpose of (～のに使う)', 4, 40, 'ために ので には で', 1),
  ]),
  ('kedo', 'けど・が', 'But', [
   ('kedo-but', 'けど', 'But (けど・けれども)', 5, 80, 'から ので し のに', 2),
   ('ga-but', 'が', 'But / soft lead-in', 5, 80, 'から ので し と', 2),
  ]),
  ('shi', 'し', 'And what is more', [
   ('shi-listing', 'し', 'Listing reasons', 4, 70, 'から て と たり', 1),
  ]),
  ('te-form-links', 'て', 'て-form links', [
   ('te-sequence', 'て', 'And then / and (て・で)', 5, 100, 'と から ながら し', 2),
   ('te-mo', 'ても', 'Even if', 4, 90, 'たら のに ば と', 2),
   ('te-wa', 'ては', 'ては (てはいけない・ては)', 4, 60, 'ても たら て と', 1),
  ]),
  ('nagara', 'ながら', 'While', [
   ('nagara-while', 'ながら', 'While doing', 4, 70, 'て たり から し', 2),
   ('nagara-although', 'ながら', 'Although (ながらも)', 2, 30, 'のに つつ ても けど', 0),
  ]),
  ('tari', 'たり', 'Things like doing', [
   ('tari-tari', 'たり', '～たり～たりする', 5, 70, 'て し ながら と', 2),
  ]),
  ('conditionals', 'と・ば・たら・なら', 'If / when', [
   ('to-conditional', 'と', 'Whenever / natural result', 4, 90, 'ば たら なら ても', 2),
   ('ba-conditional', 'ば', 'If (ば)', 4, 90, 'と たら なら ても', 2),
   ('tara-conditional', 'たら', 'If / when (たら)', 4, 100, 'と ば なら ても', 2),
   ('nara-conditional', 'なら', 'If that is the case (なら)', 4, 90, 'と ば たら ても', 2),
   ('x-conditionals', 'と／ば／たら／なら', 'Which conditional?', 3, 160, 'と ば たら なら', 2),
  ]),
  ('tame', 'ために・ように', 'Purpose', [
   ('tameni-purpose', 'ために', 'In order to / for the sake of', 4, 70, 'ように のに ので から', 2),
   ('youni-purpose', 'ように', 'So that (ように)', 4, 70, 'ために のに から と', 2),
   ('x-tameni-youni', 'ために／ように', 'ために or ように', 3, 80, 'ために ように', 1),
  ]),
  ('aida', 'あいだ・うちに', 'While / before it changes', [
   ('aida-ni', 'あいだに', 'あいだ vs あいだに', 4, 60, 'うちに まで までに ながら', 1),
   ('uchi-ni', 'うちに', 'While still (うちに)', 3, 50, 'あいだに までに ながら まえに', 1),
  ]),
  ('mae-ato', 'まえに・あとで', 'Before / after', [
   ('maeni-atode', 'まえに', 'まえに・あとで', 5, 60, 'てから ながら とき まで', 2),
  ]),
  ('toki', 'とき', 'When', [
   ('toki-when', 'とき', 'とき・ときに・ときは', 5, 60, 'たら と まえに あいだ', 2),
  ]),
  ('mono-no', 'ものの', 'Although (written)', [
   ('monono-although', 'ものの', 'Although', 2, 35, 'のに ので から ながら', 0),
  ]),
  ('tsutsu', 'つつ', 'While (written)', [
   ('tsutsu-while', 'つつ', 'While / つつある', 2, 35, 'ながら て たり ものの', 0),
  ]),
  ('kuse-ni', 'くせに', 'And yet', [
   ('kuseni-despite', 'くせに', 'Despite (critical)', 3, 40, 'のに ので から ものの', 0),
  ]),
 ]),
 ('voice', 'Who does what to whom', 'Particles that change when the verb changes: giving, passive, causative, potential.', [
  ('giving', 'あげる・くれる・もらう', 'Giving and receiving', [
   ('give-ageru', 'に', 'あげる: giver が/は, receiver に', 5, 80, 'を が から で', 2),
   ('give-kureru', 'が', 'くれる: giver が, to me に', 4, 80, 'に を から で', 2),
   ('give-morau', 'に', 'もらう: receiver が/は, giver に/から', 4, 80, 'を が で へ', 2),
   ('give-te-forms', 'に', '～てあげる・～てくれる・～てもらう', 4, 110, 'を が から で', 2),
  ]),
  ('passive', '受身', 'Passive', [
   ('passive-agent', 'に', 'Passive: doer marked with に', 4, 110, 'を が で から', 2),
   ('passive-suffering', 'を', 'Indirect passive (財布を盗まれた)', 4, 70, 'が に で は', 1),
   ('passive-niyotte', 'によって', 'Created by (によって)', 3, 40, 'に で から を', 1),
  ]),
  ('causative', '使役', 'Causative', [
   ('causative-o-ni', 'に', 'Causative: を or に for the person made to act', 4, 110, 'を が で と', 2),
   ('causative-passive', 'に', 'Causative-passive: made to do', 3, 60, 'を が で から', 1),
  ]),
  ('potential', '可能', 'Potential', [
   ('potential-ga', 'が', 'Potential verbs: が (and を)', 4, 90, 'に で は の', 2),
  ]),
  ('desire', '～たい・欲しい', 'Wanting', [
   ('tai-ga-o', 'が', '～たい with が / を; 欲しい with が', 5, 70, 'に で は の', 2),
   ('te-hoshii', 'に', '～てほしい: person marked with に', 4, 50, 'を が で と', 1),
  ]),
 ]),
 ('final', 'Sentence-final particles', 'The last syllable carries the tone of voice.', [
  ('final-na', 'な', 'な', [
   ('na-musing', 'な', 'Musing / emotion (な・なあ)', 4, 50, 'ね よ か ぞ', 1),
   ('na-prohibition', 'な', 'Prohibition (するな)', 4, 40, 'ね よ か ぞ', 1),
  ]),
  ('final-kana', 'かな', 'I wonder', [
   ('kana-wonder', 'かな', 'かな・かしら', 4, 60, 'よね よ ね ぞ', 1),
  ]),
  ('final-no', 'の', 'Soft question / explanation', [
   ('no-final', 'の', 'Sentence-final の', 4, 50, 'か よ ね な', 1),
  ]),
  ('final-kke', 'っけ', 'What was it again?', [
   ('kke-recall', 'っけ', 'Trying to recall', 3, 40, 'かな よね か の', 1),
  ]),
  ('final-zo-ze', 'ぞ・ぜ', 'Rough emphasis', [
   ('zo-ze', 'ぞ', 'ぞ・ぜ', 3, 40, 'わ ね かな の', 0),
  ]),
  ('final-wa-sa', 'わ・さ', 'わ and さ', [
   ('wa-final', 'わ', 'Sentence-final わ', 3, 30, 'ぞ か な ぜ', 0),
   ('sa-final', 'さ', 'Sentence-final さ', 3, 30, 'か わ かな っけ', 0),
  ]),
  ('final-mono', 'もの', 'Because, you see', [
   ('mono-reason', 'もの', 'もの・もん', 3, 40, 'から よ ね かな', 0),
  ]),
  ('final-tomo', 'とも', 'Of course', [
   ('tomo-certainly', 'とも', 'Emphatic agreement', 2, 25, 'よ ね かな っけ', 0),
  ]),
  ('final-ja-nai', 'じゃない', 'Isn\'t it', [
   ('janai-ka', 'じゃないか', 'じゃない・ではないか', 3, 50, 'だろう かな よね っけ', 0),
  ]),
  ('final-tte', 'って', 'I hear', [
   ('tte-hearsay', 'って', 'Sentence-final って / だって', 3, 40, 'よ ね かな っけ', 0),
  ]),
 ]),
 ('compound1', 'Compound particles I', 'Two or three words acting as one particle. Everyday and exam staples.', [
  ('nitsuite', 'について', 'About', [('nitsuite', 'について', 'Concerning', 4, 60, 'にとって に対して によって として', 2)]),
  ('nitotte', 'にとって', 'For / from the viewpoint of', [('nitotte', 'にとって', 'From the standpoint of', 3, 70, 'について に対して として によって', 1)]),
  ('nitaishite', 'に対して', 'Towards / in contrast to', [('nitaishite', 'に対して', 'Towards; in contrast', 3, 70, 'にとって について として によって', 1)]),
  ('toshite', 'として', 'As', [('toshite', 'として', 'In the role of', 3, 70, 'にとって に対して について によって', 1)]),
  ('niyotte', 'によって', 'By / depending on', [
   ('niyotte-means', 'によって', 'By means of / due to', 3, 50, 'について にとって として に対して', 1),
   ('niyotte-depending', 'によって', 'Depending on', 3, 50, 'について にとって として に対して', 1),
  ]),
  ('niyoruto', 'によると', 'According to', [('niyoruto', 'によると', 'According to (hearsay)', 4, 50, 'によって について にとって として', 1)]),
  ('x-compound-core', 'について／にとって／に対して／として／によって', 'Which compound?', [
   ('x-compound-core', '複合', 'について・にとって・に対して・として・によって', 3, 160, 'について にとって に対して として によって', 1)]),
  ('nokawarini', 'のかわりに', 'Instead of', [('kawarini', 'かわりに', 'Instead of / in exchange', 3, 50, 'のために のおかげで について として', 1)]),
  ('okagede-seide', 'おかげで・せいで', 'Thanks to / because of', [
   ('okagede', 'おかげで', 'Thanks to', 3, 50, 'せいで ために かわりに について', 1),
   ('seide', 'せいで', 'Because of (blame)', 3, 50, 'おかげで ために かわりに について', 1),
  ]),
  ('nikurabete', 'に比べて', 'Compared with', [('nikurabete', 'に比べて', 'Compared with', 3, 45, 'に対して について によって として', 1)]),
  ('toissho', 'といっしょに', 'Together with', [('toisshoni', 'といっしょに', 'Together with', 5, 40, 'のために について として かわりに', 2)]),
  ('nokotode', 'のことで', 'About the matter of', [('nokoto', 'のこと', 'のこと: about (好き・心配・話す)', 4, 50, 'について のため として にとって', 1)]),
  ('toshitewa', 'にしては', 'For (a) …', [
   ('nishitewa', 'にしては', 'Considering that', 3, 45, 'わりに として にとって にしても', 0),
   ('wari-ni', 'わりに', 'In proportion to / unexpectedly', 3, 45, 'にしては くせに として かわりに', 0),
  ]),
  ('wo-tooshite', 'を通して', 'Through', [('wotooshite', 'を通して', 'Through / via (を通して・を通じて)', 3, 45, 'によって について にわたって として', 0)]),
  ('ni-kakete', 'にかけて', 'Over a span', [('nikakete', 'にかけて', 'From … through to', 3, 40, 'にわたって まで までに を通して', 0)]),
  ('ni-wa', 'には', 'In order to / for', [('niwa-purpose', 'には', 'には: in order to; for (someone)', 3, 50, 'ために のに では とは', 0)]),
  ('to-wa', 'とは', 'Definition / surprise', [('towa', 'とは', 'とは・というのは', 3, 40, 'には では とも って', 0)]),
  ('dewa', 'では', 'In / as for (scope)', [('dewa-scope', 'では', 'では: within; judging by', 4, 50, 'には とは にも でも', 1)]),
  ('double', '二重助詞', 'Stacked particles', [
   ('double-particles', 'には', 'には・では・とは・からは・までは・へは', 4, 110, 'には では とは からは', 1),
   ('double-mo', 'にも', 'にも・でも・とも・からも', 4, 70, 'にも でも とも からも', 1),
   ('no-compound', 'での', 'での・との・からの・までの・への before a noun', 3, 80, 'での との からの までの への', 1),
  ]),
 ]),
 ('compound2', 'Compound particles II', 'The N2 written-style set.', [
  ('nikanshite', 'に関して', 'Regarding', [('nikanshite', 'に関して', 'Regarding (formal)', 2, 40, 'に対して にとって において に基づいて', 0)]),
  ('nioite', 'において', 'In / at (formal)', [('nioite', 'において', 'At, in (formal place/time/field)', 2, 45, 'に関して に対して によって にとって', 0)]),
  ('niwatatte', 'にわたって', 'Across', [('niwatatte', 'にわたって', 'Throughout a span', 2, 40, 'にかけて を通じて において に沿って', 0)]),
  ('nisotte', 'に沿って', 'Along', [('nisotte', 'に沿って', 'Along / in line with', 2, 35, 'に基づいて に従って にわたって に応じて', 0)]),
  ('nimotozuite', 'に基づいて', 'Based on', [
   ('nimotozuite', 'に基づいて', 'On the basis of', 2, 40, 'に沿って に従って をもとに に応じて', 0),
   ('womotoni', 'をもとに', 'Using as material', 2, 35, 'に基づいて を中心に をめぐって に沿って', 0),
  ]),
  ('womegutte', 'をめぐって', 'Over (a dispute)', [('womegutte', 'をめぐって', 'Concerning (contested issue)', 2, 35, 'に関して について を中心に をもとに', 0)]),
  ('nikuwaete', 'に加えて', 'In addition to', [('nikuwaete', 'に加えて', 'In addition to', 2, 35, 'に対して に比べて に応じて にかわって', 0)]),
  ('nitsurete', 'につれて', 'As … changes', [
   ('nitsurete', 'につれて', 'As (gradual change)', 2, 40, 'に従って に伴って とともに に応じて', 0),
   ('nishitagatte', 'に従って', 'In accordance with / as', 2, 40, 'につれて に伴って に沿って に基づいて', 0),
   ('nitomonatte', 'に伴って', 'Along with', 2, 35, 'につれて に従って とともに に応じて', 0),
   ('totomoni', 'とともに', 'Together with / as', 2, 40, 'につれて に伴って に従って に加えて', 0),
  ]),
  ('nioujite', 'に応じて', 'In response to', [('nioujite', 'に応じて', 'According to / in proportion', 2, 35, 'に従って によって に沿って に基づいて', 0)]),
  ('nihanshite', 'に反して', 'Contrary to', [('nihanshite', 'に反して', 'Contrary to', 2, 35, 'に対して に比べて に応じて に従って', 0)]),
  ('wotowazu', 'を問わず', 'Regardless of', [
   ('wotowazu', 'を問わず', 'Regardless of', 2, 40, 'にかかわらず にもかかわらず に限らず はもちろん', 0),
   ('nikakawarazu', 'にかかわらず', 'Regardless / whether or not', 2, 40, 'を問わず にもかかわらず に限らず に応じて', 0),
   ('nimokakawarazu', 'にもかかわらず', 'In spite of', 2, 40, 'にかかわらず を問わず のに ものの', 0),
  ]),
  ('nikagirazu', 'に限らず', 'Not limited to', [
   ('nikagirazu', 'に限らず', 'Not only', 2, 35, 'を問わず に限って にかかわらず はもちろん', 0),
   ('nikagitte', 'に限って', 'Only in the case of', 2, 35, 'に限らず に限り だけ こそ', 0),
  ]),
  ('bakarika', 'ばかりか', 'Not only … but', [
   ('bakarika', 'ばかりか', 'Not only (ばかりか・ばかりでなく)', 2, 40, 'どころか はもちろん だけ に限らず', 0),
   ('dokoroka', 'どころか', 'Far from', 2, 40, 'ばかりか はもちろん に限らず だけ', 0),
   ('wamochiron', 'はもちろん', 'Let alone / of course', 2, 35, 'ばかりか どころか に限らず をはじめ', 0),
  ]),
  ('wohajime', 'をはじめ', 'Starting with', [('wohajime', 'をはじめ', 'Beginning with (representative example)', 2, 35, 'を中心に はもちろん に加えて をもとに', 0)]),
  ('wochuushinni', 'を中心に', 'Centred on', [('wochuushinni', 'を中心に', 'Centring on', 2, 35, 'をはじめ をもとに をめぐって に沿って', 0)]),
  ('karaniwa', 'からには', 'Now that', [
   ('karaniwa', 'からには', 'Now that / since', 2, 40, 'からこそ からといって ものの くせに', 0),
   ('karakoso', 'からこそ', 'Precisely because', 2, 35, 'からには からといって ので のに', 0),
   ('karatoitte', 'からといって', 'Just because', 2, 40, 'からには からこそ のに ので', 0),
  ]),
  ('toshitemo', 'としても', 'Even supposing', [
   ('toshitemo', 'としても', 'Even if (hypothetical)', 2, 40, 'にしても としては にしては ても', 0),
   ('nishitemo', 'にしても', 'Even granting / whether', 2, 40, 'としても にしては にせよ ても', 0),
  ]),
  ('toiuyori', 'というより', 'Rather than', [
   ('toiuyori', 'というより', 'Rather than say', 2, 35, 'といっても といえば としても どころか', 0),
   ('toittemo', 'といっても', 'Although one says', 2, 35, 'というより といえば としても からといって', 0),
   ('toieba', 'といえば', 'Speaking of', 2, 35, 'というより といっても としては にとって', 0),
  ]),
  ('nikawatte', 'にかわって', 'In place of', [('nikawatte', 'にかわって', 'In place of (a person)', 2, 35, 'に対して に加えて に応じて として', 0)]),
  ('nisaishite', 'に際して', 'On the occasion of', [
   ('nisaishite', 'に際して', 'On the occasion of', 2, 35, 'において にあたって に先立って に応じて', 0),
   ('nisakidatte', 'に先立って', 'Prior to', 2, 30, 'に際して にあたって において に続いて', 0),
  ]),
  ('uede', 'うえで', 'Upon / in terms of', [
   ('uede', '上で', 'After doing; in doing', 2, 40, '上に 上は うちに 際に', 0),
   ('ueni', '上に', 'On top of that', 2, 35, '上で 上は ばかりか くせに', 0),
  ]),
  ('monodakara', 'ものだから', 'Because (excuse)', [('monodakara', 'ものだから', 'Because (personal excuse)', 2, 35, 'からには からこそ ものの くせに', 0)]),
  ('x-compound-n2', '複合 N2', 'N2 mixed review', [('x-compound-n2', '複合', 'N2 compound particles mixed', 2, 180, 'に関して において に基づいて に応じて', 0)]),
 ]),
 ('literary', 'Formal and literary', 'The N1 layer: stiff, written, and unmistakable once drilled.', [
  ('yainaya', 'や否や', 'The moment', [
   ('yainaya', 'や否や', 'As soon as (や・や否や)', 1, 30, 'が早いか なり そばから とたんに', 0),
   ('gahayaika', 'が早いか', 'No sooner than', 1, 30, 'や否や なり そばから とたんに', 0),
   ('nari', 'なり', 'As soon as (なり)', 1, 30, 'や否や が早いか そばから ながら', 0),
   ('sobakara', 'そばから', 'As soon as, again and again', 1, 25, 'や否や が早いか なり とたんに', 0),
  ]),
  ('womotte', 'をもって', 'By means of / as of', [('womotte', 'をもって', 'With; as of (formal)', 1, 30, 'において にあって をよそに を機に', 0)]),
  ('niatte', 'にあって', 'In (a situation)', [('niatte', 'にあって', 'In, under (circumstances)', 1, 30, 'において をもって として にして', 0)]),
  ('woyosoni', 'をよそに', 'Ignoring', [('woyosoni', 'をよそに', 'In disregard of', 1, 30, 'をものともせず にもかかわらず を問わず に反して', 0)]),
  ('womonotomosezu', 'をものともせず', 'Undaunted by', [('womonotomosezu', 'をものともせず', 'In defiance of', 1, 30, 'をよそに にもかかわらず を問わず に反して', 0)]),
  ('wokawakirini', 'を皮切りに', 'Starting with', [
   ('wokawakirini', 'を皮切りに', 'Starting with (a series)', 1, 25, 'を機に をはじめ を限りに をもって', 0),
   ('wokagirini', 'を限りに', 'As the last time', 1, 25, 'を皮切りに をもって を機に を境に', 0),
   ('wokini', 'を機に', 'Taking the opportunity of', 1, 30, 'を皮切りに を限りに をもって を境に', 0),
  ]),
  ('naradewa', 'ならでは', 'Unique to', [('naradewa', 'ならでは', 'Only possible with', 1, 30, 'にして こそ だけ をおいて', 0)]),
  ('wooite', 'をおいて', 'Other than', [('wooite', 'をおいて', 'No one but (をおいて～ない)', 1, 25, 'ならでは を除いて に限らず はおろか', 0)]),
  ('waoroka', 'はおろか', 'Let alone', [('waoroka', 'はおろか', 'Let alone', 1, 30, 'はもちろん どころか ばかりか をおいて', 0)]),
  ('tomonaruto', 'ともなると', 'When it comes to', [
   ('tomonaruto', 'ともなると', 'Once one reaches (ともなると・ともなれば)', 1, 30, 'とあって にして として といえども', 0),
   ('toatte', 'とあって', 'Because of the special situation', 1, 30, 'ともなると にして ゆえに といえども', 0),
  ]),
  ('toiedomo', 'といえども', 'Even though', [
   ('toiedomo', 'といえども', 'Even (a) …', 1, 30, 'とあって ともなると ながらも とはいえ', 0),
   ('towaie', 'とはいえ', 'That said', 1, 30, 'といえども ものの ながらも とあって', 0),
  ]),
  ('deare', 'であれ', 'Whether … or', [
   ('deare', 'であれ', 'AであれBであれ / にせよ・にしろ', 1, 35, 'といい なり やら だの', 0),
   ('toii', 'といい', 'AといいBといい', 1, 25, 'であれ なり やら だの', 0),
   ('nari-nari', 'なり', 'AなりBなり (either)', 1, 25, 'であれ といい やら とか', 0),
  ]),
  ('yueni', 'ゆえに', 'Because (literary)', [('yueni', 'ゆえに', 'On account of', 1, 30, 'とあって こととて ばこそ をもって', 0)]),
  ('bakoso', 'ばこそ', 'Precisely because', [('bakoso', 'ばこそ', '～ばこそ', 1, 25, 'ゆえに からこそ とあって こととて', 0)]),
  ('nishite', 'にして', 'Only at / both', [('nishite', 'にして', 'Only at (that level); in just', 1, 30, 'にあって として ならでは をもって', 0)]),
  ('tote', 'とて', 'Even / just because', [('tote', 'とて', 'Even (とて・としたところで)', 1, 25, 'といえども すら だに こそ', 0)]),
  ('dani', 'だに', 'Even (archaic)', [('dani', 'だに', 'Even to (imagine)', 1, 20, 'すら さえ とて こそ', 0)]),
  ('zukume', 'ながらに', 'While remaining', [('nagarani', 'ながらに', 'In the state of (生まれながらに)', 1, 25, 'つつ ながらも がてら かたわら', 0)]),
  ('gatera', 'がてら', 'While at it', [
   ('gatera', 'がてら', 'On the same occasion', 1, 30, 'かたわら ながらに つつ かたがた', 0),
   ('katawara', 'かたわら', 'Alongside (a main activity)', 1, 30, 'がてら ながらに つつ かたがた', 0),
  ]),
  ('x-literary', '文語', 'N1 mixed review', [('x-literary-n1', '混合', 'N1 particles mixed', 1, 150, 'をもって にあって とあって といえども', 0)]),
 ]),
]


def build(stage_rows=None, target_total=None):
    stage_rows = STAGES if stage_rows is None else stage_rows
    target_total = TARGET_TOTAL if target_total is None else target_total
    stages, skills, total = [], [], 0
    for sid, stitle, blurb, groups in stage_rows:
        gout = []
        for gid, display, name, rows in groups:
            ids = []
            for row in rows:
                kid, particle, title, lv, n, conf, packs = row[:7]
                ids.append(kid)
                skills.append({'id': kid, 'group': gid, 'stage': sid, 'p': particle,
                               'title': title, 'lv': lv, 'n': n,
                               'conf': conf.split(), 'packs': packs})
                if len(row) > 7:
                    skills[-1]['ask'] = row[7]
                total += n
            gout.append({'id': gid, 'p': display, 'name': name, 'skills': ids})
        stages.append({'id': sid, 'title': stitle, 'blurb': blurb, 'groups': gout})
    # The rows above are relative weights; scale them to TARGET_TOTAL exactly
    # (multiples of 5, at least 20 a skill, remainder on the largest skills).
    factor = target_total / total
    for s in skills:
        s['n'] = max(20, int(round(s['n'] * factor / 5.0)) * 5)
    diff = target_total - sum(s['n'] for s in skills)
    big = sorted(skills, key=lambda s: -s['n'])
    i = 0
    while diff:
        step = 5 if diff > 0 else -5
        big[i % 40]['n'] += step
        diff -= step
        i += 1
    total = sum(s['n'] for s in skills)
    ids = [s['id'] for s in skills]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    gids = [g['id'] for st in stages for g in st['groups']]
    assert len(gids) == len(set(gids)), [i for i in gids if gids.count(i) > 1]
    return {'language': 'ja', 'version': 1, 'stages': stages, 'skills': skills}, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='write catalog.json')
    args = ap.parse_args()
    cat, total = build()
    print(f"stages {len(cat['stages'])}  groups {sum(len(s['groups']) for s in cat['stages'])}  "
          f"skills {len(cat['skills'])}  items {total}  packs {sum(s['packs'] for s in cat['skills'])}")
    if args.apply:
        with open(OUT, 'w', encoding='utf-8') as fh:
            json.dump(cat, fh, ensure_ascii=False, indent=1)
        print('wrote', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
