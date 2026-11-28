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

let generatorsModule;

/**
 * slug -> [{ key, label, make(rng) }]. The generators module is optional.
 * `url` is its URL when the server has the file (the template checks) and ''
 * when it does not: then nothing is requested, so a missing module leaves no
 * failed request in the console. A module that fails to load or to run is
 * ignored the same way: every topic simply has no generators.
 */
export async function loadGenerators(url) {
  if (generatorsModule === undefined) {
    generatorsModule = null;
    if (url) {
      try {
        generatorsModule = await import(/* @vite-ignore */ url);
      } catch {
        generatorsModule = null;
      }
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
