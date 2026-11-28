// /grammar-drill and /idiom-trainer have no language in their address: go to
// the page of the study language (selectedLanguageId: 1 Chinese, 3 Japanese).
// Chinese is the default. The base path comes from the script tag's data-base
// (default /grammar-drill).
(function () {
  const tag = document.currentScript;
  const base = (tag && tag.dataset.base) || '/grammar-drill';
  let id = null;
  try {
    id = parseInt(window.localStorage.getItem('selectedLanguageId'), 10);
  } catch (_e) {
    id = null;
  }
  window.location.replace(`${base}/${id === 3 ? 'ja' : 'zh'}`);
})();
