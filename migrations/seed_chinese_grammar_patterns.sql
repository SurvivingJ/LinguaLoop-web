-- Seed 15 Chinese grammar patterns for exercise generation
-- language_id = 1 (Chinese), spread across A1–B2 and 7 categories

INSERT INTO dim_grammar_patterns
  (pattern_code, pattern_name, description, user_facing_description,
   example_sentence, example_sentence_en, language_id, cefr_level, category)
VALUES
  ('cn_ba_construction', '把 Construction',
   'The 把 construction moves the object before the verb to emphasise the action done to it. Structure: Subject + 把 + Object + Verb + Complement.',
   'Using 把 to show what happens to something',
   '我把书放在桌子上了。', 'I put the book on the table.', 1, 'A2', 'word_order'),

  ('cn_bei_passive', '被 Passive',
   'The 被 construction marks the passive voice. Structure: Subject + 被 + (Agent) + Verb.',
   'Using 被 to say something was done to the subject',
   '我的手机被偷了。', 'My phone was stolen.', 1, 'B1', 'voice'),

  ('cn_le_completed', '了 Completed Action',
   'The particle 了 after a verb indicates completed action. Structure: Subject + Verb + 了 + Object.',
   'Using 了 to show an action is completed',
   '我吃了早饭。', 'I ate breakfast.', 1, 'A1', 'aspect'),

  ('cn_guo_experience', '过 Experiential',
   'The particle 过 after a verb indicates past experience. Structure: Subject + Verb + 过 + Object.',
   'Using 过 to talk about past experiences',
   '我去过中国。', 'I have been to China.', 1, 'A2', 'aspect'),

  ('cn_zhe_continuous', '着 Continuous',
   'The particle 着 after a verb indicates a continuous or ongoing state. Structure: Verb + 着.',
   'Using 着 to describe an ongoing state',
   '门开着。', 'The door is open.', 1, 'B1', 'aspect'),

  ('cn_de_complement', '得 Complement',
   'The particle 得 links a verb to a degree/result complement. Structure: Verb + 得 + Complement.',
   'Using 得 to describe how well something is done',
   '她说得很好。', 'She speaks very well.', 1, 'B1', 'complement'),

  ('cn_shi_de_cleft', '是…的 Cleft',
   'The 是…的 construction emphasises the time, place, or manner of a past action. Structure: 是 + Detail + Verb + 的.',
   'Using 是…的 to emphasise when, where, or how something happened',
   '我是昨天来的。', 'I came yesterday (emphasis on when).', 1, 'B1', 'clause_structure'),

  ('cn_bi_comparative', '比 Comparative',
   'The 比 construction compares two things. Structure: A + 比 + B + Adjective.',
   'Using 比 to compare two things',
   '他比我高。', 'He is taller than me.', 1, 'A2', 'word_order'),

  ('cn_lian_dou_emphasis', '连…都/也 Emphasis',
   'The 连…都/也 construction emphasises an extreme case. Structure: 连 + Noun/Verb + 都/也 + Verb.',
   'Using 连…都/也 to emphasise that even something extreme applies',
   '他连饭都没吃。', 'He didn''t even eat.', 1, 'B2', 'word_order'),

  ('cn_measure_word_ge', '个 General Measure Word',
   'The measure word 个 is the most common classifier used between a number/demonstrative and a noun. Structure: Number + 个 + Noun.',
   'Using 个 as a general measure word for counting',
   '我有三个朋友。', 'I have three friends.', 1, 'A1', 'measure_words'),

  ('cn_neng_hui_keyi', '能/会/可以 Modal Verbs',
   'Chinese uses different modal verbs for ability (能/会) and permission (可以). Each has distinct usage contexts.',
   'Choosing between 能, 会, and 可以 for ability and permission',
   '我会说中文。', 'I can speak Chinese.', 1, 'A2', 'modality'),

  ('cn_yao_intention', '要 Intention/Desire',
   'The word 要 expresses wanting, needing, or future intention. Structure: Subject + 要 + Verb/Object.',
   'Using 要 to express wanting or going to do something',
   '我要去北京。', 'I want to go to Beijing.', 1, 'A1', 'modality'),

  ('cn_ruguo_conditional', '如果…就 Conditional',
   'The 如果…就 construction expresses conditional "if…then" relationships. Structure: 如果 + Condition, 就 + Result.',
   'Using 如果…就 to express if-then conditions',
   '如果明天下雨，我就不去了。', 'If it rains tomorrow, I won''t go.', 1, 'B1', 'clause_structure'),

  ('cn_yinwei_suoyi_cause', '因为…所以 Cause-Effect',
   'The 因为…所以 construction links cause and effect. Structure: 因为 + Reason, 所以 + Result.',
   'Using 因为…所以 to explain cause and effect',
   '因为今天很冷，所以我穿了外套。', 'Because it''s cold today, I wore a jacket.', 1, 'B2', 'clause_structure'),

  ('cn_bu_shi_er_shi_contrast', '不是…而是 Contrast',
   'The 不是…而是 construction negates one thing and asserts another. Structure: 不是 + A + 而是 + B.',
   'Using 不是…而是 to contrast what something is not vs. what it is',
   '他不是老师，而是学生。', 'He is not a teacher, but rather a student.', 1, 'B2', 'clause_structure');
