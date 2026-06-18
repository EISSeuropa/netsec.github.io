/* Roadmap shipped-releases collapse toggle (shared EN/FR/DE).
 *
 * Extracted from the identical inline scripts of roadmap.html /
 * .fr.html / .de.html (issue #725). Collapses all but the most recent
 * shipped releases behind a "Show N earlier releases" button; labels
 * come from the lang-keyed table below via <html lang>.
 */
(function () {
  const lang = (document.documentElement.lang || 'en').toLowerCase().slice(0, 2);
  const L = ({
    en: {
      show: (n) => n === 1 ? 'Show 1 earlier release' : `Show ${n} earlier releases`,
      hide: 'Hide earlier releases',
    },
    fr: {
      show: (n) => n === 1 ? 'Afficher la version précédente' : `Afficher les ${n} versions précédentes`,
      hide: 'Masquer les versions précédentes',
    },
    de: {
      show: (n) => n === 1 ? 'Eine frühere Version anzeigen' : `${n} frühere Versionen anzeigen`,
      hide: 'Frühere Versionen ausblenden',
    },
  })[lang] || ({
    show: (n) => `Show ${n} earlier releases`,
    hide: 'Hide earlier releases',
  });

  function chevronSvg() {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    svg.classList.add('rm-shipped-chevron');
    const poly = document.createElementNS(ns, 'polyline');
    poly.setAttribute('points', '6 9 12 15 18 9');
    svg.appendChild(poly);
    return svg;
  }

  document.querySelectorAll('ol.rm-timeline').forEach((ol) => {
    const shipped = ol.querySelectorAll(":scope > .rm-entry.shipped:not(.rm-milestone)");
    // Keep the most recent shipped card visible and collapse the
    // earlier ones. With one shipped card (or none) there is nothing to
    // collapse, so no toggle is injected.
    if (shipped.length <= 1) return;
    const collapsible = Array.prototype.slice.call(shipped, 0, -1);
    collapsible.forEach((el) => el.classList.add('rm-shipped-collapsible'));
    const n = collapsible.length;

    const li = document.createElement('li');
    li.className = 'rm-shipped-toggle';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rm-shipped-btn';
    btn.setAttribute('aria-expanded', 'false');
    btn.appendChild(chevronSvg());
    const lbl = document.createElement('span');
    lbl.className = 'lbl';
    lbl.textContent = L.show(n);
    btn.appendChild(lbl);
    li.appendChild(btn);

    ol.insertBefore(li, shipped[0]);
    ol.dataset.shippedState = 'collapsed';

    btn.addEventListener('click', () => {
      const wasExpanded = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!wasExpanded));
      ol.dataset.shippedState = wasExpanded ? 'collapsed' : 'expanded';
      lbl.textContent = wasExpanded ? L.show(n) : L.hide;
    });
  });
})();
