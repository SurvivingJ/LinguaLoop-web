// Prestudy page (/test/<slug>/prestudy): hands two session modules to the
// classic script static/js/prestudy/prestudy.js.
import { countWord } from '../session/players/intro_drill.js';
import { posClass, maskHeadword } from '../session/lexicon.js';

// The new-word drill's counting rule, so a prime that counts as intro session 1
// is judged the same way.
window.IntroDrillCount = { countWord };
window.LinguaLexicon = { posClass, maskHeadword };
