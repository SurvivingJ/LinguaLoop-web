// /grammar-drill has no language in its address: go to the page of the study
// language (selectedLanguageId: 1 Chinese, 3 Japanese). Chinese is the default,
// as it was the only grammar drill at this address.
(function () {
  let id = null;
  try {
    id = parseInt(window.localStorage.getItem('selectedLanguageId'), 10);
  } catch (_e) {
    id = null;
  }
  window.location.replace(id === 3 ? '/grammar-drill/ja' : '/grammar-drill/zh');
})();
