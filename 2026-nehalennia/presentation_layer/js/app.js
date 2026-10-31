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

  const [collectie, verhaal, perioden] = await Promise.all([
    laad('data/collectie.json'),
    laad('data/verhaal.json'),
    laad('data/perioden.json'),
  ])

  // The RMO image proxy rate-limits when a whole grid loads at once, and a few
  // images are genuinely unavailable (403). Both are tracked per RMO object.
  // A piece is either an 'altaardossier' (altar + linked RMA prints) or an RMO object.
  const alleStukken = collectie.stukken
  for (const stuk of alleStukken) {
    stuk.mislukt = false
    stuk.pogingen = 0
    stuk.zoektekst = [
      stuk.titel, stuk.objectnaam, stuk.vindplaats, stuk.edcsId, stuk.recordnummer,
      (stuk.opschrift || []).join(' '),
      (stuk.prenten || []).map((p) => `${p.objectnummer} ${p.toont}`).join(' '),
    ].join(' ').toLowerCase()
  }
  const SOORTEN = [
    { sleutel: 'alle', label: 'Alles', hoort: () => true },
    { sleutel: 'dossier', label: 'Altaren met prenten', hoort: (o) => o.soort === 'dossier' },
    { sleutel: 'altaar', label: 'RMO-altaren', hoort: (o) => o.soort === 'rmo' && o.objectnaam === 'altaar' },
    { sleutel: 'bouwfragment', label: 'Bouwfragmenten', hoort: (o) => o.objectnaam === 'bouwfragment' },
    { sleutel: 'glasnegatief', label: 'Glasnegatieven', hoort: (o) => o.objectnaam === 'glasnegatief' },
    { sleutel: 'overig', label: 'Overig', hoort: (o) => o.soort === 'rmo' && !['altaar', 'bouwfragment', 'glasnegatief'].includes(o.objectnaam) },
  ]
  const INSTELLINGEN = [
    { sleutel: 'alle', label: 'Alle instellingen' },
    { sleutel: 'RMO', label: 'RMO' },
    { sleutel: 'RMA', label: 'RMA' },
  ]
  const STUKKEN_PER_KEER = 12
  const IIIF = 'https://iiif.micr.io/'

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
    STUKKEN_PER_KEER,
    soort: 'alle',
    instelling: 'alle',
    zoek: '',
    zichtbaar: STUKKEN_PER_KEER,
    gekozen: null,
    prentIndex: 0,
    instellingen: INSTELLINGEN,
    get filters() {
      return SOORTEN.map((f) => ({ sleutel: f.sleutel, label: f.label, aantal: alleStukken.filter(f.hoort).length }))
    },
    get gefilterdeStukken() {
      const hoort = SOORTEN.find((f) => f.sleutel === this.soort).hoort
      const q = this.zoek.trim().toLowerCase()
      return alleStukken.filter(
        (o) => hoort(o) && (this.instelling === 'alle' || o.instelling === this.instelling) && (!q || o.zoektekst.includes(q)),
      )
    },
    get getoondeStukken() {
      return this.gefilterdeStukken.slice(0, this.zichtbaar)
    },
    get actievePrent() {
      return this.gekozen?.prenten?.[this.prentIndex] ?? {}
    },
    kiesSoort(sleutel) {
      this.soort = sleutel
      this.zichtbaar = STUKKEN_PER_KEER
    },
    kiesInstelling(sleutel) {
      this.instelling = sleutel
      this.zichtbaar = STUKKEN_PER_KEER
    },
    toonMeer() {
      this.zichtbaar += STUKKEN_PER_KEER
    },
    naam(o) {
      if (o.titel && o.titel !== 'Zonder titel') return o.titel
      return o.objectnaam ? o.objectnaam.charAt(0).toUpperCase() + o.objectnaam.slice(1) : 'Zonder titel'
    },
    miniatuur: (id) => `${IIIF}${id}/full/!240,240/0/default.jpg`,
    middel: (id) => `${IIIF}${id}/full/!640,640/0/default.jpg`,
    /** The print shown as the tile picture: the first one that has an image (originals come first). */
    hoofdprent: (o) => o.prenten.find((p) => p.beeld) || null,
    nummers(o) {
      const eerste = o.prenten.slice(0, 3).map((p) => p.objectnummer).join(', ')
      return o.prenten.length > 3 ? `${eerste} en ${o.prenten.length - 3} meer` : eerste
    },
    twijfel: (o) => o.prenten.filter((p) => p.zekerheid !== 'zeker').length,
    grootBeeld: (id) => `${IIIF}${id}/full/!1600,1600/0/default.jpg`,
    /** If the sized variant is not served, fall back once to the full image, then give up. */
    prentFout(event, prent) {
      const img = event.target
      if (!img.dataset.terug && prent.beeld) {
        img.dataset.terug = '1'
        img.src = `${IIIF}${prent.beeld}/full/max/0/default.jpg`
      } else {
        img.hidden = true
      }
    },
    async kopieer(tekst, event) {
      const knop = event.currentTarget
      try {
        await navigator.clipboard.writeText(tekst)
        knop.textContent = 'Gekopieerd'
      } catch {
        knop.textContent = tekst   // clipboard blocked: show the number so it can be selected
      }
      setTimeout(() => { knop.textContent = 'Kopieer nr.' }, 1600)
    },
    open(o) {
      this.gekozen = o
      this.prentIndex = 0
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
      if (lijst.length) this.open(lijst[Math.floor(Math.random() * lijst.length)])
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
