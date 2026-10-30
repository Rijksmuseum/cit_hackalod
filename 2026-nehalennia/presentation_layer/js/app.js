import { createApp } from 'https://unpkg.com/petite-vue@0.4.1/dist/petite-vue.es.js'

const PER_PAGINA = 8
const MAX_POGINGEN = 2


async function laad(pad) {
  const res = await fetch(pad)
  if (!res.ok) throw new Error(`${pad} gaf ${res.status}`)
  return res.json()
}

/** Move focus between tab-like buttons with the arrow keys. */
function volgendeIndex(event, huidig, lengte) {
  const stap = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key]
  if (stap === undefined) {
    if (event.key === 'Home') return 0
    if (event.key === 'End') return lengte - 1
    return null
  }
  return (huidig + stap + lengte) % lengte
}

function richtFocus(event, selector, index) {
  event.preventDefault()
  // petite-vue updates the DOM on the next tick, so wait before moving focus
  requestAnimationFrame(() => {
    const knoppen = event.target.closest(selector).querySelectorAll('button')
    knoppen[index]?.focus()
  })
}

const [tijdlijn, verhaal] = await Promise.all([
  laad('data/timeline.json'),
  laad('data/verhaal.json'),
])

// The RMO image proxy rate-limits when a whole grid loads at once, and a few
// images are genuinely unavailable (403). Both are tracked per object.
for (const jaar of tijdlijn.jaren) {
  for (const object of jaar.objecten) {
    object.mislukt = false
    object.pogingen = 0
  }
}

const eersteGevuld = tijdlijn.jaren.find((j) => j.objecten.length) ?? tijdlijn.jaren[0]

createApp({
  // --- verhaal ---
  stappen: verhaal.stappen,
  stap: 0,
  get huidigeStap() {
    return this.stappen[this.stap]
  },
  stapToets(event, i) {
    const volgende = volgendeIndex(event, i, this.stappen.length)
    if (volgende === null) return
    this.stap = volgende
    richtFocus(event, '.stappen', volgende)
  },


  // --- tijdlijn ---
  jaren: tijdlijn.jaren,
  bronnen: tijdlijn.bronnen,
  actiefJaar: eersteGevuld.jaar,
  pagina: 1,
  perPagina: PER_PAGINA,

  get jaar() {
    return this.jaren.find((j) => j.jaar === this.actiefJaar)
  },
  get totaalPaginas() {
    return Math.max(1, Math.ceil(this.jaar.objecten.length / this.perPagina))
  },
  get zichtbareObjecten() {
    const start = (this.pagina - 1) * this.perPagina
    return this.jaar.objecten.slice(start, start + this.perPagina)
  },
  kiesJaar(jaar) {
    this.actiefJaar = jaar
    this.pagina = 1
  },
  blader(richting) {
    this.pagina = Math.min(this.totaalPaginas, Math.max(1, this.pagina + richting))
  },
  jaarToets(event, jaar) {
    const i = this.jaren.findIndex((j) => j.jaar === jaar)
    const volgende = volgendeIndex(event, i, this.jaren.length)
    if (volgende === null) return
    this.kiesJaar(this.jaren[volgende].jaar)
    richtFocus(event, '.jaren', volgende)
  },

  /** Retry a failed image twice with a growing delay, then show a placeholder. */
  beeldMislukt(object, event) {
    object.pogingen += 1
    if (object.pogingen > MAX_POGINGEN) {
      object.mislukt = true
      return
    }
    const img = event.target
    // the proxy ignores the query string, so it only serves to dodge the cache
    setTimeout(() => {
      img.src = `${object.afbeelding}?poging=${object.pogingen}`
    }, 700 * object.pogingen)
  },

  // --- gedeeld ---
  nummer(i) {
    return String(i + 1).padStart(2, '0')
  },
}).mount('#app')
