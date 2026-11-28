"""scripts/language_pack.py: profile, item, sense, dictionary and exercise-document checks; blind compare; build."""

import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'language_pack', os.path.join(ROOT, 'scripts', 'language_pack.py'))
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)

SUBS = ['x']
WHY = 'Motion verbs take essere, so the participle agrees with the subject.'


def profile(**over):
    prof = json.loads(json.dumps(lp.PROFILE_TEMPLATE))
    prof.update(code='xx', name='Testish', native_name='Testese', proposed_language_id=9)
    prof.update(over)
    return prof


def full_profile():
    ladder = [{'type_code': f'type_{i}', 'ladder_level': i, 'generator': 'llm', 'status': 'reuse'} for i in range(8)]
    ladder.append({'type_code': 'article_match', 'ladder_level': 4, 'generator': 'deterministic', 'status': 'new',
                   'note': 'pick the article from the gender dictionary'})
    feats = [{'key': f'f{i}', 'title': 't', 'why': 'w', 'delivered_by': 'grammar'} for i in range(2)]
    feats.append({'key': 'gender', 'title': 't', 'why': 'w', 'delivered_by': 'dictionary', 'dictionary': 'noun_gender'})
    dicts = [{'key': 'noun_gender', 'target': 100, 'unique': ['lemma'],
              'fields': {'lemma': 'str', 'gender': ['m', 'f'], 'plural': {'regex': r'^[a-zà-ù]+$'},
                         'irregular?': 'bool', 'forms': {'list': 'str', 'min': 1}}}]
    return profile(ladder=ladder, unique_features=feats, dictionaries=dicts)


@pytest.fixture
def tx():
    return lp.Text(profile())


def cloze(**over):
    item = {'id': 'aux-01-001', 'type': 'cloze', 'sub': 'x', 'lvl': 1, 'q': 'Ieri ___ andata al mare.',
            'opts': ['sono', 'ho', 'è', 'sto'], 'a': 0, 'tl': 'Ieri sono andata al mare.',
            'en': 'Yesterday I went to the seaside.', 'why': WHY}
    item.update(over)
    return item


def order(**over):
    item = {'id': 'aux-01-002', 'type': 'order', 'sub': 'x', 'lvl': 1,
            'tokens': ['ieri', 'ho visto', "l'amico", 'di Marco'],
            'alts': [['ho visto', "l'amico", 'di Marco', 'ieri']],
            'tl': "Ieri ho visto l'amico di Marco.", 'en': "Yesterday I saw Marco's friend.", 'why': WHY}
    item.update(over)
    return item


def judge(**over):
    item = {'id': 'aux-01-003', 'type': 'judge', 'sub': 'x', 'lvl': 1, 's': 'Ho andato a casa.', 'ok': False,
            'tl': 'Sono andato a casa.', 'en': 'I went home.', 'why': WHY}
    item.update(over)
    return item


def problems(item, tx):
    return lp.item_problems(item, SUBS, 'aux', tx)


# ---- profile ----------------------------------------------------------------

def test_template_profile_is_incomplete():
    errs = lp.profile_problems(profile(), 'xx')
    assert any(e.startswith('ladder') for e in errs)
    assert any(e.startswith('unique_features') for e in errs)


def test_full_profile_passes():
    assert lp.profile_problems(full_profile(), 'xx') == []


def test_profile_new_row_needs_a_note_and_dictionary_must_exist():
    prof = full_profile()
    prof['ladder'][-1].pop('note')
    prof['unique_features'][-1]['dictionary'] = 'nope'
    errs = lp.profile_problems(prof, 'xx')
    assert any('note' in e for e in errs)
    assert any("'nope'" in e for e in errs)


def test_profile_code_must_match():
    assert any(e.startswith('code') for e in lp.profile_problems(full_profile(), 'yy'))


# ---- drill items ------------------------------------------------------------

def test_valid_items(tx):
    for item in (cloze(), order(), judge(), judge(s='Sono andato a casa.', ok=True)):
        assert problems(item, tx) == []


def test_cloze_empty_option_closes_the_gap(tx):
    item = cloze(q='Vado ___ a casa.', opts=['in', '∅'], a=1, tl='Vado a casa.')
    assert problems(item, tx) == []


def test_cloze_two_blanks(tx):
    item = cloze(q='___ piove, ___ resto a casa.', opts=['Siccome|quindi', 'Siccome|∅', 'Perché|∅'], a=1,
                 tl='Siccome piove, resto a casa.')
    assert problems(item, tx) == []
    assert any('part(s)' in e for e in problems(dict(item, opts=['Siccome', 'Siccome|∅']), tx))


def test_cloze_tl_must_be_q_filled(tx):
    assert any('must equal q' in e for e in problems(cloze(tl='Ieri ho andata al mare.'), tx))


def test_digits_and_foreign_characters_are_rejected(tx):
    assert any('forbidden' in e for e in problems(cloze(q='Ho 3 ___ gatti.', opts=['bei', 'belli'], tl='Ho 3 bei gatti.'), tx))
    assert any('outside the profile' in e for e in problems(judge(s='我 andato a casa.'), tx))


def test_sentence_length_bounds(tx):
    assert any('words' in e for e in problems(judge(s='Vado.', ok=True, tl='Vado.'), tx))


def test_order_tokens_must_rebuild_the_sentence_ignoring_case(tx):
    assert problems(order(), tx) == []
    assert any('must equal tl' in e for e in problems(order(tokens=['ieri', 'ho visto', 'di Marco', "l'amico"], alts=[]), tx))


def test_order_alts_and_extra(tx):
    assert any('same tiles' in e for e in problems(order(alts=[['ieri', 'ho visto']]), tx))
    assert any('repeats' in e for e in problems(order(alts=[order()['tokens']]), tx))
    assert any('extra' in e for e in problems(order(extra=['ieri']), tx))


def test_judge_wrong_sentence_must_differ(tx):
    assert any('must differ' in e for e in problems(judge(s='Sono andato a casa.'), tx))
    assert any('must equal tl' in e for e in problems(judge(ok=True), tx))


def test_unknown_field_sub_and_id(tx):
    errs = problems(cloze(zh='x', sub='nope', id='other-01-001'), tx)
    assert any('unknown fields' in e for e in errs)
    assert any('sub:' in e for e in errs)
    assert any('must start with aux-' in e for e in errs)


def test_romanisation_required_when_the_profile_names_one():
    prof = profile()
    prof['text']['romanisation'] = 'revised romanisation'
    tx = lp.Text(prof)
    assert any(e.startswith('rom') for e in lp.item_problems(cloze(), SUBS, 'aux', tx))
    assert lp.item_problems(cloze(rom='ieri sono andata al mare'), SUBS, 'aux', tx) == []


def test_unspaced_script_joins_tiles_without_spaces():
    prof = profile()
    prof['text'].update(allowed_regex='^[一-鿿。，]+$', punctuation='。，', token_joiner='', casefold_tokens=False,
                        length_unit='chars', sentence_min=3, sentence_max=34)
    tx = lp.Text(prof)
    item = {'id': 'aux-01-009', 'type': 'order', 'sub': 'x', 'lvl': 1, 'tokens': ['我', '明天', '看', '电影'],
            'tl': '我明天看电影。', 'en': 'e', 'why': WHY}
    assert lp.item_problems(item, SUBS, 'aux', tx) == []


# ---- a pack on disk ---------------------------------------------------------

@pytest.fixture
def pack(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, 'PACKS', str(tmp_path / 'packs'))
    monkeypatch.setattr(lp, 'ROOT', str(tmp_path))
    assert lp.main(['init', 'xx', '--name', 'Testish', '--native', 'Testese']) == 0
    with open(lp.P('xx', 'profile.json'), 'w', encoding='utf-8') as fh:
        json.dump(full_profile(), fh)
    plan = {'language': 'xx', 'batch_size': 10, 'categories': [{'key': 'c', 'title': 'C'}],
            'themes': [f'theme {i}' for i in range(10)],
            'topics': [{'slug': 'aux', 'title': 'Auxiliaries', 'cat': 'c', 'batches': 1,
                        'mix': {'cloze': 4, 'order': 3, 'judge': 3},
                        'scope': 'Which auxiliary a verb takes in compound tenses, and participle agreement with essere.'}]}
    with open(lp.P('xx', 'grammar', 'plan.json'), 'w', encoding='utf-8') as fh:
        json.dump(plan, fh)
    ex = [{'tl': 'Sono andato a casa.', 'en': 'I went home.'}, {'tl': 'Ho mangiato la pasta.', 'en': 'I ate the pasta.'}]
    guide = {'topic': 'aux', 'summary': 'Most verbs take avere; verbs of motion and change of state take essere. ' * 2,
             'subs': [{'key': k, 'label': k, 'focus': 'f'} for k in ('x', 'y', 'z')],
             'rules': [{'sub': k, 'rule': 'r', 'examples': ex} for k in ('x', 'y', 'z')],
             'contrasts': [{'wrong': f'Ho andato a casa {w}.', 'right': {'tl': f'Sono andato a casa {w}.', 'en': 'e'},
                            'why': 'w'} for w in ('ieri', 'oggi', 'presto')],
             'cheat': ['a', 'b', 'c']}
    with open(lp.P('xx', 'grammar', 'guides', 'aux.json'), 'w', encoding='utf-8') as fh:
        json.dump(guide, fh)
    return tmp_path


def batch_items():
    names = ['Anna', 'Marta', 'Paola', 'Lucia', 'Giulia', 'Sara', 'Elena', 'Chiara', 'Laura', 'Silvia']
    items = []
    for i, n in enumerate(names):
        iid = f'aux-01-{i + 1:03d}'
        lvl = 1 if i < 5 else (3 if i < 7 else 2)
        if i < 4:
            items.append(cloze(id=iid, lvl=lvl, a=i % 2, q=f'Ieri {n} ___ andata al mare.',
                               opts=['è', 'ha'] if i % 2 == 0 else ['ha', 'è'], tl=f'Ieri {n} è andata al mare.'))
        elif i < 7:
            items.append(order(id=iid, lvl=lvl, tokens=['ieri', n, 'ha visto', 'il film'],
                               alts=[[n, 'ha visto', 'il film', 'ieri']], tl=f'Ieri {n} ha visto il film.'))
        else:
            items.append(judge(id=iid, lvl=lvl, s=f'{n} ha andata a casa.', tl=f'{n} è andata a casa.')
                         if i < 9 else judge(id=iid, lvl=lvl, s=f'{n} è andata a casa.', ok=True, tl=f'{n} è andata a casa.'))
    for i, it in enumerate(items):
        it['sub'] = 'xyz'[i % 3]
    return items


def write_batch(sub, items):
    path = lp.P('xx', 'grammar', sub, 'aux-01.jsonl')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(json.dumps(i, ensure_ascii=False) for i in items))
    return path


def test_plan_guide_and_batch_validate(pack, capsys):
    write_batch('batches', batch_items())
    assert lp.main(['validate-plan', 'xx']) == 0
    assert lp.main(['validate-guide', 'xx', 'aux.json']) == 0
    assert lp.main(['validate-batch', 'xx', 'aux-01.jsonl']) == 0
    assert 'OK, 10 items' in capsys.readouterr().out


def test_batch_reports_duplicates_and_size(pack, capsys):
    items = batch_items()
    items[1] = dict(items[0], id='aux-01-002')
    write_batch('batches', items[:9])
    assert lp.main(['validate-batch', 'xx', 'aux-01.jsonl']) == 1
    out = capsys.readouterr().out
    assert 'duplicate content' in out and 'at least 10 required' in out


def test_strip_hides_answers_and_compare_flags_disagreement(pack, capsys):
    items = batch_items()
    write_batch('batches', items)
    assert lp.main(['strip', 'xx', 'aux-01.jsonl']) == 0
    blind = [json.loads(line) for line in open(lp.P('xx', 'grammar', 'blind', 'aux-01.blind.jsonl'), encoding='utf-8')]
    assert all('tl' not in b and 'a' not in b and 'why' not in b and 'ok' not in b for b in blind)
    answers = []
    for it in items:
        if it['type'] == 'cloze':
            answers.append({'id': it['id'], 'ok': [it['a']]})
        elif it['type'] == 'order':
            answers.append({'id': it['id'], 'tl': it['tl']})
        else:
            answers.append({'id': it['id'], 'ok': it['ok']})
    answers[0]['ok'] = [0, 1]                       # ambiguous cloze
    answers[4]['tl'] = f'{items[4]["tokens"][1]} ha visto il film ieri.'   # listed alt: accepted
    answers[5]['tl'] = 'Il film ha visto ieri.'     # not an accepted order
    answers[7]['ok'] = True                          # judgement differs
    with open(lp.P('xx', 'grammar', 'blind', 'aux-01.answers.jsonl'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(json.dumps(a, ensure_ascii=False) for a in answers))
    capsys.readouterr()
    assert lp.main(['compare', 'xx', 'aux-01.jsonl']) == 0
    out = capsys.readouterr().out
    assert '10 items, 3 flagged' in out
    assert 'AMBIGUOUS' in out and 'DIFFERENT ORDER' in out and 'JUDGEMENT DIFFERS' in out


def test_build_serves_reviewed_batches_only(pack, capsys):
    write_batch('batches', batch_items())
    assert lp.main(['build', 'xx']) == 0
    assert '0 items in 0 topics' in capsys.readouterr().out
    write_batch('reviewed', batch_items())
    assert lp.main(['build', 'xx']) == 0
    out_dir = lp.P('xx', 'grammar', 'built')
    manifest = json.load(open(os.path.join(out_dir, 'manifest.json'), encoding='utf-8'))
    assert manifest['total'] == 10 and manifest['fields']['sentence'] == 'tl' and manifest['token_joiner'] == ' '
    assert manifest['topics'][0]['types'] == {'cloze': 4, 'order': 3, 'judge': 3}
    assert lp.main(['build', 'xx', '--check']) == 0
    write_batch('reviewed', batch_items()[:9])
    assert lp.main(['build', 'xx', '--check']) == 1


def sense(**over):
    s = {'lemma': 'casa', 'pos': 'noun', 'confidence': 0.95, 'pronunciation': '/ˈkaza/',
         'tl_simple': 'Il posto dove una persona vive con la sua famiglia.',
         'tl_standard': 'Edificio o parte di edificio destinato ad abitazione.', 'example': 'La mia casa è piccola.',
         'glosses': {'en': {'simple': 'house', 'standard': 'house; home'}}, 'lexical': {'gender': 'f'}}
    s.update(over)
    return s


def test_sense_checks():
    prof = full_profile()
    assert lp.sense_problems(prof, [sense()]) == []
    errs = lp.sense_problems(prof, [sense(tl_simple='La casa è una casa.',
                                          glosses={'en': {'simple': 'house; home', 'standard': 'house'}})])
    assert any('uses the word itself' in e for e in errs)
    assert any('longer than simple' in e for e in errs)
    assert lp.sense_problems(prof, [{'lemma': 'x', 'skip': True, 'reason': 'not a word'}]) == []
    assert any('input order' in e for e in lp.sense_problems(prof, [sense()], expect=['cane']))


def test_sense_batches_merge_and_worklist(pack, capsys):
    rows = [{'lemma': 'casa', 'pos': 'noun', 'level': 'A1', 'zipf': 6.0, 'hint': 'house'},
            {'lemma': 'andare', 'pos': 'verb', 'level': 'A1', 'zipf': 6.5, 'hint': 'to go'},
            {'lemma': 'marco', 'drop': True, 'reason': 'name'}]
    with open(lp.P('xx', 'lexicon', 'lexicon_01.jsonl'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(json.dumps(r) for r in rows))
    assert lp.main(['validate-lexicon', 'xx']) == 0
    capsys.readouterr()
    assert lp.main(['sense-batches', 'xx', '--size', '5']) == 0
    assert json.loads(capsys.readouterr().out) == {'batches': ['write_001.in.json'], 'words': 2}
    assert [w['lemma'] for w in json.load(open(lp.P('xx', 'senses', 'write_001.in.json')))] == ['andare', 'casa']
    assert lp.main(['sense-batches', 'xx']) == 0
    assert json.loads(capsys.readouterr().out)['batches'] == []       # nothing is cut twice
    out = [sense(lemma='andare', pos='verb', tl_simple='Muoversi da un posto a un altro.', example='Voglio andare a casa.',
                 glosses={'en': {'simple': 'to go', 'standard': 'to go; to move toward a place'}}), sense()]
    for suffix in ('out', 'reviewed'):
        with open(lp.P('xx', 'senses', f'write_001.{suffix}.json'), 'w', encoding='utf-8') as fh:
            json.dump(out, fh)
        if suffix == 'out':
            assert lp.main(['merge-senses', 'xx']) == 0
            assert json.load(open(lp.P('xx', 'senses', 'final.json'))) == []   # unreviewed batches are left out
    assert lp.main(['validate-senses', 'xx', 'write_001.reviewed.json']) == 0
    assert lp.main(['merge-senses', 'xx']) == 0
    assert len(json.load(open(lp.P('xx', 'senses', 'final.json')))) == 2
    capsys.readouterr()
    assert lp.main(['fatseed-worklist', 'xx', '--n', '2']) == 0
    assert json.loads(capsys.readouterr().out) == {'senses': ['andare.verb.json', 'casa.noun.json']}


def test_dictionary_rows_follow_the_profile_spec(pack, capsys):
    rows = [{'lemma': 'casa', 'gender': 'f', 'plural': 'case', 'forms': ['la casa']},
            {'lemma': 'uomo', 'gender': 'x', 'plural': 'UOMINI', 'forms': [], 'extra': 1},
            {'lemma': 'casa', 'gender': 'f', 'plural': 'case', 'forms': ['la casa'], 'irregular': False}]
    with open(lp.P('xx', 'dictionaries', 'noun_gender_01.jsonl'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(json.dumps(r) for r in rows))
    assert lp.main(['validate-dict', 'xx', 'noun_gender']) == 1
    out = capsys.readouterr().out
    for needle in ("'x' is not one of", 'does not match', 'a list of at least 1', "unknown fields ['extra']", 'same lemma as'):
        assert needle in out
    os.makedirs(lp.P('xx', 'dictionaries', 'reviewed'), exist_ok=True)
    with open(lp.P('xx', 'dictionaries', 'reviewed', 'noun_gender_01.jsonl'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(rows[0]))
    assert lp.main(['validate-dict', 'xx', 'noun_gender', '--reviewed']) == 0


def fat_doc():
    def opts(words):
        return {'sentence_index': 0, 'options': [{'text': w, 'is_correct': i == 0, 'explanation': f'{w}: a specific reason here'}
                                                 for i, w in enumerate(words)]}
    core = {'definition': 'Edificio destinato ad abitazione.',
            'sentences': [{'text': f'La casa numero {w} è bella.', 'target_word': 'casa'}
                          for w in ('uno', 'due', 'tre', 'quattro', 'cinque', 'sei', 'sette', 'otto', 'nove', 'dieci')]}

    def variant(tag):
        return {'level_1': opts(['casa', f'cassa{tag}', f'cosa{tag}', f'caso{tag}']),
                'level_3': opts(['casa', f'strada{tag}', f'mano{tag}', f'idea{tag}']),
                'level_4': {'declined': 'no_inflection'},
                'level_6': {'sentence_index': 1, 'correct_sentence_index': 1,
                            'wrong_sentences': [{'text': f'Ho bevuto una casa {tag} {w}.', 'explanation': 'a house is not drunk'}
                                                for w in ('ieri', 'oggi', 'domani')]},
                'level_7': {'sentence_index': 2, 'incorrect_sentence': f'Il casa {tag} è bella.',
                            'corrected_sentence': f'La casa {tag} è bella.', 'error_description': 'casa is feminine: la casa'}}
    return {'lemma': 'casa', 'pos': 'noun', 'core': core, 'variants': {'A': variant('a'), 'B': variant('b')}}


def test_fatseed_document_shape():
    prof = full_profile()
    assert lp.fatseed_problems(prof, fat_doc()) == []
    doc = fat_doc()
    doc['variants']['B'] = json.loads(json.dumps(doc['variants']['A']))
    assert any('write B independently' in e for e in lp.fatseed_problems(prof, doc))
    doc = fat_doc()
    doc['core']['sentences'][0]['target_word'] = 'cas'
    doc['variants']['A']['level_3']['options'][1]['is_correct'] = True
    doc['variants']['A']['level_4'] = {'declined': 'because'}
    doc['variants']['A']['mystery'] = {}
    errs = lp.fatseed_problems(prof, doc)
    for needle in ('not a whole word', 'exactly one correct', 'cannot be declined', 'unknown block'):
        assert any(needle in e for e in errs)


def test_status_counts(pack):
    write_batch('batches', batch_items())
    write_batch('reviewed', batch_items())
    st = lp.status('xx')
    assert st['profile_problems'] == 0
    assert st['grammar']['batches_written'] == 1 and st['grammar']['items_reviewed_valid'] == 10
    assert st['dictionaries']['noun_gender'] == {'rows': 0, 'reviewed_rows': 0, 'target': 100}


# ---- comprehension tests ------------------------------------------------------

def a_test(**over):
    sents = [{'tl': 'Marta abita a Bologna con la sua famiglia.', 'en': 'Marta lives in Bologna with her family.'},
             {'tl': 'Ogni mattina prende il treno delle 7 per andare al lavoro.', 'en': 'Every morning she takes the 7 o\'clock train to work.'},
             {'tl': 'In ufficio beve un caffè e parla con i colleghi.', 'en': 'At the office she drinks a coffee and talks with her colleagues.'},
             {'tl': 'La sera torna a casa stanca ma contenta, e prepara la cena.', 'en': 'In the evening she comes home tired but happy, and makes dinner.'},
             {'tl': 'Dopo cena legge un libro sul divano e poi va a letto presto.', 'en': 'After dinner she reads a book on the sofa and then goes to bed early.'}]
    def q(i, typ, ans):
        return {'type': typ, 'text': f'Che cosa fa Marta nella frase {"uno due tre quattro".split()[i]}?',
                'choices': [f'Risposta {w}' for w in ('prima', 'seconda', 'terza', 'quarta')], 'answer': ans,
                'evidence': [i], 'explanation': 'The passage says this directly; the other choices are not mentioned at all.'}
    t = {'slug': 'xx-t1-marta-day', 'tier': 1, 'category': 'Family', 'topic': 'An ordinary working day of a woman who lives in Bologna.',
         'style': 'academic', 'title': 'La giornata di Marta', 'title_en': "Marta's day", 'sentences': sents,
         'questions': [q(0, 'literal_detail', 0), q(1, 'literal_detail', 1), q(2, 'vocabulary_context', 2), q(3, 'literal_detail', 3)],
         'vocab': [{'lemma': w, 'pos': 'noun', 'en': 'x'} for w in ('famiglia', 'treno', 'lavoro', 'ufficio', 'cena')]}
    t.update(over)
    return t


def test_a_valid_test_and_its_main_faults(tx):
    assert lp.one_test_problems(a_test(), tx, 'xx') == []
    t = a_test(tier=2)
    errs = lp.one_test_problems(t, tx, 'xx')
    assert any('takes 70 to 120' in e for e in errs) and any('exactly 5' in e for e in errs) and any('slug' in e for e in errs)
    t = a_test()
    t['questions'][0]['type'] = 'inference'
    t['questions'][1]['choices'][1] = t['questions'][1]['choices'][0]
    t['questions'][2]['evidence'] = [9]
    t['questions'][3]['answer'] = 4
    errs = lp.one_test_problems(t, tx, 'xx')
    for needle in ('type must be one of', 'two choices are the same', 'evidence is a list', 'answer is the index'):
        assert any(needle in e for e in errs)
    conv = a_test(style='conversational')
    assert any('names the speaker' in e for e in lp.one_test_problems(conv, tx, 'xx'))
    assert any('outside the profile' in e for e in lp.one_test_problems(a_test(title='我的一天'), tx, 'xx'))


def test_test_plan_batch_blind_compare_and_export(pack, capsys):
    plan = {'tier': 1, 'batches': [{'id': 't1-01', 'tests': [
        {'slug': 'xx-t1-marta-day', 'category': 'Family', 'style': 'academic', 'topic': 'An ordinary working day of a woman who lives in Bologna.'}]}]}
    with open(lp.P('xx', 'tests', 'plan', 't1.json'), 'w', encoding='utf-8') as fh:
        json.dump(plan, fh)
    assert lp.main(['validate-test-plan', 'xx', 't1.json']) == 0
    for sub in ('batches', 'reviewed'):
        with open(lp.P('xx', 'tests', sub, 't1-01.jsonl'), 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(a_test(), ensure_ascii=False))
    assert lp.main(['validate-tests', 'xx', 't1-01.jsonl']) == 0
    assert lp.main(['tests-strip', 'xx', 't1-01.jsonl']) == 0
    blind = open(lp.P('xx', 'tests', 'blind', 't1-01.nopassage.jsonl'), encoding='utf-8').read()
    assert 'answer' not in blind and 'Bologna' not in blind
    assert 'Bologna' in open(lp.P('xx', 'tests', 'blind', 't1-01.passage.jsonl'), encoding='utf-8').read()
    with open(lp.P('xx', 'tests', 'blind', 't1-01.answers_nopassage.jsonl'), 'w') as fh:
        fh.write(json.dumps({'slug': 'xx-t1-marta-day', 'answers': [0, 3, 2, 0]}))
    with open(lp.P('xx', 'tests', 'blind', 't1-01.answers.jsonl'), 'w') as fh:
        fh.write(json.dumps({'slug': 'xx-t1-marta-day', 'answers': [[0], [1, 2], [2], [0]]}))
    capsys.readouterr()
    assert lp.main(['tests-compare', 'xx', 't1-01.jsonl']) == 0
    out = capsys.readouterr().out
    assert 'GUESSABLE' in out and 'AMBIGUOUS' in out and 'KEY REJECTED' in out
    assert 'without the passage: 1 of 3' in out          # the vocabulary question is not counted
    assert lp.main(['tests-export', 'xx']) == 0
    row = json.loads(open(lp.P('xx', 'tests', 'final.jsonl'), encoding='utf-8').read())
    assert row['difficulty'] == 1 and row['transcript'].startswith('Marta abita') and row['transcript'].endswith('presto.')
    assert lp.status('xx')['tests']['valid'] == 1


def test_lexicon_dedupe_and_archive_round_trip(pack, capsys):
    for n, rows in (('lexicon_01.jsonl', [{'lemma': 'casa', 'pos': 'noun', 'level': 'A1', 'zipf': 6.0, 'hint': 'house'}]),
                    ('lexicon_02.jsonl', [{'lemma': 'Casa', 'pos': 'noun', 'level': 'A1', 'zipf': 6.0, 'hint': 'house'},
                                          {'lemma': 'casa', 'pos': 'verb', 'level': 'B2', 'zipf': 3.0, 'hint': 'x'}])):
        with open(lp.P('xx', 'lexicon', n), 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(json.dumps(r) for r in rows))
    assert lp.main(['lexicon-dedupe', 'xx']) == 0
    assert '1 repeated' in capsys.readouterr().out
    assert lp.main(['validate-lexicon', 'xx']) == 0
    assert lp.main(['archive', 'xx']) == 0
    first = open(lp.P('xx', 'archive', 'lexicon.tar.gz'), 'rb').read()
    assert lp.main(['archive', 'xx']) == 0
    assert open(lp.P('xx', 'archive', 'lexicon.tar.gz'), 'rb').read() == first      # same content, same bytes
    os.remove(lp.P('xx', 'lexicon', 'lexicon_02.jsonl'))
    assert lp.main(['unarchive', 'xx']) == 0
    assert os.path.exists(lp.P('xx', 'lexicon', 'lexicon_02.jsonl'))
    assert json.load(open(lp.P('xx', 'archive', 'MANIFEST.json')))['lexicon']['files'] == 2
