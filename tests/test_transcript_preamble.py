"""TASK-900: the transcript preamble matcher (services/transcript_preamble.py)."""

import hashlib

import pytest

from services.transcript_preamble import (
    PreambleMatch,
    detect_preamble,
    strip_preamble,
    transcript_hash,
)

JA_BODY = '小さなロボットアームを作ろう！まず、必要な部品を集めます。'
JA_PREAMBLE = (
    'この文章は、T3レベル（B1-B2）の学習者向けに、小さな物を掴めるシンプルなロボットアームの'
    '製作について解説します。'
)
JA_SAMPLE = JA_PREAMBLE + '--- ' + JA_BODY


def test_strips_ja_level_sentence_with_separator():
    found = detect_preamble(JA_SAMPLE)
    assert isinstance(found, PreambleMatch)
    assert found.kind == 'separator'
    assert found.preamble == JA_PREAMBLE
    assert found.cleaned == JA_BODY
    assert strip_preamble(JA_SAMPLE) == JA_BODY


def test_separator_run_and_newlines_are_consumed():
    text = 'T2 level (B1) passage for learners.\n----\n\nThe body starts here. More.'
    assert strip_preamble(text) == 'The body starts here. More.'


def test_does_not_strip_legitimate_sentence_mentioning_t3():
    text = ('T3ロボットアームは小さな物を掴めます。シンプルな構造で、誰でも作れます。'
            '次に、必要な部品を見ていきましょう。')
    assert detect_preamble(text) is None
    assert strip_preamble(text) == text

    en = ('The T3 robot arm can grip small objects. It uses three motors and a simple frame. '
          'Students build it in one afternoon.')
    assert detect_preamble(en) is None

    # Even with a later paragraph break: a plain opening paragraph is prose.
    en_para = 'The T3 robot arm can grip small objects.\n\nIt uses three motors.'
    assert detect_preamble(en_para) is None


def test_separator_inside_body_without_level_lead_is_not_a_preamble():
    text = 'Robots are useful. Here is a list --- motors, frames and sensors --- of parts.'
    assert detect_preamble(text) is None


def test_zh_benwen_with_separator():
    text = '本文为T4级别（B2-C1）学习者介绍长城的历史。--- 长城是中国古代的伟大工程。它有两千多年的历史。'
    found = detect_preamble(text)
    assert found is not None and found.kind == 'separator'
    assert found.cleaned == '长城是中国古代的伟大工程。它有两千多年的历史。'


def test_zh_benwen_first_sentence_without_separator():
    text = '本文介绍长城的历史。长城是中国古代的伟大工程。它有两千多年的历史。'
    found = detect_preamble(text)
    assert found is not None and found.kind == 'sentence'
    assert found.preamble == '本文介绍长城的历史。'
    assert found.cleaned == '长城是中国古代的伟大工程。它有两千多年的历史。'


def test_en_this_passage_first_sentence():
    text = ('This passage is written for B1-B2 learners and explains organ donation. '
            'Organ donation is a vital medical process. It can save lives.')
    found = detect_preamble(text)
    assert found is not None and found.kind == 'sentence'
    assert found.cleaned == 'Organ donation is a vital medical process. It can save lives.'

    article = 'This article explains tides.\n\nTides rise and fall twice a day.'
    assert strip_preamble(article) == 'Tides rise and fall twice a day.'


def test_en_parenthetical_note_block():
    text = ('(Note: The prompt designates Level T2, which maps to the B1-B2 intermediate tier '
            'defined in the guidelines).\n\nOrgan donation is a vital medical process that can '
            'save lives. When a person decides to become a donor, they give permission.')
    found = detect_preamble(text)
    assert found is not None and found.kind == 'block'
    assert found.cleaned.startswith('Organ donation is a vital medical process')


def test_en_header_block_with_tier_code():
    text = ('Level Definitions & Target Audience Analysis:\n   Target Level: A1-A2 (Beginner)\n'
            '   Target Audience: Elementary school students.\n   Mandatory Keywords: China, wall.\n\n'
            'Long ago, people in China made a very big wall. They needed a wall for defense.')
    found = detect_preamble(text)
    assert found is not None and found.kind == 'block'
    assert found.cleaned == ('Long ago, people in China made a very big wall. '
                             'They needed a wall for defense.')


def test_header_block_without_tier_code_is_kept():
    # A title-like first line followed by a blank line is not metadata on its own.
    text = 'The Great Wall: a short history\n\nLong ago, people in China made a very big wall.'
    assert detect_preamble(text) is None


def test_opener_only_without_terminator_is_kept():
    assert detect_preamble('This passage has no terminator at all') is None


@pytest.mark.parametrize('value', [None, '', '   '])
def test_empty_inputs(value):
    assert detect_preamble(value) is None


def test_transcript_hash_is_sha256_hex():
    assert transcript_hash(JA_BODY) == hashlib.sha256(JA_BODY.encode('utf-8')).hexdigest()
    assert len(transcript_hash('x')) == 64
