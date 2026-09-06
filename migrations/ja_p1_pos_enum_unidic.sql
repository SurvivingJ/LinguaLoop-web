-- ja Prompt-1 POS enum + validation profile alignment (UniDic tagset)
--
-- WHY
-- ---
-- `vocab_prompt1_core` (language_id=3) left its output schema's key "1" as a
-- bare 品詞（文字列） with no enumerated vocabulary, unlike key "2" which pins
-- the semantic-class tokens. With nothing to constrain it, qwen/qwen3.7-plus
-- free-formed the label and settled on *Simplified Chinese* POS terms (名词,
-- 动词). That passed validation only because the ja LanguageValidationProfile
-- declared `pos_set=DEFAULT_POS_SET` — the merged EN+ZH set — so the gate
-- accepted a tagset no other ja data uses.
--
-- The corpus disagrees: dim_vocabulary carries 3,323 ja rows tagged in the
-- UniDic style (名詞 2537, 動詞 498, 形状詞 129, 副詞 80, 形容詞 79) against 6
-- written by the ladder itself. UniDic is the intended tagset; the ladder was
-- the outlier.
--
-- PAIRED CODE CHANGE — APPLY TOGETHER
-- -----------------------------------
-- services/vocabulary_ladder/config.py adds `_POS_JA` and points profile 3 at
-- it. The two halves are a matched pair and neither is safe alone:
--   * code without this migration -> the prompt still emits 名词, which the
--     narrowed gate now REJECTS: every ja P1 generation fails.
--   * this migration without the code -> the prompt emits 名詞, which the old
--     merged gate does not contain: every ja P1 generation fails.
-- Apply this immediately before or after deploying that commit, not weeks
-- apart. Blast radius today is small (9 ja word_assets, 0 ja exercises), which
-- is exactly why now is the moment to fix it.
--
-- Idempotent: re-running is a no-op once v3 exists.

begin;

-- 1. Guard. Fail loudly rather than silently writing an unmodified v3 if the
--    v2 text has drifted (a prompt rewrite would move this literal).
do $$
declare
  n int;
begin
  select count(*) into n
  from prompt_templates
  where task_name = 'vocab_prompt1_core'
    and language_id = 3
    and version = 2
    and template_text like '%"1" = 品詞（文字列）%';

  if n <> 1 then
    raise exception
      'expected exactly 1 ja vocab_prompt1_core v2 row containing the bare '
      '品詞（文字列） schema line, found %. The prompt has drifted — re-derive '
      'the replacement target before applying.', n;
  end if;
end $$;

-- 2. v3 = v2 with the POS enum pinned. Derived from the live row by targeted
--    replacement rather than pasted in full, so nothing else in the prompt can
--    drift by accident — the numeric keys and Latin tokens are parser contract,
--    not prose, and must survive verbatim.
insert into prompt_templates
    (task_name, language_id, version, template_text, model, provider, is_active)
select
    task_name,
    language_id,
    3,
    replace(
        template_text,
        '"1" = 品詞（文字列）',
        '"1" = 品詞（規定トークン：名詞/動詞/形容詞/形状詞/副詞/助詞/助動詞/接続詞/代名詞/連体詞/感動詞/接頭辞/接尾辞）'
    ),
    model,
    provider,
    true
from prompt_templates
where task_name = 'vocab_prompt1_core'
  and language_id = 3
  and version = 2
  and not exists (
      select 1 from prompt_templates
      where task_name = 'vocab_prompt1_core' and language_id = 3 and version = 3
  );

-- 3. Retire v2. get_template_config orders by version desc and filters
--    is_active, so v3 would win regardless — but leaving two active rows is
--    how a later "deactivate the new one" rollback silently serves nothing.
update prompt_templates
set is_active = false
where task_name = 'vocab_prompt1_core'
  and language_id = 3
  and version = 2;

-- 4. Clean the rows the ladder contaminated. Scoped to language_id=3 so the
--    genuinely-Chinese vocabulary is untouched. 6 rows as of 2026-09-04.
update dim_vocabulary set part_of_speech = '名詞'
where language_id = 3 and part_of_speech = '名词';

update dim_vocabulary set part_of_speech = '動詞'
where language_id = 3 and part_of_speech = '动词';

commit;

-- Verification — run after applying.
--
-- Expect exactly one active row, version 3, with the enum present:
--   select version, is_active,
--          template_text like '%規定トークン：名詞/動詞%' as enum_pinned
--   from prompt_templates
--   where task_name = 'vocab_prompt1_core' and language_id = 3
--   order by version desc;
--
-- Expect zero rows:
--   select part_of_speech, count(*) from dim_vocabulary
--   where language_id = 3 and part_of_speech in ('名词','动词')
--   group by 1;
--
-- All 13 existing ja prompt1_core assets still carry the old labels in their
-- stored content (validation runs at write time, not on read), 9 of them valid.
-- Regenerate rather than back-fill the JSON. Note --regenerate-core: without
-- it, stage=core skips any sense that already has a valid core, so a stale one
-- would stay invisible.
--   python scripts/export_exercise_worklist.py --language ja --stage core \
--     --regenerate-core --sense-ids 34997,34998,35001,35005,35009,35011,35015,35017,35215
