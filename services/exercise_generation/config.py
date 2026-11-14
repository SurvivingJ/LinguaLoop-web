# services/exercise_generation/config.py

# --- Sentence generation ------------------------------------------------------
LLM_BATCH_SIZE: int = 25

# --- Grammar pattern heuristics (for transcript mining) ---------------------
PATTERN_HEURISTICS: dict[str, str] = {
    'en_present_perfect_cont':  r'\b(has|have)\s+been\s+\w+ing\b',
    'en_passive_voice_simple':  r'\b(is|was|are|were|been)\s+\w+ed\b',
    'en_reported_speech':       r'\b(said|told|asked|thought)\s+(that|if|whether)\b',
    'cn_ba_construction':       r'把',
    'cn_bei_passive':           r'被',
    'cn_le_completed':          r'了',
    'cn_guo_experience':        r'过',
    'cn_zhe_continuous':        r'着',
    'cn_de_complement':         r'得',
    'cn_shi_de_cleft':          r'是.+的',
    'cn_bi_comparative':        r'比',
    'cn_lian_dou_emphasis':     r'连.+[都也]',
    'cn_measure_word_ge':       r'[一两三四五六七八九十几多]\s*个',
    'cn_neng_hui_keyi':         r'[能会]|可以',
    'cn_yao_intention':         r'要',
    'cn_ruguo_conditional':     r'如果.+就',
    'cn_yinwei_suoyi_cause':    r'因为.+所以',
    'cn_bu_shi_er_shi_contrast': r'不是.+而是',
    'jp_te_form_progressive':   r'ている|ています',
    'jp_keigo_sonkeigo':        r'ていらっしゃ|いらっしゃ|ございます',
}

# --- Language IDs (mirrors dim_languages) ------------------------------------
LANG_CHINESE:  int = 1
LANG_ENGLISH:  int = 2
LANG_JAPANESE: int = 3

# language_id -> ISO code (llm_calls.language_code and friends). A local
# constant rather than DimensionService: a DB-cached lookup needs an
# app-startup init that judges and batch scripts cannot rely on, and the id
# space is small and stable.
LANG_ID_TO_CODE: dict[int, str] = {
    LANG_CHINESE: 'zh', LANG_ENGLISH: 'en', LANG_JAPANESE: 'ja',
}
