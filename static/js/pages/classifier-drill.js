// /classifier-drill: the measure-word drill as a page.
import { CLASSIFIER, mountDrillPage } from '../session/players/classifier_drill.js';

const start = () => mountDrillPage(document.getElementById('drillRoot'), CLASSIFIER);

if (document.readyState === 'complete') start();
else document.addEventListener('DOMContentLoaded', start);
