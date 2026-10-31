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

  const [objecten, verhaal, perioden] = await Promise.all([
    laad('data/objecten.json'),
    laad('data/verhaal.json'),
    laad('data/perioden.json'),
  ])

  // --- objects: every field of data/objecten.json is used somewhere ---
  const RMA = 'Rijksmuseum Amsterdam'
  const IIIF_MAX = '/full/max/0/default.jpg'
  const hoofdletter = (t) => t.charAt(0).toUpperCase() + t.slice(1)
  const edcsId = (url) => 'EDCS-' + url.split('/').pop().padStart(8, '0')

  /** 'Nederland, Zeeland, Noord-Beveland, Colijnsplaat, Oosterschelde' -> 'Colijnsplaat (Oosterschelde)'. */
  function korteVindplaats(waarde) {
    if (!waarde) return null
    const delen = waarde.split('|').map((vp) => {
      const d = vp.split(',').map((x) => x.trim()).filter((x) => x && x !== 'Onbekend')
      if (!d.length) return null
      if (d.length === 1) return d[0]
      const land = d[0]
      const plaats = land === 'Nederland' ? d[3] || d[d.length - 1] : d[3] || d[d.length - 1]
      const extra = d.slice(4).join(', ')
      const naam = extra ? `${plaats} (${extra})` : plaats
      return land === 'Nederland' ? naam : `${naam}, ${land}`
    }).filter(Boolean)
    return delen.length ? delen.join(' · ') : 'Onbekend'
  }

  const jaar = (n) => (n < 1000 ? `${n} n.Chr.` : String(n))
  function periodeTekst(van, tot) {
    if (van == null && tot == null) return null
    if (van == null || tot == null || van === tot) return jaar(van ?? tot)
    return tot < 1000 ? `${van}–${tot} n.Chr.` : `${van}–${tot}`
  }

  const perPeriode = {}
  for (const p of perioden.perioden) perPeriode[p.period_id] = p
  const perId = {}
  for (const o of objecten) {
    const rma = o.bron === RMA
    const namen = (o.objectnaam || 'onbekend').split(/\n|;/).map((x) => x.trim()).filter(Boolean)
    const eerst = namen[0].toLowerCase()
    const groep = rma || ['prent', 'gravure'].includes(eerst) ? 'prent'
      : eerst.startsWith('altaar') ? 'altaar'
      : ['bouwfragment', 'glasnegatief'].includes(eerst) ? eerst : 'overig'
    const afbeelding = o.image_url && rma ? o.image_url.replace(IIIF_MAX, '/full/!640,640/0/default.jpg') : o.image_url
    const stuk = {
      id: o.pid,
      pid: o.pid,
      bron: o.bron,
      rma,
      groep,
      objectnummer: o.objectnummer,
      titel: o.titel?.trim() || hoofdletter(namen[0]),
      soort: hoofdletter(namen[0]),
      soortTekst: namen.map(hoofdletter).join(' · '),
      beschrijving: o.beschrijving?.trim() || null,
      plaats: korteVindplaats(o.vindplaats),
      plaatsVolledig: o.vindplaats ? o.vindplaats.split('|').map((x) => x.trim()).join('  |  ') : null,
      datering: periodeTekst(o.datering_datum_start, o.datering_datum_eind),
      gevonden: periodeTekst(o.gevonden_datum_van, o.gevonden_datum_tot),
      afbeelding,
      afbeeldingGroot: o.image_url && rma ? o.image_url.replace(IIIF_MAX, '/full/!1600,1600/0/default.jpg') : o.image_url,
      miniatuur: o.image_url && rma ? o.image_url.replace(IIIF_MAX, '/full/!240,240/0/default.jpg') : o.image_url,
      opschrift: o.inscripties_text ? o.inscripties_text.split(' / ').map((x) => x.trim()) : [],
      vertaling: o.edcs_vertaling_concept,
      edcs: [...new Set(o.inscripties)].map((url) => ({ url, id: edcsId(url) })),
      periodes: o.period_ids.map((id) => perPeriode[id]).filter(Boolean),
      // RMO pids are handles; RMA pids point to the linked-data record, the public page is behind id.rijksmuseum.nl
      bronLink: rma ? o.pid.replace('https://data.rijksmuseum.nl/', 'https://id.rijksmuseum.nl/') : o.pid,
      mislukt: false,
      pogingen: 0,
    }
    stuk.periodeTekst = stuk.periodes.map((p) => p.kort).join(', ')
    // the same linked pid can appear twice (via inscription and via research): merge, keep the best score
    const rel = {}
    for (const l of o.linked_objecten) {
      const r = (rel[l.pid] ||= { id: l.pid, vias: [], score: 0 })
      if (!r.vias.includes(l.via)) r.vias.push(l.via)
      r.score = Math.max(r.score, l.score)
    }
    stuk.relaties = Object.values(rel).sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
    stuk.zoektekst = [stuk.titel, stuk.soortTekst, stuk.objectnummer, stuk.plaatsVolledig, stuk.beschrijving,
      stuk.opschrift.join(' '), stuk.vertaling, stuk.edcs.map((e) => e.id).join(' ')].join(' ').toLowerCase()
    perId[o.pid] = stuk
  }
  // linked objects first, then objects with a picture
  const alleStukken = Object.values(perId).sort(
    (a, b) => b.relaties.length - a.relaties.length || Number(!!b.afbeelding) - Number(!!a.afbeelding),
  )
  for (const p of perioden.perioden) p.aantal = alleStukken.filter((o) => o.periodes.includes(p)).length
  const zonderPeriode = alleStukken.filter((o) => !o.periodes.length).length

  const SOORTEN = [
    { sleutel: 'alle', label: 'Alles', hoort: () => true },
    { sleutel: 'altaar', label: 'Altaren', hoort: (o) => o.groep === 'altaar' },
    { sleutel: 'prent', label: 'Prenten', hoort: (o) => o.groep === 'prent' },
    { sleutel: 'bouwfragment', label: 'Bouwfragmenten', hoort: (o) => o.groep === 'bouwfragment' },
    { sleutel: 'glasnegatief', label: 'Glasnegatieven', hoort: (o) => o.groep === 'glasnegatief' },
    { sleutel: 'overig', label: 'Overig', hoort: (o) => o.groep === 'overig' },
  ]
  const INSTELLINGEN = [
    { sleutel: 'alle', label: 'Alle instellingen' },
    { sleutel: 'RMO', label: 'RMO' },
    { sleutel: 'RMA', label: 'RMA' },
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

    // --- collectiestukken ---
    alle: alleStukken,
    STUKKEN_PER_KEER,
    soort: 'alle',
    instelling: 'alle',
    periodeFilter: 'alle',
    alleenGekoppeld: false,
    zoek: '',
    zichtbaar: STUKKEN_PER_KEER,
    gekozen: null,
    vorige: [],
    instellingen: INSTELLINGEN,
    zonderPeriode,
    get filters() {
      return SOORTEN.map((f) => ({ sleutel: f.sleutel, label: f.label, aantal: alleStukken.filter(f.hoort).length }))
    },
    get gefilterdeStukken() {
      const hoort = SOORTEN.find((f) => f.sleutel === this.soort).hoort
      const q = this.zoek.trim().toLowerCase()
      const pf = this.periodeFilter
      return alleStukken.filter(
        (o) => hoort(o)
          && (this.instelling === 'alle' || (this.instelling === 'RMA') === o.rma)
          && (pf === 'alle' || (pf === 'geen' ? !o.periodes.length : o.periodes.some((p) => p.period_id === pf)))
          && (!this.alleenGekoppeld || o.relaties.length)
          && (!q || o.zoektekst.includes(q)),
      )
    },
    get getoondeStukken() {
      return this.gefilterdeStukken.slice(0, this.zichtbaar)
    },
    kiesSoort(sleutel) {
      this.soort = sleutel
      this.zichtbaar = STUKKEN_PER_KEER
    },
    kiesInstelling(sleutel) {
      this.instelling = sleutel
      this.zichtbaar = STUKKEN_PER_KEER
    },
    kiesPeriode(id) {
      this.periodeFilter = id
      this.zichtbaar = STUKKEN_PER_KEER
      this.sluit()
      document.getElementById('collectie').scrollIntoView({ behavior: 'smooth' })
    },
    /** From the timeline: show the objects of the period that is open. */
    bekijkPeriode(id) {
      this.soort = 'alle'
      this.instelling = 'alle'
      this.alleenGekoppeld = false
      this.zoek = ''
      this.kiesPeriode(id)
    },
    jarenTekst(p) {
      return p.datum_tot > 2030 ? `vanaf ${p.datum_van}` : `${p.datum_van}–${p.datum_tot}`
    },
    toonMeer() {
      this.zichtbaar += STUKKEN_PER_KEER
    },
    obj: (id) => perId[id],

    /** RMO images come from an image proxy that rate-limits: retry twice, then show a placeholder.
     *  For RMA images (IIIF) the sized variant falls back once to the full image first. */
    beeldFout(o, event) {
      const img = event.target
      if (o.rma && !img.dataset.terug) {
        img.dataset.terug = '1'
        img.src = o.afbeeldingGroot.replace(/\/full\/[^/]+\/0\/default\.jpg/, IIIF_MAX)
        return
      }
      o.pogingen += 1
      if (o.pogingen > MAX_POGINGEN) {
        o.mislukt = true
        return
      }
      setTimeout(() => { img.src = `${img.src.split('?')[0]}?poging=${o.pogingen}` }, 700 * o.pogingen)
    },
    miniFout(event) {
      event.target.hidden = true
    },
    open(o, vanuitDetail = false) {
      if (vanuitDetail && this.gekozen) this.vorige.push(this.gekozen)
      else if (!vanuitDetail) this.vorige = []
      this.gekozen = o
      const dialoog = document.getElementById('lichtbak')
      if (!dialoog.open) dialoog.showModal()
      dialoog.scrollTop = 0
    },
    terug() {
      this.gekozen = this.vorige.pop()
      document.getElementById('lichtbak').scrollTop = 0
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
      return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'][i] ?? String(i + 1)
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
