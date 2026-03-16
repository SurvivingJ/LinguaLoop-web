"""
Per-language stoplists for collocation quality filtering.
Used by CollocationClassifier.is_valid_collocation().
"""

# ── English (language_id = 2) ────────────────────────────────

EN_QUOTE_ANCHORS: frozenset = frozenset({
    'said', 'says', 'say', 'replied', 'answered', 'asked', 'added',
    'continued', 'explained', 'remarked', 'noted', 'observed',
    'exclaimed', 'muttered', 'whispered', 'shouted', 'cried',
})

# ── Chinese (language_id = 1) ────────────────────────────────

ZH_QUOTE_ANCHORS: frozenset = frozenset({
    '说道', '说', '道', '说着', '答道', '问道', '回答', '表示',
    '认为', '指出', '强调', '称', '写道', '喊道', '叫道',
    '回道', '答', '应道', '笑道', '怒道', '低声道',
})

ZH_LIGHT_SCAFFOLD_NOUNS: frozenset = frozenset({
    '样子', '姿势', '态度', '表情', '神情', '神态', '动作',
    '方式', '方法', '形式', '状态', '情况', '程度',
})

# ── Japanese (language_id = 3) ───────────────────────────────

JA_QUOTE_ANCHORS: frozenset = frozenset({
    '言った', '言う', '言い', '述べた', '述べる', '答えた', '答える',
    '聞いた', '聞く', '叫んだ', '叫ぶ', '囁いた', '囁く',
    '話した', '話す', '説明した', '説明する', '指摘した', '指摘する',
    '強調した', '強調する', '表明した', '表明する',
})

JA_LIGHT_SCAFFOLD_NOUNS: frozenset = frozenset({
    '様子', '状態', '態度', '表情', '動作', '方法', '形', '状況',
    '程度', '場合', '意味', '関係', '問題',
})
