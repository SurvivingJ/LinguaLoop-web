// static/js/grammar/data.js
// Grammar drills: loading the static content (built by
// scripts/grammar_drills.py into static/data/grammar/<lang>/) and the optional
// item generators. No API and no database are involved.

async function getJson(url) {
  const resp = await fetch(url, { credentials: 'same-origin' });
  if (!resp.ok) throw new Error('HTTP ' + resp.status + ' for ' + url);
  return resp.json();
}

/** { language, categories, total, topics } */
export function loadManifest(url) {
  return getJson(url);
}

/** URL of a topic file beside the manifest, versioned by the topic's hash. */
export function topicUrl(manifestUrl, topic) {
  const base = String(manifestUrl)
    .split('?')[0]
    .replace(/[^/]*$/, '');
  return base + encodeURIComponent(topic.slug) + '.json' + (topic.v ? '?v=' + topic.v : '');
}

const topicCache = new Map();

/** { topic, guide, items } for a manifest topic (each file is fetched once). */
export function loadTopic(manifestUrl, topic) {
  const url = topicUrl(manifestUrl, topic);
  if (!topicCache.has(url)) {
    const pending = getJson(url).then((data) => ({
      topic: data.topic || topic.slug,
      guide: data.guide || null,
      items: Array.isArray(data.items) ? data.items : [],
    }));
    pending.catch(() => topicCache.delete(url));
    topicCache.set(url, pending);
  }
  return topicCache.get(url);
}

// Held in a variable so that tooling does not require the optional file to exist.
const GENERATORS_MODULE = './generators/index.js';
let generatorsModule;

/**
 * slug -> [{ key, label, make(rng) }]. The generators module is optional:
 * when it is missing or broken every topic simply has none.
 */
export async function loadGenerators() {
  if (generatorsModule === undefined) {
    try {
      generatorsModule = await import(/* @vite-ignore */ GENERATORS_MODULE);
    } catch {
      generatorsModule = null;
    }
  }
  const mod = generatorsModule;
  return (slug) => {
    if (!mod || typeof mod.generatorsFor !== 'function') return [];
    try {
      const list = mod.generatorsFor(slug);
      return Array.isArray(list) ? list.filter((g) => g && typeof g.make === 'function') : [];
    } catch {
      return [];
    }
  };
}
