/* Slide-templates gallery (/slides.html).
 *
 * Crisp scaled previews. Each template is the real 1920×1080 markup wrapped
 * in a `.slide-stage` (a 16:9 clip box). We set a `--scale` custom property
 * on the stage equal to stageWidth / 1920; CSS applies `transform:
 * scale(var(--scale))` to the slide, so the preview is a true vector
 * down-scale that stays sharp at any card width. A ResizeObserver keeps it
 * exact as the grid reflows. Progressive enhancement: with JS off the CSS
 * default scale still renders a (slightly off) preview.
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
})();
