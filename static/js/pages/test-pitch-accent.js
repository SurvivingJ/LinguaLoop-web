// /test/<slug>/pitch-accent: the pitch-accent session player mounted as a page.
import { mount } from '../session/players/pitch_accent.js';
import { mountTestPage } from '../session/players/_syllable_trainer.js';

const start = () =>
  mountTestPage(mount, {
    root: document.getElementById('pitchAccentRoot'),
    testType: 'pitch_accent',
  });

if (document.readyState === 'complete') start();
else document.addEventListener('DOMContentLoaded', start);
