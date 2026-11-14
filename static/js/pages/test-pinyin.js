// /test/<slug>/pinyin: the pinyin session player mounted as a page.
import { mount } from '../session/players/pinyin.js';
import { mountTestPage } from '../session/players/_syllable_trainer.js';

const start = () =>
  mountTestPage(mount, { root: document.getElementById('pinyinRoot'), testType: 'pinyin' });

if (document.readyState === 'complete') start();
else document.addEventListener('DOMContentLoaded', start);
