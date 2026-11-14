// static/js/session/save_queue.js
// Background saves: the UI moves on at once, the POSTs run one at a time in
// order, each retried with a short backoff. A save that still fails is kept
// (never dropped) so it can be reported and retried.

const DEFAULT_DELAYS = [1000, 3000];

/**
 * createSaveQueue({ delays, onFail, onChange })
 *   delays   ms to wait before each retry; length = number of retries.
 *   onFail   (job) => void, once a job has used all its retries.
 *   onChange ({ pending, failed }) => void, whenever either count changes.
 *
 * A job's `send()` resolves truthy when the server acknowledged the save;
 * resolving falsy or throwing counts as a failed try.
 */
export function createSaveQueue(opts = {}) {
  const delays = opts.delays || DEFAULT_DELAYS;
  let chain = Promise.resolve();
  let pending = 0;
  let failed = [];
  let wake = null;

  const call = (fn, arg) => {
    if (!fn) return;
    try {
      fn(arg);
    } catch (e) {
      console.error('[session] save queue callback failed:', e);
    }
  };
  const notify = () => call(opts.onChange, { pending, failed: failed.length });

  function wait(ms) {
    return new Promise((resolve) => {
      const done = () => {
        clearTimeout(timer);
        wake = null;
        resolve();
      };
      const timer = setTimeout(done, ms);
      wake = done;
    });
  }

  async function run(job) {
    for (let attempt = 0; ; attempt++) {
      let ok = false;
      try {
        ok = !!(await job.send());
      } catch (e) {
        console.error('[session] save failed:', job.label || '', e);
      }
      if (ok) return true;
      if (attempt >= delays.length) return false;
      await wait(delays[attempt]);
    }
  }

  /** Queue a save; resolves true (saved) or false (failed after retries). */
  function enqueue(send, label) {
    const job = { send, label };
    pending++;
    notify();
    const result = chain
      .then(() => run(job))
      .then((ok) => {
        pending--;
        if (!ok) failed.push(job);
        notify();
        if (!ok) call(opts.onFail, job);
        return ok;
      });
    chain = result;
    return result;
  }

  /** Resolves once nothing is in flight: true when no save is left failed. */
  function settle() {
    const seen = chain;
    return seen.then(() => (chain === seen ? failed.length === 0 : settle()));
  }

  /** Send every failed save again (with fresh retries). */
  function retryFailed() {
    const jobs = failed;
    failed = [];
    jobs.forEach((job) => enqueue(job.send, job.label));
    return settle();
  }

  /** Skip the current backoff, e.g. when the page is about to be hidden. */
  function hurry() {
    if (wake) wake();
  }

  return {
    enqueue,
    settle,
    retryFailed,
    hurry,
    get pending() {
      return pending;
    },
    get failed() {
      return failed.length;
    },
  };
}
