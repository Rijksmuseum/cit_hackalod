// The film loops silently. It pauses when scrolled out of view, does not start
// at all for visitors who prefer reduced motion, and has a pause button (WCAG 2.2.2).
(() => {
  const film = document.getElementById('film')
  const knop = document.getElementById('filmPauze')
  if (!film || !knop) return

  let handmatigGepauzeerd = matchMedia('(prefers-reduced-motion: reduce)').matches

  const toon = () => {
    knop.setAttribute('aria-pressed', String(film.paused))
    knop.setAttribute('aria-label', film.paused ? 'Film afspelen' : 'Film pauzeren')
  }

  if (handmatigGepauzeerd) film.pause()
  film.addEventListener('play', toon)
  film.addEventListener('pause', toon)

  knop.addEventListener('click', () => {
    handmatigGepauzeerd = !film.paused
    film.paused ? film.play() : film.pause()
  })

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([r]) => {
      if (handmatigGepauzeerd) return
      r.isIntersecting ? film.play().catch(() => {}) : film.pause()
    }, { threshold: 0.2 }).observe(film)
  }
  toon()
})()
