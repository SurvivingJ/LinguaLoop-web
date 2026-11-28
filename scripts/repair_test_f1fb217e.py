#!/usr/bin/env python3
"""One-off repair of test f1fb217e ("ねるまえのおはなし", ja, 2026-11-27).

Why this exists
    The generator stored its own self-correction inside the transcript: a
    first draft with a stray Hangul character (안心), the note "Wait —
    correcting a stray character in the last sentence. Final text:", then a
    corrected passage that also changed ねる前 to 就寝前 and dropped 子どもは.
    The token map, furigana, pitch, sense links and audio were all built from
    that text, and sense generation created 11 Japanese "words" for the
    English note (Wait, a, the, stray, character, ...).

    The repaired transcript keeps the draft's first two sentences (they match
    the questions, which say ねる前に) and the corrected third sentence
    (安心). The audio already holds clean takes of exactly those three
    sentences, so it is cut rather than re-synthesised (no TTS call).

What --dry-run does (read-only)
    Builds the new transcript, token map, sense list, furigana and pitch,
    cuts the audio locally, and prints a summary. Writes nothing.

What --apply does (LIVE-DB + R2)
    1. Backs up the test row, the junk vocabulary and senses, and the old
       audio to data/transcript_cleanup/2026-11-28/ (audio also to R2 under
       backups/).
    2. Uploads the cut audio over the same R2 key (URL unchanged).
    3. Updates transcript, transcript_hash, vocab_token_map, vocab_sense_ids,
       furigana_payload and pitch_payload in one UPDATE.
    4. Deletes the 11 junk dim_vocabulary rows and their 22 senses after
       re-checking that nothing else references them.
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv  # noqa: E402

try:
    from _common import base_parser  # noqa: E402
except ImportError:  # imported as scripts.<name>
    from scripts._common import base_parser  # noqa: E402

load_dotenv(os.path.join(ROOT, '.env'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger('repair_f1fb217e')

TEST_ID = 'f1fb217e-5e2f-4173-8752-c6a5a30c47b4'
JA = 3
NEW_TRANSCRIPT = (
    '夜、ねる前に、おかあさんは子どもに物語を読み聞かせします。'
    '子どもは、すきな本をえらんで、ベッドの中で聞きます。'
    'やさしい声を聞くと、安心して、ねむくなります。'
)
JUNK_VOCAB_IDS = list(range(37891, 37902))  # Wait ... text (11 rows)
# 就寝: only in the discarded corrected first sentence; 心: only from the
# typo 안心, now covered by 安心.
DROP_SENSES = {41287, 37813}
ADD_SENSES = {105388}  # 安心: the sense the other ja tests use
# Audio cut points (seconds), from silencedetect on the stored file: the long
# pauses split it into draft S1 | S2 | S3 | "Wait — ..." | "Final text:" |
# final S1 | S2 | S3. Keep 0-9.71 (draft S1+S2, half the pause after) and
# 31.87-end (half the pause before final S3, then S3).
AUDIO_KEEP = [(0.0, 9.71), (31.87, None)]
BACKUP_DIR = os.path.join(ROOT, 'data', 'transcript_cleanup', '2026-11-28')


def r2():
    import boto3
    return boto3.client(
        's3', endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'], region_name='auto')


def duration(path: str) -> float:
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'csv=p=0', path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def cut_audio(src: str, dst: str) -> None:
    parts = []
    for i, (a, b) in enumerate(AUDIO_KEEP):
        end = f':end={b}' if b is not None else ''
        parts.append(f'[0:a]atrim=start={a}{end},asetpts=PTS-STARTPTS[a{i}]')
    labels = ''.join(f'[a{i}]' for i in range(len(AUDIO_KEEP)))
    graph = ';'.join(parts) + f';{labels}concat=n={len(AUDIO_KEEP)}:v=0:a=1[out]'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-filter_complex', graph,
                    '-map', '[out]', '-ar', '48000', '-ac', '1', '-b:a', '192k', dst], check=True)


def main() -> int:
    a = base_parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    from services.test_generation.orchestrator import build_token_map_for_test
    from services.furigana_service import process_test_payload
    from services.pitch_accent_service import process_passage
    from services.dual_translation import sentence_refs as sr
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    row = db.table('tests').select('*').eq('id', TEST_ID).single().execute().data
    if 'Wait' not in (row['transcript'] or ''):
        log.error('transcript no longer holds the generator note; already repaired?')
        return 1
    junk_vocab = db.table('dim_vocabulary').select('*').in_('id', JUNK_VOCAB_IDS).execute().data or []
    junk_senses = db.table('dim_word_senses').select('*').in_('vocab_id', JUNK_VOCAB_IDS).execute().data or []
    junk_ids = {s['id'] for s in junk_senses}
    lemmas = sorted(v['lemma'] for v in junk_vocab)
    if len(junk_vocab) != 11 or any(not all(c.isascii() for c in l) for l in lemmas):
        log.error('junk vocabulary rows are not the expected 11 ASCII lemmas: %s', lemmas)
        return 1

    old_ids = set(row['vocab_sense_ids'] or [])
    seed_ids = sorted((old_ids - junk_ids - DROP_SENSES) | ADD_SENSES)
    token_map = build_token_map_for_test(db, NEW_TRANSCRIPT, 'ja', JA, sense_ids=seed_ids)
    joined = ''.join(t[0] for t in token_map)
    if joined != NEW_TRANSCRIPT:
        log.error('token map does not reproduce the transcript:\n%s', joined)
        return 1
    map_ids = sorted({t[1] for t in token_map if t[1]})
    stray = sorted(set(map_ids) - set(seed_ids))
    unused = sorted(set(seed_ids) - set(map_ids))
    sense_ids = sorted(set(seed_ids) | set(map_ids))
    unlinked = [t[0] for t in token_map if not t[1] and not all(c in '、。「」' for c in t[0])]

    questions = db.table('questions').select('question_id, question_text, choices') \
        .eq('test_id', TEST_ID).order('question_id').execute().data or []
    furigana = process_test_payload(NEW_TRANSCRIPT, questions)
    pitch = process_passage(NEW_TRANSCRIPT)

    tmp = tempfile.mkdtemp(prefix='f1fb217e_')
    old_mp3, new_mp3 = os.path.join(tmp, 'old.mp3'), os.path.join(tmp, 'new.mp3')
    key = row['audio_url'].rsplit('/', 1)[1]
    bucket = os.environ['R2_BUCKET_NAME']
    s3 = r2()
    s3.download_file(bucket, key, old_mp3)
    cut_audio(old_mp3, new_mp3)

    log.info('transcript: %s', NEW_TRANSCRIPT)
    log.info('token map: %d tokens, %d linked senses; unlinked tokens: %s', len(token_map), len(map_ids), unlinked)
    log.info('senses: %d -> %d (removed %d junk, dropped %s, added %s); linked by map but not seeded: %s; seeded but not in map: %s',
             len(old_ids), len(sense_ids), len(old_ids & junk_ids), sorted(DROP_SENSES & old_ids), sorted(ADD_SENSES), stray, unused)
    log.info('furigana: %d transcript tokens, %d questions; pitch: %d tokens',
             len(furigana.get('transcript') or []), len(furigana.get('questions') or []), len(pitch or []))
    log.info('audio: %.2fs -> %.2fs', duration(old_mp3), duration(new_mp3))
    log.info('junk to delete: %d vocabulary rows (%s), %d senses', len(junk_vocab), ', '.join(lemmas), len(junk_senses))

    if not a.apply:
        dst = os.path.join(tempfile.gettempdir(), 'claude-0', 'f1fb217e_new.mp3')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(new_mp3, dst)
        log.info('dry run: nothing written; cut audio left at %s', dst)
        return 0

    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup = {k: row[k] for k in ('id', 'title', 'transcript', 'transcript_hash', 'vocab_token_map', 'vocab_sense_ids',
                                  'furigana_payload', 'pitch_payload', 'audio_url', 'vocab_sense_stats')}
    backup['junk_vocabulary'] = junk_vocab
    backup['junk_senses'] = junk_senses
    with open(os.path.join(BACKUP_DIR, f'{TEST_ID}.json'), 'w', encoding='utf-8') as fh:
        json.dump(backup, fh, ensure_ascii=False, indent=1, default=str)
    with open(old_mp3, 'rb') as fh:
        old_bytes = fh.read()
    with open(os.path.join(BACKUP_DIR, f'{TEST_ID}.mp3'), 'wb') as fh:
        fh.write(old_bytes)
    s3.put_object(Bucket=bucket, Key=f'backups/2026-11-28/{key}', Body=old_bytes, ContentType='audio/mpeg')
    log.info('backed up row, junk rows and audio to %s and R2 backups/2026-11-28/', BACKUP_DIR)

    with open(new_mp3, 'rb') as fh:
        s3.put_object(Bucket=bucket, Key=key, Body=fh.read(), ContentType='audio/mpeg')
    log.info('uploaded cut audio over %s', key)

    db.table('tests').update({
        'transcript': NEW_TRANSCRIPT,
        'transcript_hash': sr.transcript_hash(NEW_TRANSCRIPT),
        'vocab_token_map': token_map,
        'vocab_sense_ids': sense_ids,
        'furigana_payload': furigana,
        'pitch_payload': pitch,
    }).eq('id', TEST_ID).execute()
    log.info('updated test row')

    # re-check nothing else points at the junk before deleting
    still = db.table('tests').select('id').overlaps('vocab_sense_ids', [str(i) for i in sorted(junk_ids)]).execute().data or []
    if still:
        log.error('junk senses still referenced by tests %s; not deleting', [t['id'] for t in still])
        return 1
    db.table('dim_word_senses').delete().in_('id', sorted(junk_ids)).execute()
    db.table('dim_vocabulary').delete().in_('id', JUNK_VOCAB_IDS).execute()
    log.info('deleted %d senses and %d vocabulary rows', len(junk_ids), len(JUNK_VOCAB_IDS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
