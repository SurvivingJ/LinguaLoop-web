// /grammar-drill: Chinese grammar drills (static/js/grammar/app.js).
import { mountGrammar } from '../grammar/app.js';

const start = () => {
  const root = document.getElementById('grammarRoot');
  if (root) mountGrammar(root, { manifestUrl: root.dataset.manifest });
};

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
else start();
