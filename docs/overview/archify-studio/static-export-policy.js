// Local packaging policy for script-free exports from the pinned Studio renderer.
function sanitizeStaticSvg(root, title) {
  root.setAttribute('role', 'img');
  root.setAttribute('aria-label', title + ' diagram');
  for (const element of [root, ...root.querySelectorAll('*')]) {
    if (element.tagName && element.tagName.toLowerCase() === 'style') {
      element.textContent = element.textContent.replace(
        /(^|\n)[^\n{}]*\.graph-(?:node|edge)[^{]*\{[^{}]*\}/g,
        rule => /:hover|:focus|\bcursor\s*:/.test(rule) ? '' : rule
      );
    }
    if (element.getAttribute('role') === 'button') {
      element.removeAttribute('role');
      element.removeAttribute('aria-label');
    }
    for (const name of ['tabindex', 'focusable', 'aria-pressed', 'aria-expanded', 'aria-controls']) {
      element.removeAttribute(name);
    }
  }
}
