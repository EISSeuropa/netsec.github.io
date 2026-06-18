/* Slide-templates gallery (/slides.html).
 *
 * Two jobs, both vanilla and progressive-enhancement only:
 *
 *  1. Crisp scaled previews. Each template is the real 1920×1080 markup
 *     wrapped in a `.slide-stage` (a 16:9 clip box). We set a `--scale`
 *     custom property on the stage equal to stageWidth / 1920; CSS applies
 *     `transform: scale(var(--scale))` to the slide, so the preview is a
 *     true vector down-scale that stays sharp at any card width. A
 *     ResizeObserver keeps it exact as the grid reflows.
 *
 *  2. Save one slide as PDF. Clicking a card's "Save as PDF" clones that
 *     slide into #slide-print-stage at full size and calls window.print().
 *     The print stylesheet (site.css) sets `@page { size: 1920px 1080px
 *     landscape; margin: 0 }` and hides everything except the clone, so the
 *     browser's "Save as PDF" yields one clean slide. `afterprint` clears
 *     the clone. No dependency, no network, no install.
 */
(function () {
  'use strict';

  var stages = Array.prototype.slice.call(document.querySelectorAll('.slide-stage'));
  var BASE = 1920;

  function fit(stage) {
    var w = stage.clientWidth;
    if (w > 0) {
      stage.style.setProperty('--scale', (w / BASE).toFixed(5));
    }
  }

  function fitAll() {
    stages.forEach(fit);
  }

  fitAll();

  if ('ResizeObserver' in window) {
    var ro = new ResizeObserver(function (entries) {
      entries.forEach(function (entry) { fit(entry.target); });
    });
    stages.forEach(function (stage) { ro.observe(stage); });
  } else {
    window.addEventListener('resize', fitAll);
  }

  // ---- Save a single slide as PDF -------------------------------------
  var printStage = document.getElementById('slide-print-stage');
  var isPrinting = false;

  function clearPrint() {
    document.body.classList.remove('is-printing-slide');
    if (printStage) { printStage.textContent = ''; }
    isPrinting = false;
  }

  document.querySelectorAll('.slide-save').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.getAttribute('data-target');
      var slide = id && document.getElementById(id);
      if (!slide || !printStage) { return; }
      printStage.textContent = '';
      var clone = slide.cloneNode(true);
      clone.removeAttribute('id');
      printStage.appendChild(clone);
      document.body.classList.add('is-printing-slide');
      isPrinting = true;
      window.print();
    });
  });

  // Most browsers fire afterprint synchronously after the dialog closes;
  // the timeout is a belt-and-braces cleanup for any that do not.
  window.addEventListener('afterprint', function () { if (isPrinting) { clearPrint(); } });
})();
