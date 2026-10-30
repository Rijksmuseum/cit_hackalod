// Sections fade in as they scroll into view. Without IntersectionObserver
// (or with reduced motion) everything simply stays visible.
(() => {const reveal = document.querySelectorAll('.js-reveal')
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const waakhond = new IntersectionObserver((regels) => {
      for (const r of regels) {
        if (r.isIntersecting) {
          r.target.classList.add('is-zichtbaar')
          waakhond.unobserve(r.target)
        }
      }
    }, { rootMargin: '0px 0px -8% 0px' })
    reveal.forEach((el) => waakhond.observe(el))
  } else {
    reveal.forEach((el) => el.classList.add('is-zichtbaar'))
  }
  
})()

// Safety net: if #app is still hidden after a few seconds (the module script did
// not run at all, e.g. on file://), show the explanation.
setTimeout(() => {
  const app = document.getElementById('app')
  if (app && app.hasAttribute('v-cloak')) document.getElementById('laadfout').hidden = false
}, 4000)
