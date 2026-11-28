"""Source of the Japanese grammar-drill catalog (the second sentence-drill course).

Run ``python scripts/grammar_drill_catalog.py --apply`` to rewrite
``data/particle_drill/ja-grammar/catalog.json`` (a bare run prints totals).

Same row format as scripts/particle_drill_catalog.py:
  (skill_id, display, title, jlpt_level, target_items, confusables, packs[, ask])
``ask`` is set for the two kanji areas: 'reading' (the kanji is shown and its
reading is asked) and 'kanji' (the reading is shown and the kanji is chosen).
Skill ids are unique across both courses: progress is one document.
"""
import argparse
import json
import os

import particle_drill_catalog as base

OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'particle_drill', 'ja-grammar',
                   'catalog.json')
TARGET_TOTAL = 8000
R, K = 'reading', 'kanji'

STAGES = [
 ('give', 'Giving and receiving', 'Who gives to whom: the verb changes with the direction.', [
  ('gv-basic', 'あげる・くれる・もらう', 'Give and receive', [
   ('gv-ageru', 'あげる', 'あげる: giving away from me', 5, 50, 'くれる もらう くださる', 1),
   ('gv-kureru', 'くれる', 'くれる: someone gives to me or mine', 5, 50, 'あげる もらう やる', 1),
   ('gv-morau', 'もらう', 'もらう: receiving', 5, 50, 'あげる くれる いただく', 1),
  ]),
  ('gv-te', 'てあげる・てくれる・てもらう', 'Doing favours', [
   ('gv-teageru', 'てあげる', '〜てあげる: I do it for someone', 4, 45, 'てくれる てもらう てやる', 0),
   ('gv-tekureru', 'てくれる', '〜てくれる: someone does it for me', 4, 50, 'てあげる てもらう ていただく', 0),
   ('gv-temorau', 'てもらう', '〜てもらう: I have someone do it', 4, 50, 'てくれる てあげる てくださる', 0),
  ]),
  ('gv-polite', 'さしあげる・くださる・いただく', 'Polite and downward forms', [
   ('gv-sashiageru', 'さしあげる', 'さしあげる: giving to a superior', 3, 35, 'くださる いただく あげる', 0),
   ('gv-kudasaru', 'くださる', 'くださる: a superior gives to me', 3, 35, 'さしあげる いただく くれる', 0),
   ('gv-itadaku', 'いただく', 'いただく: receiving from a superior', 3, 35, 'くださる さしあげる もらう', 0),
   ('gv-yaru', 'やる', 'やる: giving to pets, plants, juniors', 4, 25, 'くれる もらう さしあげる', 0),
  ]),
  ('x-give', '授受', 'Giving and receiving mixed', [
   ('x-give', '授受', 'あげる / くれる / もらう: choose by direction', 4, 90, 'あげる くれる もらう', 0),
   ('x-give-te', '授受て', 'てあげる / てくれる / てもらう: choose by direction', 4, 80, 'てあげる てくれる てもらう', 0),
  ]),
 ]),
 ('trans', 'Transitive and intransitive pairs', 'It opens / I open it: two verbs, two particles.', [
  ('tr-pairs1', '自動詞・他動詞 I', 'Everyday pairs', [
   ('tr-aku', '開く・開ける', 'Doors, lights, switches (開く・開ける, 閉まる・閉める, つく・つける, 消える・消す)', 4, 70, '開ける 開く 開けられる', 1),
   ('tr-hajimaru', '始まる・始める', 'Start, stop, continue (始まる・始める, 終わる・終える, 止まる・止める, 続く・続ける)', 4, 70, '始める 始まる 始められる', 1),
   ('tr-hairu', '入る・入れる', 'In, out, up, down (入る・入れる, 出る・出す, 上がる・上げる, 下がる・下げる, 落ちる・落とす)', 4, 70, '入れる 入る 入られる', 1),
   ('tr-kowareru', '壊れる・壊す', 'Damage and repair (壊れる・壊す, 割れる・割る, 切れる・切る, 折れる・折る, 直る・直す, 汚れる・汚す)', 4, 70, '壊す 壊れる 壊される', 0),
  ]),
  ('tr-pairs2', '自動詞・他動詞 II', 'More pairs', [
   ('tr-kimaru', '決まる・決める', 'Decisions and change (決まる・決める, 変わる・変える, 集まる・集める, 見つかる・見つける, 伝わる・伝える)', 3, 60, '決める 決まる 決められる', 0),
   ('tr-narabu', '並ぶ・並べる', 'Placement and delivery (並ぶ・並べる, かかる・かける, 乗る・乗せる, 届く・届ける, 残る・残す, 渡る・渡す)', 3, 60, '並べる 並ぶ 並ばれる', 0),
   ('tr-okiru', '起きる・起こす', 'People and amounts (起きる・起こす, 育つ・育てる, 増える・増やす, 減る・減らす, 冷える・冷やす, 温まる・温める)', 3, 60, '起こす 起きる 起こされる', 0),
   ('tr-n2', '高まる・高める', 'N2 pairs (高まる・高める, 深まる・深める, 広がる・広げる, 済む・済ませる, 片付く・片付ける, 溶ける・溶かす)', 2, 50, '高める 高まる 高められる', 0),
  ]),
  ('tr-state', 'ている・てある', 'Resulting states', [
   ('tr-teiru-tearu', 'ている・てある', '窓が開いている vs 窓が開けてある', 4, 60, 'ている てある ておく', 0),
  ]),
  ('x-trans', '自他', 'Pairs mixed', [
   ('x-trans', '自他', 'Transitive or intransitive? Read the particle', 3, 100, '自動詞 他動詞', 0),
  ]),
 ]),
 ('keigo', 'Keigo', 'Raising the listener, lowering yourself.', [
  ('kg-son', '尊敬語', 'Honorific: the other person\'s actions', [
   ('kg-son-special', '尊敬語 (特別)', 'Special honorific verbs (いらっしゃる・おっしゃる・召し上がる・ご覧になる・なさる・ご存じ)', 3, 70, '参る 申す いただく', 0),
   ('kg-o-ninaru', 'お〜になる', 'お〜になる', 3, 50, 'お〜する 〜られる お〜いたす', 0),
   ('kg-rareru', '〜られる (尊敬)', '〜れる / 〜られる as an honorific', 3, 40, 'お〜する 〜させる お〜になる', 0),
   ('kg-o-kudasai', 'お〜ください', 'お〜ください / ご〜ください', 3, 40, 'お〜します お〜になります 〜てくれ', 0),
  ]),
  ('kg-ken', '謙譲語', 'Humble: my own actions', [
   ('kg-ken-special', '謙譲語 (特別)', 'Special humble verbs (参る・申す・いただく・拝見する・いたす・おる・伺う・存じる)', 3, 70, 'いらっしゃる おっしゃる 召し上がる', 0),
   ('kg-o-suru', 'お〜する', 'お〜する / ご〜する', 3, 50, 'お〜になる 〜られる お〜ください', 0),
   ('kg-sasete', 'させていただく', '〜させていただく', 3, 40, 'てくださる ていただく させてくださる', 0),
   ('kg-teitadaku', 'ていただく', '〜ていただく / 〜ていただけませんか', 3, 40, 'てくださる てさしあげる させていただく', 0),
  ]),
  ('kg-tei', '丁寧語', 'Polite words and set phrases', [
   ('kg-gozaimasu', 'ございます', 'ございます / でございます', 3, 35, 'いらっしゃいます おります あります', 0),
   ('kg-bika', 'お・ご', 'お or ご before a noun', 3, 35, 'お ご', 0),
   ('kg-set', '決まり文句', 'Set phrases at work and in shops', 3, 40, 'かしこまりました 恐れ入ります 少々お待ちください', 0),
  ]),
  ('x-keigo', '敬語', 'Keigo mixed', [
   ('x-keigo', '敬語', 'Honorific or humble? Whose action is it', 3, 100, '尊敬語 謙譲語', 0),
   ('x-keigo-biz', 'ビジネス敬語', 'Business keigo mixed', 2, 60, '尊敬語 謙譲語 丁寧語', 0),
  ]),
 ]),
 ('kosoado', 'こ・そ・あ・ど and question words', 'Pointing at things, and asking about them.', [
  ('ko-point', 'こ・そ・あ', 'This, that, that over there', [
   ('ko-kore', 'これ・それ・あれ', 'これ / それ / あれ', 5, 50, 'これ それ あれ どれ', 0),
   ('ko-kono', 'この・その・あの', 'この / その / あの + noun', 5, 45, 'これ この その あの', 0),
   ('ko-koko', 'ここ・そこ・あそこ', 'ここ / そこ / あそこ, こちら / そちら / あちら', 5, 45, 'ここ そこ あそこ どこ', 0),
   ('ko-konna', 'こんな・そう', 'こんな / そんな / あんな, こう / そう / ああ', 4, 45, 'こんな そんな あんな どんな', 0),
   ('ko-context', 'それ・あれ (文脈)', 'それ or あれ for things mentioned: shared or not', 3, 50, 'それ あれ これ', 0),
  ]),
  ('ko-q', '疑問詞', 'Question words', [
   ('ko-dore', 'どれ・どの・どちら', 'どれ / どの / どちら / どんな', 5, 50, 'どれ どの どちら どんな', 0),
   ('ko-nani', '何・誰・どこ・いつ', 'Which question word? 何・誰・どこ・いつ・どう・なぜ・いくら・いくつ', 5, 60, '何 誰 どこ いつ', 0),
   ('ko-ka', '何か・誰か', '何か / 誰か / どこか / いつか (some-)', 5, 40, '何も 何でも 何が', 0),
   ('ko-mo', '何も・誰も', '何も / 誰も / どこも + negative (no-)', 5, 40, '何か 何でも 何を', 0),
   ('ko-demo', '何でも・誰でも', '何でも / 誰でも / いつでも / どこでも (any-)', 4, 40, '何か 何も 何が', 0),
   ('x-ko-kamodemo', 'か・も・でも', '〜か / 〜も / 〜でも mixed', 4, 70, '何か 何も 何でも', 0),
  ]),
 ]),
 ('connect', 'Connectors', 'The word between two sentences that says how they relate.', [
  ('cn-basic', '接続詞 I', 'Everyday connectors', [
   ('cn-soshite', 'そして・それから', 'Addition and sequence (そして・それから・それに・その上)', 5, 50, 'しかし だから それとも', 0),
   ('cn-shikashi', 'でも・しかし', 'Contrast (でも・しかし・けれども・ところが)', 4, 50, 'だから そして つまり', 0),
   ('cn-dakara', 'だから・それで', 'Result (だから・それで・そのため)', 4, 45, 'しかし それに ところで', 0),
   ('cn-mataha', 'または・それとも', 'Alternatives (または・それとも・あるいは)', 4, 40, 'そして だから しかし', 0),
   ('cn-soredewa', 'それでは・ところで', 'Changing the subject (それでは・じゃ・ところで・さて)', 4, 40, 'だから しかし それに', 0),
  ]),
  ('cn-logic', '接続詞 II', 'Connectors of reasoning', [
   ('cn-nazenara', 'なぜなら・というのは', 'Giving the reason afterwards (なぜなら・というのは・だって)', 3, 40, 'だから すると ところが', 0),
   ('cn-sorenanoni', 'それなのに・それでも', 'Despite that (それなのに・それでも・にもかかわらず)', 3, 45, 'だから そのうえ つまり', 0),
   ('cn-suruto', 'すると・そこで', 'Then, so, in that case (すると・そこで・それなら)', 3, 45, 'しかし つまり または', 0),
   ('cn-tsumari', 'つまり・要するに', 'Restating (つまり・要するに・すなわち)', 3, 40, 'しかし すると ところで', 0),
   ('cn-tatoeba', 'たとえば・特に', 'Examples and emphasis (たとえば・特に・とりわけ)', 3, 35, 'つまり しかし それで', 0),
  ]),
  ('cn-formal', '接続詞 III', 'Formal connectors', [
   ('cn-tadashi', 'ただし・なお', 'Provisos and notes (ただし・ただ・もっとも・なお)', 2, 40, 'したがって つまり すると', 0),
   ('cn-shitagatte', 'したがって', 'Formal consequence (したがって・それゆえ・よって)', 2, 35, 'ただし ところが あるいは', 0),
  ]),
  ('x-connect', '接続', 'Connectors mixed', [
   ('x-connect', '接続', 'Choose the connector by the logic of the two sentences', 3, 120, 'しかし だから そして', 0),
  ]),
 ]),
 ('adverb', 'Adverbs that set up the ending', 'The adverb promises an ending; the ending must keep the promise.', [
  ('av-neg', '〜ない副詞', 'Adverbs that need a negative', [
   ('av-zenzen', '全然・あまり', '全然 / あまり / ちっとも / 決して + ない', 5, 50, 'とても よく きっと', 0),
   ('av-mettani', 'めったに・必ずしも', 'めったに / ろくに / 必ずしも / 一切 + ない', 3, 45, 'よく いつも きっと', 0),
   ('av-nakanaka', 'なかなか', 'なかなか + ない, and なかなか + praise', 4, 40, 'すぐ とても 全然', 0),
   ('av-masaka', 'まさか', 'まさか + ないだろう / とは', 3, 35, 'きっと ぜひ たぶん', 0),
  ]),
  ('av-modal', '陳述副詞', 'Adverbs of guessing, wishing, supposing', [
   ('av-kitto', 'きっと・たぶん', 'きっと / たぶん / おそらく + だろう / でしょう', 4, 45, 'ぜひ まさか 全然', 0),
   ('av-doumo', 'どうも・どうやら', 'どうも / どうやら + らしい / ようだ', 3, 40, 'ぜひ きっと もし', 0),
   ('av-zehi', 'ぜひ・どうか', 'ぜひ / どうか / どうぞ + たい / ください', 4, 40, 'たぶん まさか どうも', 0),
   ('av-moshi', 'もし・万一', 'もし / 万一 / 仮に + たら / ば / なら', 4, 40, 'たとえ まるで きっと', 0),
   ('av-tatoe', 'たとえ・いくら', 'たとえ / いくら / どんなに + ても', 3, 45, 'もし まるで きっと', 0),
   ('av-marude', 'まるで', 'まるで / あたかも + よう / みたい', 3, 40, 'たとえ もし どうも', 0),
   ('av-sekkaku', 'せっかく', 'せっかく + のに / のだから', 3, 35, 'わざわざ たとえ まさか', 0),
  ]),
  ('av-common', '程度・時間', 'Degree and time adverbs', [
   ('av-degree', 'とても・かなり', 'Degree (とても・かなり・ずいぶん・少し・ちょっと・あまり)', 5, 50, 'とても あまり 少し', 0),
   ('av-mou-mada', 'もう・まだ', 'もう or まだ', 5, 50, 'もう まだ また', 0),
   ('av-time', 'やっと・とうとう', 'Time (すぐ・やっと・とうとう・ついに・そろそろ・さっき・たまに)', 4, 60, 'やっと そろそろ さっき', 0),
  ]),
  ('x-adverb', '副詞', 'Adverbs mixed', [
   ('x-adverb', '副詞', 'Which adverb fits this ending?', 3, 90, 'きっと まさか たとえ', 0),
  ]),
 ]),
 ('ono', 'Sound and manner words', 'ぺらぺら, どきどき, ぐっすり: one word for a whole feeling.', [
  ('on-people', '擬態語 I', 'People', [
   ('on-feel', 'どきどき・わくわく', 'Feelings (どきどき・わくわく・いらいら・はらはら・がっかり・ほっと・うきうき・びっくり)', 3, 55, 'どきどき いらいら がっかり', 0),
   ('on-body', 'ぺこぺこ・くたくた', 'Body states (ぺこぺこ・からから・へとへと・くたくた・ふらふら・ぐっすり・うとうと)', 3, 50, 'ぺこぺこ くたくた ぐっすり', 0),
   ('on-talk', 'ぺらぺら・はっきり', 'Speech and manner (ぺらぺら・はっきり・ゆっくり・こっそり・のんびり・しっかり・うっかり・ぼんやり)', 3, 60, 'ぺらぺら こっそり うっかり', 0),
   ('on-laugh', 'にこにこ・しくしく', 'Laughing, crying, looking (にこにこ・げらげら・くすくす・しくしく・わんわん・じろじろ・きょろきょろ)', 3, 50, 'にこにこ げらげら じろじろ', 0),
   ('on-move', 'ぶらぶら・どんどん', 'Movement and pace (ぶらぶら・うろうろ・ばたばた・のろのろ・さっさと・どんどん・ぐんぐん・ぞろぞろ)', 3, 55, 'ぶらぶら のろのろ どんどん', 0),
  ]),
  ('on-things', '擬態語 II', 'Things', [
   ('on-weather', 'ざあざあ・ぴかぴか', 'Weather and light (ざあざあ・しとしと・ぽつぽつ・びゅうびゅう・ぴかぴか・きらきら・ごろごろ)', 3, 50, 'ざあざあ しとしと きらきら', 0),
   ('on-texture', 'ふわふわ・つるつる', 'Texture and food (ふわふわ・さらさら・べたべた・つるつる・ざらざら・ぬるぬる・ぱりぱり・もちもち)', 2, 50, 'ふわふわ べたべた ざらざら', 0),
   ('on-sound', 'とんとん・がたがた', 'Sounds (とんとん・がたがた・がちゃん・ばたん・ざわざわ・しいんと)', 2, 45, 'とんとん がたがた ざわざわ', 0),
   ('on-look', 'ぴったり・そっくり', 'Fit and amount (ぴったり・そっくり・ぎりぎり・ばらばら・めちゃくちゃ・ぎっしり・たっぷり・すっきり)', 3, 55, 'ぴったり ばらばら たっぷり', 0),
  ]),
  ('x-ono', '擬音語・擬態語', 'Sound and manner words mixed', [
   ('x-ono', '擬音語・擬態語', 'Which word fits the scene?', 3, 80, 'どきどき ぺらぺら ぴかぴか', 0),
  ]),
 ]),
 ('cond', 'Conditionals in depth', 'と, ば, たら, なら: four ways to say "if", each with its own limits.', [
  ('cd-four', 'と・ば・たら・なら', 'The four conditionals', [
   ('cd-to', '〜と', 'と: natural consequences, habits, discoveries', 4, 50, 'たら ば なら', 0),
   ('cd-ba', '〜ば', 'ば: general conditions, 〜ばいい, 〜ば〜ほど', 4, 50, 'と たら なら', 0),
   ('cd-tara', '〜たら', 'たら: one-off events, "once", discoveries, 〜たらどう', 4, 50, 'と ば なら', 0),
   ('cd-nara', '〜なら', 'なら: taking up what was said; advice', 4, 50, 'と ば たら', 0),
  ]),
  ('cd-more', '条件 II', 'Edges of the conditionals', [
   ('cd-volition', '意志と条件', 'A request or intention follows: which conditional is allowed?', 3, 60, 'と ば たら なら', 0),
   ('cd-regret', '〜ばよかった', 'Unreal conditions and regret (〜ば…のに, 〜ばよかった, 〜たらいいのに)', 3, 45, 'と なら ても', 0),
   ('cd-temo', '〜ても', 'ても / でも (even if) against たら', 4, 45, 'たら ば と', 0),
   ('cd-n2', '〜としたら・〜限り', 'としたら / とすれば / ものなら / ない限り', 2, 50, 'としたら ものなら ない限り', 0),
  ]),
  ('x-cond', '条件', 'Conditionals mixed', [
   ('x-cond', '条件', 'と / ば / たら / なら: choose by context', 3, 100, 'と ば たら なら', 0),
  ]),
 ]),
 ('pattern1', 'Sentence patterns I (N5 to N4)', 'What the end of the verb says: request, wish, plan, experience.', [
  ('pt-request', '依頼・許可・義務', 'Requests, permission, obligation', [
   ('pt-tekudasai', 'てください', '〜てください / 〜ないでください', 5, 45, 'てもいいです てはいけません ましょう', 1),
   ('pt-temoii', 'てもいい', '〜てもいい', 5, 40, 'てはいけない なくてもいい てください', 1),
   ('pt-tewaikenai', 'てはいけない', '〜てはいけない', 5, 40, 'てもいい なくてもいい なければならない', 1),
   ('pt-nakutemoii', 'なくてもいい', '〜なくてもいい', 5, 35, 'てはいけない なければならない てもいい', 0),
   ('pt-nakereba', 'なければならない', '〜なければならない / 〜なくてはいけない / 〜ないと', 5, 45, 'なくてもいい てはいけない てもいい', 1),
   ('pt-mashou', 'ましょう・ませんか', '〜ましょう / 〜ませんか / 〜ましょうか', 5, 40, 'てください たいです ています', 1),
  ]),
  ('pt-desire', '希望・意志・予定', 'Wishes, intentions, plans', [
   ('pt-tai', 'たい', '〜たい / 〜たがる', 5, 40, 'ほしい つもり ましょう', 1),
   ('pt-hoshii', 'ほしい・てほしい', '〜がほしい / 〜てほしい', 4, 40, 'たい てもらう てあげる', 0),
   ('pt-tsumori', 'つもり', '〜つもりだ', 4, 40, '予定 はず たい', 1),
   ('pt-youtoomou', '〜ようと思う', 'Volitional + と思う / 〜ようとする', 4, 45, 'つもり たい そうだ', 0),
   ('pt-kotonisuru', 'ことにする・ことになる', '〜ことにする / 〜ことになる / 〜予定だ', 4, 50, 'ことがある ようにする ようになる', 0),
  ]),
  ('pt-aspect', '経験・状態・完了', 'Experience, state, completion', [
   ('pt-takotogaaru', 'たことがある', '〜たことがある', 5, 40, 'ことができる ことにする たほうがいい', 1),
   ('pt-teiru', 'ている', '〜ている: in progress, resulting state, habit', 5, 50, 'てある ておく た', 1),
   ('pt-teshimau', 'てしまう', '〜てしまう / 〜ちゃう', 4, 40, 'ておく てみる てある', 0),
   ('pt-teoku', 'ておく', '〜ておく', 4, 40, 'てしまう てみる てある', 0),
   ('pt-temiru', 'てみる', '〜てみる', 4, 35, 'ておく てしまう てくる', 0),
   ('pt-tekuru', 'てくる・ていく', '〜てくる / 〜ていく', 3, 45, 'てみる ておく てしまう', 0),
   ('pt-tokoro', 'ところ・ばかり', '〜るところ / 〜ているところ / 〜たところ / 〜たばかり', 4, 55, 'るところ ているところ たところ', 0),
   ('pt-hajimeru', '〜始める・〜続ける', '〜始める / 〜出す / 〜続ける / 〜終わる', 4, 45, '始める 出す 続ける 終わる', 0),
  ]),
  ('pt-ability', '可能・変化・程度', 'Ability, change, degree', [
   ('pt-dekiru', 'ことができる', '〜ことができる / potential form', 4, 40, 'ことがある ことにする ようになる', 1),
   ('pt-youninaru', 'ようになる・ようにする', '〜ようになる / 〜ようにする', 4, 50, 'ことになる ことにする ことができる', 0),
   ('pt-yasui', 'やすい・にくい', '〜やすい / 〜にくい', 4, 35, 'やすい にくい すぎる', 0),
   ('pt-sugiru', 'すぎる', '〜すぎる', 4, 35, 'やすい にくい たがる', 0),
   ('pt-kata', '〜方', '〜方: the way of doing', 5, 30, 'こと もの ところ', 0),
  ]),
  ('pt-advice', '助言・命令', 'Advice and commands', [
   ('pt-hougaii', 'たほうがいい', '〜たほうがいい / 〜ないほうがいい', 4, 40, 'てもいい たことがある なければならない', 1),
   ('pt-tarado', 'たらどう・といい', '〜たらどうですか / 〜といい / 〜ばいい', 4, 35, 'たほうがいい てもいい てください', 0),
   ('pt-nasai', 'なさい・命令形', '〜なさい / command forms / 〜な (don\'t)', 4, 45, 'てください ましょう てもいい', 0),
   ('pt-beki', 'べき', '〜べきだ / 〜べきではない', 3, 40, 'はず わけ つもり', 0),
  ]),
  ('pt-time', '時間', 'Time clauses', [
   ('pt-maeni', '前に・後で・てから', '〜前に / 〜た後で / 〜てから', 5, 50, '前に 後で てから', 1),
   ('pt-toki', '〜とき', '〜るとき or 〜たとき', 4, 45, 'るとき たとき ているとき', 0),
   ('pt-aida', '間・間に・うちに', '〜間 / 〜間に / 〜うちに', 3, 50, '間 間に うちに', 0),
   ('pt-tabini', 'たびに・ついでに', '〜たびに / 〜ついでに / 〜最中に', 3, 45, 'たびに ついでに 最中に', 0),
   ('pt-totan', 'たとたん・次第', '〜たとたん / 〜かと思うと / 〜次第', 2, 45, 'たとたん 次第 うちに', 0),
  ]),
 ]),
 ('pattern2', 'Sentence patterns II (N4 to N2)', 'Guessing, explaining, comparing, and the patterns of N3 and N2.', [
  ('pt-conject', '推量・伝聞', 'Seeming, hearsay, likelihood', [
   ('pt-sou-look', 'そうだ (様態)', '〜そうだ: looks as if', 4, 45, 'ようだ らしい そうだ(伝聞)', 0),
   ('pt-sou-hear', 'そうだ (伝聞)', '〜そうだ: I hear that', 4, 40, 'ようだ らしい そうだ(様態)', 0),
   ('pt-youda', 'ようだ・みたいだ', '〜ようだ / 〜みたいだ', 4, 45, 'そうだ らしい はずだ', 0),
   ('pt-rashii', 'らしい', '〜らしい: hearsay-based guess, and "typical of"', 4, 40, 'そうだ ようだ みたいだ', 0),
   ('pt-deshou', 'でしょう・かもしれない', '〜でしょう / 〜だろう / 〜かもしれない', 4, 50, 'はずだ らしい そうだ', 0),
   ('pt-hazu', 'はずだ', '〜はずだ / 〜はずがない', 4, 45, 'べきだ わけだ つもりだ', 0),
   ('pt-nichigainai', 'に違いない', '〜に違いない / 〜に決まっている', 3, 40, 'かもしれない はずがない わけがない', 0),
   ('x-pt-conject', '推量', 'そう / よう / らしい / みたい mixed', 3, 80, 'そうだ ようだ らしい みたいだ', 0),
  ]),
  ('pt-explain', '説明', 'Explaining and concluding', [
   ('pt-nda', 'んです', '〜んです / 〜のだ', 4, 45, 'です でしょう そうです', 0),
   ('pt-wake', 'わけ', '〜わけだ / 〜わけがない / 〜わけではない / 〜わけにはいかない', 3, 70, 'わけだ わけがない わけではない わけにはいかない', 0),
   ('pt-mono', 'ものだ', '〜ものだ / 〜ものではない / 〜もの (because)', 3, 50, 'ことだ わけだ はずだ', 0),
   ('pt-koto', 'ことだ', '〜ことだ / 〜ことはない / 〜ということだ', 3, 50, 'ものだ わけだ はずだ', 0),
   ('x-pt-wake', 'わけ・はず・もの・こと', 'わけ / はず / もの / こと mixed', 2, 70, 'わけだ はずだ ものだ ことだ', 0),
  ]),
  ('pt-purpose', '目的・原因', 'Purpose and cause', [
   ('pt-tame', 'ために', '〜ために: purpose, and cause', 4, 45, 'ように のに には', 0),
   ('pt-youni', 'ように', '〜ように (so that) against 〜ために', 4, 50, 'ために のに には', 0),
   ('pt-okagede', 'おかげで・せいで', '〜おかげで / 〜せいで / 〜ばかりに', 3, 45, 'おかげで せいで ために', 0),
   ('pt-kuseni', 'くせに・わりに', '〜くせに / 〜わりに / 〜にしては', 3, 45, 'くせに わりに にしては', 0),
  ]),
  ('pt-nominal', '名詞化・引用・比較', 'Nominalising, quoting, comparing', [
   ('pt-no-koto', 'の・こと', 'の or こと to turn a clause into a noun', 4, 50, 'の こと もの', 0),
   ('pt-kadouka', 'かどうか', '〜かどうか / questions inside a sentence', 4, 40, 'かどうか か と', 0),
   ('pt-quote', 'と言う・ように言う', '〜と言う / 〜と思う / 〜ように言う', 4, 45, 'と ように ことを', 0),
   ('pt-toiu', 'という', '〜という + noun / 〜というのは / 〜といっても', 3, 45, 'という というのは といっても', 0),
   ('pt-hikaku', 'より・ほど・一番', 'AよりBのほうが / AほどBない / 〜の中で一番', 4, 55, 'より ほど 一番', 0),
  ]),
  ('pt-voice', '受身・使役', 'Passive and causative forms', [
   ('pt-passive', '受身', 'Passive, including the "it happened to me" passive', 4, 50, '使役 可能 使役受身', 0),
   ('pt-causative', '使役・使役受身', 'Causative and causative-passive', 3, 55, '受身 可能 使役受身', 0),
   ('pt-sasete', 'させてください', '〜させてください / 〜させてもらう', 3, 35, 'てください させられる てもらう', 0),
   ('pt-zuni', 'ないで・なくて・ずに', '〜ないで / 〜なくて / 〜ずに', 3, 50, 'ないで なくて ずに', 0),
  ]),
  ('pt-n3', 'N3〜N2 文型 I', 'Tendency, extent, inevitability', [
   ('pt-gachi', 'がち・気味・っぽい', '〜がち / 〜気味 / 〜っぽい / 〜だらけ', 3, 50, 'がち 気味 っぽい だらけ', 0),
   ('pt-kiru', 'きる・かけ・っぱなし', '〜きる / 〜かけ / 〜っぱなし / 〜ぬく', 2, 50, 'きる かけ っぱなし ぬく', 0),
   ('pt-ippou', '一方だ・つつある', '〜一方だ / 〜つつある / 〜ばかりだ', 2, 45, '一方だ つつある ばかりだ', 0),
   ('pt-zaruwoenai', 'ざるを得ない', '〜ざるを得ない / 〜ないわけにはいかない / 〜ずにはいられない', 2, 50, 'ざるを得ない ずにはいられない わけにはいかない', 0),
   ('pt-kanenai', 'かねない・かねる', '〜かねない / 〜かねる / 〜得る / 〜がたい', 2, 50, 'かねない かねる 得る がたい', 0),
  ]),
  ('pt-n2', 'N3〜N2 文型 II', 'Concession and impossibility', [
   ('pt-toshitemo', 'としても・にしても', '〜としても / 〜にしても / 〜にせよ', 2, 45, 'としても にしては としたら', 0),
   ('pt-younai', 'ようがない・っこない', '〜ようがない / 〜っこない / 〜わけがない', 2, 45, 'ようがない っこない かねない', 0),
   ('pt-bayokatta', 'ばよかった・てよかった', '〜ばよかった / 〜てよかった / 〜なければよかった', 3, 40, 'ばよかった てよかった たらいい', 0),
   ('pt-dokoroka', 'どころか・ばかりか', '〜どころか / 〜ばかりか / 〜はもちろん', 2, 45, 'どころか ばかりか はもちろん', 0),
  ]),
 ]),
 ('yomi', 'Kanji readings in context', 'One kanji, several readings: the word decides.', [
  ('ym-n5', '読み N5', 'First kanji', [
   ('ym-n5-days', '日・月・火・水・木・金・土', '日・月・火・水・木・金・土 in words (日曜日, 三日, 毎日, 今月, 月曜日, 水道, お金)', 5, 50, 'にち ひ か', 0, R),
   ('ym-n5-size', '人・大・小・中・上・下', '人・大・小・中・上・下 (大人, 一人, 三人, 大きい, 大学, 上手, 上がる, 一日中)', 5, 55, 'じん にん ひと', 0, R),
   ('ym-n5-move', '生・行・来・出・入・分', '生・行・来・出・入・分 (生まれる, 学生, 行く, 行う, 来月, 出す, 入口, 五分, 自分)', 5, 55, 'せい なま い', 0, R),
   ('ym-n5-time', '今・何・年・時・間・後・前', '今・何・年・時・間・後・前 (今年, 今朝, 何人, 何曜日, 時々, 時間, 人間, 後ろ, 午後)', 5, 55, 'いま こん なん', 0, R),
  ]),
  ('ym-special', '特別な読み', 'Special readings', [
   ('ym-jukuji', '熟字訓', 'Whole-word readings (今日・明日・昨日・大人・一人・二人・二十歳・上手・下手・果物・部屋・時計)', 4, 60, 'こんにち みょうにち おとな', 0, R),
   ('ym-onkun', '音読み・訓読み', 'On or kun? Alone against in a compound (山・登山, 水・水道, 車・電車, 花・花火)', 4, 55, 'さん やま すい', 0, R),
   ('ym-rendaku', '連濁・促音', 'Sound changes in compounds (手紙, 時々, 青空, 学校, 発表, 出発, 雑誌)', 3, 50, 'てかみ ときとき がくこう', 0, R),
  ]),
  ('ym-n4', '読み N4〜N3', 'More readings', [
   ('ym-n4-a', '明・通・開・着・重・楽', '明・通・開・着・重・楽 (明るい, 明日, 説明, 通る, 通う, 交通, 着る, 着く, 重い, 体重, 楽しい, 音楽)', 4, 55, 'めい あか つう', 0, R),
   ('ym-n4-b', '物・事・方・家・場・所', '物・事・方・家・場・所 (食べ物, 荷物, 動物, 仕事, 食事, 夕方, 方法, 家族, 大家, 場所, 台所)', 4, 55, 'もの ぶつ もつ', 0, R),
   ('ym-n3-a', '直・降・空・苦・治・止', '直・降・空・苦・治・止 (直す, 正直, 降りる, 降る, 空, 空く, 空気, 苦い, 苦しい, 治る, 政治)', 3, 55, 'なお ちょく じき', 0, R),
   ('ym-n3-b', '代・風・手・目・角・背', '代・風・手・目・角・背 (時代, 代わり, 風邪, 和風, 選手, 手伝う, 目的, 三角, 角, 背中)', 3, 50, 'だい か しろ', 0, R),
   ('ym-n2', 'N2 の読み', 'N2 words that are often misread (大勢, 行方, 相手, 場合, 手続き, 合図, 見本, 日付, 割合)', 2, 50, 'たいせい こうほう あいて', 0, R),
  ]),
  ('x-yomi', '読み', 'Readings mixed', [
   ('x-yomi', '読み', 'Read the word in its sentence', 3, 80, 'にち ひ か', 0, R),
  ]),
 ]),
 ('nita', 'Look-alike kanji and spelling', 'Kanji that differ by a stroke, words that sound the same.', [
  ('nt-shape', '似ている漢字', 'Similar shapes', [
   ('nt-n5', '待・持・特', 'First look-alikes (待・持・特, 大・太・犬, 右・石, 木・本, 人・入, 千・干, 土・士)', 5, 45, '持 特 侍', 0, K),
   ('nt-n4-a', '買・貸・借', '買・貸・質, 牛・午, 鳥・島, 末・未, 白・百・自, 体・休', 4, 45, '貸 質 貨', 0, K),
   ('nt-n4-b', '住・注・主', '住・往・注・主, 送・迷・逃, 開・閉・間・聞・問・関', 4, 50, '注 往 主', 0, K),
   ('nt-n3-a', '復・複・腹', '復・複・腹, 験・検・険, 績・積・責, 適・敵・滴', 3, 50, '複 腹 複', 0, K),
   ('nt-n3-b', '微・徴', '微・徴, 緑・録・縁, 幸・辛, 困・因, 輸・輪, 墓・暮・募・幕', 3, 50, '徴 微 緑', 0, K),
  ]),
  ('nt-spell', '同音・送り仮名', 'Same sound, and okurigana', [
   ('nt-homophone', '会う・合う', 'Same sound, different kanji (会う・合う, 暑い・熱い・厚い, 早い・速い, 聞く・効く, 着る・切る, 帰る・変える)', 3, 60, '合う 遭う 逢う', 0, K),
   ('nt-okurigana', '送り仮名', 'Okurigana (少ない・少し, 細い・細かい, 行う, 短い, 新しい, 冷たい・冷える・冷やす)', 3, 50, '少い 少ない 少くない', 0, K),
  ]),
  ('x-nita', '似た漢字', 'Look-alikes mixed', [
   ('x-nita', '似た漢字', 'Choose the right kanji for the word', 3, 60, '持 待 特', 0, K),
  ]),
 ]),
]

# Added 2026-11-28 (owner: "build all for Chinese and Japanese"). Built on their
# own target so the first twelve stages keep the counts they were authored to.
MORE_TARGET = 2000
MORE_STAGES = [
 ('colloc', 'Collocations', 'Which verb goes with which noun: the pairs English gets wrong.', [
  ('cl-daily', '日常の組み合わせ', 'Everyday pairs', [
   ('cl-wear', '着る・履く・かぶる', 'Wearing: 着る, 履く, かぶる, かける, する, つける (服, 靴, 帽子, 眼鏡, ネクタイ, 指輪)', 5, 50, '着る 履く かぶる かける', 0),
   ('cl-take', '飲む・浴びる・撮る', 'Not "take": 薬を飲む, シャワーを浴びる, 写真を撮る, 電話をかける, 風邪を引く, 試験を受ける', 5, 55, '取る 飲む 浴びる 撮る', 0),
   ('cl-play', '弾く・吹く・する', 'Not "play": ピアノを弾く, 笛を吹く, 太鼓をたたく, サッカーをする, ゲームをする', 5, 45, '弾く 吹く する 遊ぶ', 0),
   ('cl-weather', '降る・吹く・鳴る', 'Weather and nature: 雨が降る, 風が吹く, 雷が鳴る, 日が暮れる, 霧が出る, 花が咲く', 4, 45, '降る 吹く 鳴る 出る', 0),
   ('cl-life', '入る・出る・取る', 'Life events: お風呂に入る, 大学を出る, 年を取る, 休みを取る, 約束を守る, 予約を入れる', 4, 50, '入る 出る 取る 守る', 0),
  ]),
  ('cl-verbs', '多義の動詞', 'One verb, many partners', [
   ('cl-kakeru', 'かける', 'かける: 電話, 眼鏡, 鍵, 時間, 迷惑, 声, 音楽, 塩', 4, 55, 'つける する 取る 出す', 0),
   ('cl-tsukeru', 'つける', 'つける: 電気, 名前, 気, 味, 日記, 薬, 力', 4, 50, 'かける する 入れる 出す', 0),
   ('cl-dasu', '出す', '出す: 手紙, 宿題, 声, 元気, 結論, ごみ, お金', 4, 50, '送る 上げる かける つける', 0),
   ('cl-toru', '取る', '取る: 年, 休み, 連絡, 責任, 点, メモ, 予約, 食事', 3, 50, 'する 持つ かける 出す', 0),
   ('cl-hiku', '引く', '引く: 風邪, 辞書, 線, 興味, 手, くじ', 3, 40, '取る かける 見る する', 0),
  ]),
  ('cl-sense', '〜がする・形容詞', 'Senses and adjectives', [
   ('cl-gasuru', '〜がする', '〜がする: 音, 声, 味, 匂い, 香り, 気, 感じ, 頭痛, 寒気', 4, 50, 'がある がいる をする になる', 0),
   ('cl-adj', '濃い・薄い・強い', 'Adjective partners: 濃い / 薄い (味, 色, お茶), 強い / 弱い (風, 酒), 重い / 軽い (病気, 責任), 高い / 低い (声, 熱), 激しい (雨, 運動)', 3, 55, '濃い 強い 重い 高い', 0),
  ]),
  ('x-colloc', '連語', 'Collocations mixed', [
   ('x-colloc', '連語', 'Choose the verb this noun takes', 4, 90, 'する 取る かける 出す', 0),
  ]),
 ]),
 ('idiom', 'Idioms', '気 and body-part expressions, and four-character idioms.', [
  ('id-ki', '気', '気 expressions', [
   ('id-ki1', '気がする・気になる', '気がする, 気になる, 気にする, 気をつける, 気がつく, 気に入る, 気が合う', 3, 70, '気がする 気になる 気にする 気をつける', 0),
   ('id-ki2', '気が重い・気を遣う', '気が重い, 気が短い, 気が利く, 気が散る, 気が済む, 気を遣う, 気が向く, 気が楽', 2, 60, '気が重い 気が利く 気が散る 気を遣う', 0),
  ]),
  ('id-body', '体の慣用句', 'Body-part idioms', [
   ('id-head', '頭・顔・目・耳・口・鼻', 'Head: 頭に来る, 頭が固い, 顔が広い, 顔を出す, 目がない, 目を通す, 耳が痛い, 口が堅い, 口に合う, 鼻が高い', 2, 65, '頭に来る 顔が広い 目がない 口が堅い', 0),
   ('id-hand', '手・足・腹・腕・首・胸', 'Body: 手を貸す, 手が空く, 手に入れる, 足を引っ張る, 足が出る, 腹が立つ, 腕がいい, 首になる, 胸がいっぱい, 肩を持つ', 2, 65, '手を貸す 腹が立つ 首になる 足を引っ張る', 0),
  ]),
  ('id-yoji', '四字熟語', 'Four-character idioms', [
   ('id-yoji1', '四字熟語', 'Common ones: 一生懸命, 一石二鳥, 十人十色, 一期一会, 自業自得, 四苦八苦, 以心伝心, 三日坊主, 半信半疑, 試行錯誤', 2, 65, '一石二鳥 十人十色 自業自得 三日坊主', 0),
  ]),
  ('x-idiom', '慣用句', 'Idioms mixed', [
   ('x-idiom', '慣用句', 'Which expression fits the situation?', 2, 80, '気になる 腹が立つ 一石二鳥 手を貸す', 0),
  ]),
 ]),
 ('casual', 'Casual contractions', 'What spoken Japanese does to the textbook forms.', [
  ('cs-verb', '縮約形 I', 'Verb endings', [
   ('cs-teru', '〜てる・〜とく', '〜ている → 〜てる, 〜ておく → 〜とく, 〜でいる → 〜でる, 〜でおく → 〜どく', 4, 55, 'てる とく でる どく', 0),
   ('cs-chau', '〜ちゃう・〜じゃう', '〜てしまう → 〜ちゃう, 〜でしまう → 〜じゃう, 〜ちゃった, 〜じゃった', 4, 55, 'ちゃう じゃう ちゃった とく', 0),
   ('cs-nakya', '〜なきゃ・〜なくちゃ', '〜なければ → 〜なきゃ, 〜なくては → 〜なくちゃ, 〜ては → 〜ちゃ, 〜では → 〜じゃ', 4, 50, 'なきゃ なくちゃ ちゃ じゃ', 0),
  ]),
  ('cs-end', '縮約形 II', 'Sentence endings and quoting', [
   ('cs-nda', '〜んだ・〜の', '〜のだ → 〜んだ, 〜のです → 〜んです, questions with 〜の？, 〜もの → 〜もん', 4, 50, 'んだ の もん んです', 0),
   ('cs-tte', '〜って・〜っけ', '〜と / 〜という / 〜は → 〜って, 〜っけ, 〜じゃん, 〜かな', 3, 55, 'って っけ じゃん かな', 0),
   ('cs-sound', '音の変化', 'Sound changes: すみません → すいません, 〜ところ → 〜とこ, やはり → やっぱり, あまり → あんまり, 〜らない → 〜んない', 3, 45, 'とこ やっぱり あんまり すいません', 0),
  ]),
  ('x-casual', '話し言葉', 'Contractions mixed', [
   ('x-casual', '話し言葉', 'Full form and spoken form: match them', 3, 80, 'てる ちゃう なきゃ って', 0),
  ]),
 ]),
 ('compound', 'Compound verbs', 'A second verb on the stem changes direction, degree or completion.', [
  ('cv-dir', '複合動詞 I', 'Direction', [
   ('cv-komu', '〜込む', '〜込む: into, deeply (飛び込む, 申し込む, 思い込む, 持ち込む, 落ち込む)', 3, 55, '出す 上げる 切る 合う', 0),
   ('cv-dasu', '〜出す', '〜出す: out, and suddenly starting (取り出す, 思い出す, 飛び出す, 泣き出す, 走り出す)', 3, 55, '込む 上げる 切る 始める', 0),
   ('cv-ageru', '〜上げる・〜上がる', '〜上げる / 〜上がる: up, completely (持ち上げる, 立ち上がる, 仕上げる, 出来上がる, 取り上げる)', 3, 50, '込む 出す 下げる 切る', 0),
  ]),
  ('cv-deg', '複合動詞 II', 'Completion and repetition', [
   ('cv-kiru', '〜切る・〜切れる', '〜切る / 〜切れる: to the end, cannot finish (使い切る, 食べ切れない, 疲れ切る, 言い切る)', 2, 50, '込む 出す 終わる 過ぎる', 0),
   ('cv-au', '〜合う', '〜合う: each other (話し合う, 助け合う, 知り合う, 付き合う, 間に合う)', 3, 50, '込む 出す 切る 直す', 0),
   ('cv-naosu', '〜直す・〜返す', '〜直す / 〜返す: again, back (やり直す, 書き直す, 考え直す, 繰り返す, 言い返す, 取り返す)', 3, 50, '切る 合う 出す 込む', 0),
   ('cv-kakeru', '〜かける・〜かかる', '〜かける / 〜かかる: towards, about to (話しかける, 出かける, 通りかかる, 取りかかる, 言いかける)', 2, 45, '込む 出す 合う 切る', 0),
  ]),
  ('x-compound', '複合動詞', 'Compound verbs mixed', [
   ('x-compound', '複合動詞', 'Which second verb completes it?', 3, 80, '込む 出す 切る 合う', 0),
  ]),
 ]),
 ('gairaigo', 'Loanword traps', 'Katakana words that do not mean what the English word means.', [
  ('gr-traps', '外来語', 'False friends and made-in-Japan English', [
   ('gr-false', '意味のずれ', 'False friends: マンション, バイキング, サービス, クレーム, スマート, テンション, ナイーブ, カンニング, トランプ, ジュース', 3, 65, 'マンション サービス クレーム スマート', 0),
   ('gr-wasei', '和製英語', 'Made-in-Japan English: サラリーマン, コンセント, ノートパソコン, ガソリンスタンド, フロント, レンジ, ホッチキス, ペーパードライバー', 3, 60, 'コンセント フロント レンジ サラリーマン', 0),
   ('gr-short', '略語', 'Shortened words: コンビニ, パソコン, スマホ, リモコン, エアコン, アプリ, バイト, デパート, アニメ', 4, 55, 'コンビニ パソコン リモコン エアコン', 0),
  ]),
  ('x-gairaigo', 'カタカナ語', 'Loanwords mixed', [
   ('x-gairaigo', 'カタカナ語', 'Which katakana word is meant?', 3, 60, 'マンション コンセント コンビニ サービス', 0),
  ]),
 ]),
]

# Skills that get endless pattern packs (2 each) beyond the 18 of the first run.
MORE_PACKS = 2
MORE_PACK_SKILLS = '''
 gv-teageru gv-tekureru gv-temorau gv-sashiageru gv-kudasaru gv-itadaku gv-yaru
 tr-kowareru tr-kimaru tr-narabu tr-okiru tr-teiru-tearu
 kg-o-ninaru kg-o-suru kg-o-kudasai kg-sasete kg-teitadaku
 ko-kore ko-kono ko-koko ko-ka ko-mo ko-demo
 cd-to cd-ba cd-tara cd-nara cd-temo cd-regret
 pt-nakutemoii pt-hoshii pt-youtoomou pt-kotonisuru pt-teshimau pt-teoku pt-temiru pt-tekuru
 pt-tokoro pt-hajimeru pt-youninaru pt-yasui pt-sugiru pt-kata pt-tarado pt-nasai pt-beki
 pt-toki pt-aida
 pt-sou-look pt-sou-hear pt-youda pt-rashii pt-deshou pt-hazu pt-nichigainai
 pt-nda pt-tame pt-youni pt-okagede pt-no-koto pt-kadouka pt-quote pt-hikaku
 pt-passive pt-causative pt-sasete pt-zuni pt-bayokatta
 av-zenzen av-mou-mada av-kitto av-moshi
 cl-wear cl-take cl-play cl-weather cl-gasuru
 cs-teru cs-chau cs-nakya
'''.split()


def build_catalog():
    """The whole grammar catalog: the first twelve stages on their own target,
    then the stages added later on theirs."""
    cat, total = base.build(STAGES, TARGET_TOTAL)
    more, more_total = base.build(MORE_STAGES, MORE_TARGET)
    cat['stages'] += more['stages']
    cat['skills'] += more['skills']
    ids = [s['id'] for s in cat['skills']]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    by_id = {s['id']: s for s in cat['skills']}
    for sid in MORE_PACK_SKILLS:
        assert sid in by_id, sid
        if not by_id[sid]['packs']:
            by_id[sid]['packs'] = MORE_PACKS
    cat['course'] = 'grammar'
    return cat, total + more_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='write catalog.json')
    args = ap.parse_args()
    cat, total = build_catalog()
    print(f"stages {len(cat['stages'])}  groups {sum(len(s['groups']) for s in cat['stages'])}  "
          f"skills {len(cat['skills'])}  items {total}  packs {sum(s['packs'] for s in cat['skills'])}")
    if args.apply:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, 'w', encoding='utf-8') as fh:
            json.dump(cat, fh, ensure_ascii=False, indent=1)
        print('wrote', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
