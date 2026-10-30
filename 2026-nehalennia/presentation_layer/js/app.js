const PETITE_VUE = 'https://unpkg.com/petite-vue@0.4.1/dist/petite-vue.es.js'

async function start() {
  const { createApp } = await import(PETITE_VUE)
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

  const [tijdlijn, verhaal, perioden] = await Promise.all([
    laad('data/timeline.json'),
    laad('data/verhaal.json'),
    laad('data/perioden.json'),
  ])

  // The RMO image proxy rate-limits when a whole grid loads at once, and a few
  // images are genuinely unavailable (403). Both are tracked per object.
  for (const jaar of tijdlijn.jaren) {
    for (const object of jaar.objecten) {
      object.mislukt = false
      object.pogingen = 0
    }
  }

  // every object once, for the collection overview (the years in timeline.json are
  // demo data and are not shown any more)
  const alleStukken = tijdlijn.jaren.flatMap((j) => j.objecten)
  const SOORTEN = [
    { sleutel: 'alle', label: 'Alles', hoort: () => true },
    { sleutel: 'altaar', label: 'Altaren', hoort: (o) => o.objectnaam === 'altaar' },
    { sleutel: 'bouwfragment', label: 'Bouwfragmenten', hoort: (o) => o.objectnaam === 'bouwfragment' },
    { sleutel: 'glasnegatief', label: 'Glasnegatieven', hoort: (o) => o.objectnaam === 'glasnegatief' },
    { sleutel: 'overig', label: 'Overig', hoort: (o) => !['altaar', 'bouwfragment', 'glasnegatief'].includes(o.objectnaam) },
  ]
  const STUKKEN_PER_KEER = 12

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


    // --- tijdlijn: vijf perioden ---
    perioden: perioden.perioden,
    periode: 0,
    get huidigePeriode() {
      return this.perioden[this.periode]
    },
    get voortgang() {
      return this.periode / (this.perioden.length - 1)
    },
    periodeToets(event, i) {
      const volgende = volgendeIndex(event, i, this.perioden.length)
      if (volgende === null) return
      this.periode = volgende
      richtFocus(event, '.tijdas', volgende)
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

    // --- collectiestukken ---
    soort: 'alle',
    zichtbaar: STUKKEN_PER_KEER,
    gekozen: null,
    get filters() {
      return SOORTEN.map((f) => ({ sleutel: f.sleutel, label: f.label, aantal: alleStukken.filter(f.hoort).length }))
    },
    get gefilterdeStukken() {
      return alleStukken.filter(SOORTEN.find((f) => f.sleutel === this.soort).hoort)
    },
    get getoondeStukken() {
      return this.gefilterdeStukken.slice(0, this.zichtbaar)
    },
    kiesSoort(sleutel) {
      this.soort = sleutel
      this.zichtbaar = STUKKEN_PER_KEER
    },
    toonMeer() {
      this.zichtbaar += STUKKEN_PER_KEER
    },
    naam(o) {
      if (o.titel && o.titel !== 'Zonder titel') return o.titel
      return o.objectnaam ? o.objectnaam.charAt(0).toUpperCase() + o.objectnaam.slice(1) : 'Zonder titel'
    },
    open(o) {
      this.gekozen = o
      document.getElementById('lichtbak').showModal()
    },
    sluit() {
      document.getElementById('lichtbak').close()
    },
    sluitOpAchtergrond(event) {
      if (event.target.id === 'lichtbak') this.sluit()   // a click on the backdrop
    },
    verras() {
      const lijst = this.gefilterdeStukken
      this.open(lijst[Math.floor(Math.random() * lijst.length)])
    },

    // --- gedeeld ---
    nummer(i) {
      return String(i + 1).padStart(2, '0')
    },
  }).mount('#app')
}

// If petite-vue or a data file cannot be loaded (offline, or the page was opened
// as a file:// URL, where fetch() is blocked), say so instead of showing nothing.
start().catch((fout) => {
  console.error(fout)
  document.getElementById('laadfoutDetail').textContent = String(fout && fout.message ? fout.message : fout)
  document.getElementById('laadfout').hidden = false
})
