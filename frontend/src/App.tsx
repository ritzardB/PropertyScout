
import { useEffect, useState, type FormEvent } from 'react'
import {
  Activity,
  Building2,
  ChartNoAxesCombined,
  ChevronDown,
  CircleHelp,
  Compass,
  Home,
  MapPin,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Warehouse,
  ArrowLeft,
  ExternalLink,
} from 'lucide-react'

type Page = 'Overview' | 'Rental discovery' | 'Sales analytics' | 'Commercial properties'

type RentalListing = {
  id: string
  title: string
  emirate: string
  property_type: string
  community: string
  annual_rent_aed: number
  bedrooms?: number | null
  area_sqft?: number | null
  source_name: string
  source_url: string
  external_listing_id?: string | null
  advertised_date?: string | null
  last_seen_date?: string | null
  availability_status: string
  availability_checked_date?: string | null
  contact_reference?: string | null
}

const propertyTypes = [
  { label: 'All properties', value: '' },
  { label: 'Apartments', value: 'Apartment' },
  { label: 'Villas', value: 'Villa' },
  { label: 'Commercial', value: 'Commercial' },
  { label: 'Offices', value: 'Office' },
  { label: 'Retail shops', value: 'Retail shop' },
  { label: 'Warehouses', value: 'Warehouse' },
  { label: 'Commercial buildings', value: 'Commercial building' },
]

const navItems: { label: Page; icon: typeof Compass }[] = [
  { label: 'Overview', icon: Compass },
  { label: 'Rental discovery', icon: Home },
  { label: 'Sales analytics', icon: ChartNoAxesCombined },
  { label: 'Commercial properties', icon: Warehouse },
]

function formatAED(amount: number) {
  return new Intl.NumberFormat('en-AE', {
    style: 'currency',
    currency: 'AED',
    maximumFractionDigits: 0,
  }).format(amount)
}

function App() {
  const [page, setPage] = useState<Page>('Overview')
  const [emirate, setEmirate] = useState('Abu Dhabi')
  const [propertyType, setPropertyType] = useState('')
  const [community, setCommunity] = useState('')
  const [minRent, setMinRent] = useState('')
  const [maxRent, setMaxRent] = useState('')
  const [apiStatus, setApiStatus] = useState('Checking connection')
  const [listings, setListings] = useState<RentalListing[]>([])
  const [hasSearched, setHasSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [searchError, setSearchError] = useState('')

  useEffect(() => {
    fetch('/api/health')
      .then((response) => {
        if (!response.ok) throw new Error('API unavailable')
        return response.json()
      })
      .then(() => setApiStatus('API connected'))
      .catch(() => setApiStatus('API offline'))
  }, [])

  async function searchRentals(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    setPage('Rental discovery')
    setLoading(true)
    setSearchError('')
    setHasSearched(true)

    const params = new URLSearchParams()
    params.set('emirate', emirate)

    if (propertyType) params.set('property_type', propertyType)
    if (community.trim()) params.set('community', community.trim())
    if (minRent.trim()) params.set('min_annual_rent', minRent.trim())
    if (maxRent.trim()) params.set('max_annual_rent', maxRent.trim())

    try {
      const response = await fetch(`/api/rentals?${params.toString()}`)
      const payload = await response.json().catch(() => null)

      if (!response.ok) {
        const detail =
          payload && typeof payload.detail === 'string'
            ? payload.detail
            : 'Rental search failed. Please check your filters and try again.'
        throw new Error(detail)
      }

      if (!Array.isArray(payload)) {
        throw new Error('The API returned an unexpected response.')
      }

      setListings(payload as RentalListing[])
    } catch (error) {
      setListings([])
      setSearchError(
        error instanceof Error
          ? error.message
          : 'Could not reach the rental API. Check that the backend is running.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0b1020] text-slate-100 md:flex">
      <aside className="flex w-full shrink-0 flex-col border-b border-white/10 bg-[#0e1528] p-5 md:min-h-screen md:w-64 md:border-r md:border-b-0">
        <button
          type="button"
          onClick={() => setPage('Overview')}
          className="mb-10 flex items-center gap-3 text-left"
          aria-label="Go to PropertyScout overview"
        >
          <div className="rounded-xl bg-cyan-400 p-2 text-slate-950">
            <Building2 size={25} />
          </div>
          <div>
            <h1 className="font-bold tracking-wide">PropertyScout</h1>
            <p className="text-xs text-slate-400">UAE PROPERTY INTELLIGENCE</p>
          </div>
        </button>

        <p className="mb-3 text-xs font-semibold tracking-widest text-slate-500">
          WORKSPACE
        </p>

        <nav className="space-y-2" aria-label="Main navigation">
          {navItems.map(({ label, icon: Icon }) => (
            <button
              type="button"
              key={label}
              onClick={() => setPage(label)}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left font-medium transition ${
                page === label
                  ? 'bg-cyan-400/10 text-cyan-300'
                  : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
              }`}
            >
              <Icon size={19} /> {label}
            </button>
          ))}
        </nav>

        <div className="mt-8 rounded-xl border border-white/10 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <Activity size={17} className="text-cyan-300" />
            Backend status
          </div>
          <p
            className={`text-sm ${
              apiStatus === 'API connected'
                ? 'text-emerald-400'
                : 'text-amber-300'
            }`}
          >
            {apiStatus}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            FastAPI · Local development
          </p>
        </div>

        <div className="mt-auto hidden space-y-4 pt-10 text-sm text-slate-400 md:block">
          <div className="flex items-center gap-3">
            <Settings2 size={17} /> Settings
          </div>
          <div className="flex items-center gap-3">
            <CircleHelp size={17} /> Help &amp; support
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 p-5 md:p-9">
        {page === 'Rental discovery' ? (
          <>
            <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
              <div>
                <button
                  type="button"
                  onClick={() => setPage('Overview')}
                  className="mb-3 inline-flex items-center gap-2 text-sm text-cyan-300 hover:text-cyan-200"
                >
                  <ArrowLeft size={16} /> Back to overview
                </button>
                <p className="mb-1 text-sm text-slate-400">PROPERTY SEARCH</p>
                <h2 className="text-2xl font-bold md:text-3xl">
                  Rental discovery
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                  Search advertised rental listings across Abu Dhabi and Dubai.
                </p>
              </div>

              <div className="flex items-center gap-2 rounded-full border border-white/10 px-4 py-2 text-sm text-slate-300">
                <ShieldCheck size={17} className="text-emerald-400" />
                Source-aware results
              </div>
            </header>

            <section className="mb-8 rounded-2xl border border-cyan-300/20 bg-gradient-to-br from-[#142843] to-[#11172a] p-6 md:p-8">
              <p className="mb-3 text-sm font-semibold text-cyan-300">
                SEARCH FILTERS
              </p>

              <form onSubmit={searchRentals}>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <label className="text-xs text-slate-400">
                    EMIRATE
                    <span className="relative mt-2 block">
                      <MapPin size={16} className="absolute left-3 top-3 text-cyan-300" />
                      <select
                        value={emirate}
                        onChange={(e) => setEmirate(e.target.value)}
                        className="w-full appearance-none rounded-lg border border-white/10 bg-[#0b1425] py-3 pl-9 pr-8 text-sm text-white outline-none focus:border-cyan-300"
                      >
                        <option>Abu Dhabi</option>
                        <option>Dubai</option>
                      </select>
                      <ChevronDown size={15} className="pointer-events-none absolute right-3 top-3 text-slate-400" />
                    </span>
                  </label>

                  <label className="text-xs text-slate-400">
                    PROPERTY TYPE
                    <span className="relative mt-2 block">
                      <select
                        value={propertyType}
                        onChange={(e) => setPropertyType(e.target.value)}
                        className="w-full appearance-none rounded-lg border border-white/10 bg-[#0b1425] px-3 py-3 pr-8 text-sm text-white outline-none focus:border-cyan-300"
                      >
                        {propertyTypes.map((type) => (
                          <option key={type.label} value={type.value}>
                            {type.label}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={15} className="pointer-events-none absolute right-3 top-3 text-slate-400" />
                    </span>
                  </label>

                  <label className="text-xs text-slate-400">
                    AREA OR COMMUNITY
                    <span className="relative mt-2 block">
                      <Search size={16} className="absolute left-3 top-3 text-slate-500" />
                      <input
                        value={community}
                        onChange={(e) => setCommunity(e.target.value)}
                        placeholder="e.g. Al Reem Island"
                        className="w-full rounded-lg border border-white/10 bg-[#0b1425] py-3 pl-9 pr-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-cyan-300"
                      />
                    </span>
                  </label>

                  <label className="text-xs text-slate-400">
                    MINIMUM ANNUAL RENT (AED)
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={minRent}
                      onChange={(e) => setMinRent(e.target.value)}
                      placeholder="No minimum"
                      className="mt-2 w-full rounded-lg border border-white/10 bg-[#0b1425] px-3 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-cyan-300"
                    />
                  </label>

                  <label className="text-xs text-slate-400">
                    MAXIMUM ANNUAL RENT (AED)
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={maxRent}
                      onChange={(e) => setMaxRent(e.target.value)}
                      placeholder="No maximum"
                      className="mt-2 w-full rounded-lg border border-white/10 bg-[#0b1425] px-3 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-cyan-300"
                    />
                  </label>

                  <div className="flex items-end">
                    <button
                      type="submit"
                      disabled={loading}
                      className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-300 px-4 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-wait disabled:opacity-60"
                    >
                      <SlidersHorizontal size={17} />
                      {loading ? 'Searching…' : 'Search rentals'}
                    </button>
                  </div>
                </div>
              </form>
            </section>

            <section aria-live="polite">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-lg font-semibold">Rental listings</h3>
                {hasSearched && !loading && !searchError && (
                  <span className="text-sm text-slate-400">
                    {listings.length} result{listings.length === 1 ? '' : 's'}
                  </span>
                )}
              </div>

              {loading && (
                <div className="rounded-2xl border border-white/10 bg-[#11192b] p-8 text-center text-slate-300">
                  Searching your rental records…
                </div>
              )}

              {!loading && searchError && (
                <div className="rounded-2xl border border-rose-400/30 bg-rose-400/5 p-6">
                  <h4 className="font-semibold text-rose-300">
                    Rental search could not be completed
                  </h4>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    {searchError}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    Check that FastAPI is running and try again.
                  </p>
                </div>
              )}

              {!loading && !searchError && !hasSearched && (
                <div className="rounded-2xl border border-white/10 bg-[#11192b] p-8 text-center">
                  <Search size={28} className="mx-auto text-cyan-300" />
                  <h4 className="mt-3 font-semibold">
                    Ready to find a rental?
                  </h4>
                  <p className="mt-2 text-sm text-slate-400">
                    Set your filters above and search the listings stored in PropertyScout.
                  </p>
                </div>
              )}

              {!loading && !searchError && hasSearched && listings.length === 0 && (
                <div className="rounded-2xl border border-white/10 bg-[#11192b] p-8 text-center">
                  <Home size={28} className="mx-auto text-cyan-300" />
                  <h4 className="mt-3 font-semibold">
                    No matching listings found
                  </h4>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    There are currently no stored listings matching these filters.
                    This does not mean no properties are available in the market.
                    Import listings from an authorized source to populate your results.
                  </p>
                </div>
              )}

              {!loading && !searchError && listings.length > 0 && (
                <div className="grid gap-4 lg:grid-cols-2">
                  {listings.map((listing) => (
                    <article
                      key={listing.id}
                      className="rounded-2xl border border-white/10 bg-[#11192b] p-5"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-medium uppercase tracking-wide text-cyan-300">
                            {listing.emirate} · {listing.property_type}
                          </p>
                          <h4 className="mt-2 text-lg font-semibold">
                            {listing.title}
                          </h4>
                          <p className="mt-1 text-sm text-slate-400">
                            {listing.community}
                          </p>
                        </div>
                        <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
                          {listing.availability_status}
                        </span>
                      </div>

                      <p className="mt-5 text-2xl font-bold text-white">
                        {formatAED(listing.annual_rent_aed)}
                        <span className="ml-1 text-sm font-normal text-slate-400">
                          / year
                        </span>
                      </p>

                      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm text-slate-400">
                        {listing.bedrooms != null && (
                          <span>{listing.bedrooms} bedrooms</span>
                        )}
                        {listing.area_sqft != null && (
                          <span>{listing.area_sqft.toLocaleString()} sqft</span>
                        )}
                        <span>Source: {listing.source_name}</span>
                      </div>

                      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
                        <p className="text-xs text-slate-500">
                          {listing.availability_checked_date
                            ? `Availability checked ${listing.availability_checked_date}`
                            : 'Advertised listing · vacancy not verified'}
                        </p>
                        <a
                          href={listing.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-2 text-sm font-medium text-cyan-300 hover:text-cyan-200"
                        >
                          View source <ExternalLink size={14} />
                        </a>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <footer className="mt-8 border-t border-white/10 pt-5 text-xs leading-6 text-slate-500">
              Advertised availability is not confirmation of vacancy. Verify details
              with the listing source before contacting clients or arranging viewings.
            </footer>
          </>
        ) : page === 'Overview' ? (
          <>
            <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="mb-1 text-sm text-slate-400">
                  UAE PROPERTY INTELLIGENCE PLATFORM
                </p>
                <h2 className="text-2xl font-bold md:text-3xl">
                  Property overview
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                  Discover opportunities. Understand markets. Find your next client.
                </p>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-white/10 px-4 py-2 text-sm text-slate-300">
                <ShieldCheck size={17} className="text-emerald-400" />
                Data-aware workspace
              </div>
            </header>

            <section className="mb-8 rounded-2xl border border-cyan-300/20 bg-gradient-to-br from-[#142843] to-[#11172a] p-6 md:p-8">
              <p className="mb-3 text-sm font-semibold text-cyan-300">
                PROPERTY DISCOVERY
              </p>
              <h3 className="max-w-2xl text-2xl font-bold md:text-3xl">
                Find properties. Uncover opportunities.
              </h3>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                Explore advertised rental opportunities across Abu Dhabi and Dubai,
                with sales-market analytics powered by your existing DLD and ADREC datasets.
              </p>

              <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <label className="text-xs text-slate-400">
                  EMIRATE
                  <span className="relative mt-2 block">
                    <MapPin size={16} className="absolute left-3 top-3 text-cyan-300" />
                    <select
                      value={emirate}
                      onChange={(e) => setEmirate(e.target.value)}
                      className="w-full appearance-none rounded-lg border border-white/10 bg-[#0b1425] py-3 pl-9 pr-8 text-sm text-white outline-none focus:border-cyan-300"
                    >
                      <option>Abu Dhabi</option>
                      <option>Dubai</option>
                    </select>
                    <ChevronDown size={15} className="pointer-events-none absolute right-3 top-3 text-slate-400" />
                  </span>
                </label>

                <label className="text-xs text-slate-400">
                  PROPERTY TYPE
                  <span className="relative mt-2 block">
                    <select
                      value={propertyType}
                      onChange={(e) => setPropertyType(e.target.value)}
                      className="w-full appearance-none rounded-lg border border-white/10 bg-[#0b1425] px-3 py-3 pr-8 text-sm text-white outline-none focus:border-cyan-300"
                    >
                      {propertyTypes.map((type) => (
                        <option key={type.label} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={15} className="pointer-events-none absolute right-3 top-3 text-slate-400" />
                  </span>
                </label>

                <div className="flex items-end">
                  <button
                    type="button"
                    onClick={() => setPage('Rental discovery')}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-300 px-4 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-200"
                  >
                    <SlidersHorizontal size={17} /> Open rental discovery
                  </button>
                </div>
              </div>
            </section>

            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Your intelligence workspace</h3>
              <span className="text-xs text-slate-500">
                Live data requires connected sources
              </span>
            </div>

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {[
                {
                  title: 'Rental discovery',
                  detail: 'Search advertised listings across both emirates',
                  icon: Home,
                  status: 'Open module',
                  action: () => setPage('Rental discovery'),
                },
                {
                  title: 'Sales comparables',
                  detail: 'Compare recorded transactions and prices',
                  icon: ChartNoAxesCombined,
                  status: 'API available',
                  action: () => setPage('Sales analytics'),
                },
                {
                  title: 'Commercial search',
                  detail: 'Offices, retail, warehouses and buildings',
                  icon: Warehouse,
                  status: 'Rental search filters',
                  action: () => setPage('Commercial properties'),
                },
              ].map(({ title, detail, icon: Icon, status, action }) => (
                <button
                  type="button"
                  key={title}
                  onClick={action}
                  className="rounded-2xl border border-white/10 bg-[#11192b] p-5 text-left transition hover:border-cyan-300/30"
                >
                  <div className="mb-5 flex items-center justify-between">
                    <div className="rounded-xl bg-white/5 p-3 text-cyan-300">
                      <Icon size={22} />
                    </div>
                    <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-400">
                      {status}
                    </span>
                  </div>
                  <h4 className="font-semibold">{title}</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {detail}
                  </p>
                </button>
              ))}
            </section>

            <footer className="mt-8 border-t border-white/10 pt-5 text-xs leading-6 text-slate-500">
              PropertyScout UAE · Advertised availability is not confirmation of vacancy.
              Rental listings require an authorized source and explicit availability status.
            </footer>
          </>
        ) : (
          <section className="rounded-2xl border border-white/10 bg-[#11192b] p-8">
            <button
              type="button"
              onClick={() => setPage('Overview')}
              className="mb-5 inline-flex items-center gap-2 text-sm text-cyan-300 hover:text-cyan-200"
            >
              <ArrowLeft size={16} /> Back to overview
            </button>
            <p className="mb-2 text-sm text-cyan-300">WORKSPACE MODULE</p>
            <h2 className="text-2xl font-bold">{page}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              This module is not connected to its full data workflow yet. Your existing
              API and sales datasets have not been changed. Use Rental discovery to search
              records currently stored in the rental API.
            </p>
            <button
              type="button"
              onClick={() => setPage('Rental discovery')}
              className="mt-6 rounded-lg bg-cyan-300 px-4 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-200"
            >
              Open rental discovery
            </button>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
