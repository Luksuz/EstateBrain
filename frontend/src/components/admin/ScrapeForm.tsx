"use client";

import { useState, useEffect } from "react";
import { api, LocationData } from "@/lib/api";

interface ScrapeFormProps {
  onJobCreated: () => void;
}

type ScrapeMode = "location" | "search" | "urls";

export function ScrapeForm({ onJobCreated }: ScrapeFormProps) {
  const [mode, setMode] = useState<ScrapeMode>("location");
  
  // Location mode state
  const [locations, setLocations] = useState<LocationData>({});
  const [selectedZupanija, setSelectedZupanija] = useState<string>("");
  const [selectedDistrict, setSelectedDistrict] = useState<string>("");
  const [propertyType, setPropertyType] = useState("prodaja-stanova");
  
  // Search mode state
  const [searchUrl, setSearchUrl] = useState("");
  const [startPage, setStartPage] = useState(1);
  const [endPage, setEndPage] = useState(5);
  const [forceRescrape, setForceRescrape] = useState(false);
  
  // URL mode state
  const [urls, setUrls] = useState("");
  
  // Common state
  const [loading, setLoading] = useState(false);
  const [loadingLocations, setLoadingLocations] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    totalListings: number;
    newListings?: number;
    existingListings?: number;
    jobId: string;
  } | null>(null);

  // Load locations on mount
  useEffect(() => {
    const loadLocations = async () => {
      try {
        const data = await api.getAllLocations();
        setLocations(data);
        // Default to Varaždinska
        if (data["Varaždinska"]) {
          setSelectedZupanija("Varaždinska");
        }
      } catch (err) {
        console.error("Failed to load locations:", err);
      } finally {
        setLoadingLocations(false);
      }
    };
    loadLocations();
  }, []);

  const districts = selectedZupanija ? locations[selectedZupanija] || [] : [];

  const handleLocationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      if (!selectedZupanija) {
        setError("Please select a županija");
        return;
      }

      // Get the search URL for the selected location
      const { url } = await api.getSearchUrl(selectedZupanija, selectedDistrict || undefined, propertyType);
      
      // Use the generated URL to scrape, passing županija for location context
      const response = await api.scrapeFromSearch(url, {
        startPage,
        endPage,
        forceRescrape,
        zupanija: selectedZupanija,
      });
      
      if (response.total_listings === 0) {
        setError("No listings found for this location.");
        return;
      }

      setResult({
        totalListings: response.total_listings,
        newListings: response.new_listings,
        existingListings: response.existing_listings,
        jobId: response.job_id!,
      });
      onJobCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start scraping");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      if (!searchUrl.trim()) {
        setError("Please enter a search page URL");
        return;
      }

      const response = await api.scrapeFromSearch(searchUrl.trim(), {
        startPage,
        endPage,
        forceRescrape,
      });
      
      if (response.total_listings === 0) {
        setError("No listings found on this page. Make sure it's a valid njuskalo.hr search results page.");
        return;
      }

      setResult({
        totalListings: response.total_listings,
        newListings: response.new_listings,
        existingListings: response.existing_listings,
        jobId: response.job_id!,
      });
      setSearchUrl("");
      onJobCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extract listings");
    } finally {
      setLoading(false);
    }
  };

  const handleUrlsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      const urlList = urls
        .split("\n")
        .map((url) => url.trim())
        .filter((url) => url.length > 0);

      if (urlList.length === 0) {
        setError("Please enter at least one URL");
        return;
      }

      const response = await api.createScrapeJob(urlList);
      setResult({
        totalListings: urlList.length,
        jobId: response.id,
      });
      setUrls("");
      onJobCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Mode Toggle */}
      <div className="flex bg-slate-800/50 rounded-xl p-1">
        <button
          type="button"
          onClick={() => setMode("location")}
          className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
            mode === "location"
              ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-lg shadow-emerald-500/25"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          </svg>
          Location
        </button>
        <button
          type="button"
          onClick={() => setMode("search")}
          className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
            mode === "search"
              ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-lg shadow-emerald-500/25"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          URL
        </button>
        <button
          type="button"
          onClick={() => setMode("urls")}
          className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
            mode === "urls"
              ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-lg shadow-emerald-500/25"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Bulk
        </button>
      </div>

      {/* Location Mode */}
      {mode === "location" && (
        <form onSubmit={handleLocationSubmit} className="space-y-5">
          {loadingLocations ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin h-6 w-6 border-2 border-emerald-500 border-t-transparent rounded-full" />
            </div>
          ) : (
            <>
              {/* Property Type */}
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Property Type
                </label>
                <select
                  value={propertyType}
                  onChange={(e) => setPropertyType(e.target.value)}
                  className="input-field w-full"
                  disabled={loading}
                >
                  <option value="prodaja-stanova">🏢 Apartments for Sale</option>
                  <option value="prodaja-kuca">🏠 Houses for Sale</option>
                  <option value="iznajmljivanje-stanova">🔑 Apartments for Rent</option>
                  <option value="iznajmljivanje-kuca">🏡 Houses for Rent</option>
                </select>
              </div>

              {/* Županija Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Županija (County)
                </label>
                <select
                  value={selectedZupanija}
                  onChange={(e) => {
                    setSelectedZupanija(e.target.value);
                    setSelectedDistrict("");
                  }}
                  className="input-field w-full"
                  disabled={loading}
                >
                  <option value="">Select a županija...</option>
                  {Object.keys(locations).sort().map((zupanija) => (
                    <option key={zupanija} value={zupanija}>
                      {zupanija}
                    </option>
                  ))}
                </select>
              </div>

              {/* District Selection */}
              {selectedZupanija && districts.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-2">
                    District (Optional)
                  </label>
                  <select
                    value={selectedDistrict}
                    onChange={(e) => setSelectedDistrict(e.target.value)}
                    className="input-field w-full"
                    disabled={loading}
                  >
                    <option value="">All districts in {selectedZupanija}</option>
                    {districts.map((district) => (
                      <option key={district} value={district}>
                        {district}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1.5 text-xs text-slate-500">
                    {districts.length} districts available
                  </p>
                </div>
              )}

              {/* Page Range */}
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Page Range
                  <span className="text-xs text-slate-500 ml-2">
                    ({endPage - startPage + 1} pages)
                  </span>
                </label>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <label className="block text-xs text-slate-500 mb-1">From</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={startPage}
                      onChange={(e) => {
                        const val = Math.max(1, Math.min(100, parseInt(e.target.value) || 1));
                        setStartPage(val);
                        if (val > endPage) setEndPage(val);
                      }}
                      className="w-full px-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-emerald-400 font-mono font-semibold text-center focus:border-emerald-500 focus:outline-none"
                      disabled={loading}
                    />
                  </div>
                  <div className="text-slate-500 pt-5">→</div>
                  <div className="flex-1">
                    <label className="block text-xs text-slate-500 mb-1">To</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={endPage}
                      onChange={(e) => {
                        const val = Math.max(1, Math.min(100, parseInt(e.target.value) || 1));
                        setEndPage(val);
                        if (val < startPage) setStartPage(val);
                      }}
                      className="w-full px-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-emerald-400 font-mono font-semibold text-center focus:border-emerald-500 focus:outline-none"
                      disabled={loading}
                    />
                  </div>
                </div>
                <div className="mt-2 flex gap-2 flex-wrap">
                  {[
                    { label: "1-5", start: 1, end: 5 },
                    { label: "1-10", start: 1, end: 10 },
                    { label: "1-25", start: 1, end: 25 },
                    { label: "1-50", start: 1, end: 50 },
                    { label: "50-100", start: 50, end: 100 },
                  ].map((preset) => (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => {
                        setStartPage(preset.start);
                        setEndPage(preset.end);
                      }}
                      className={`px-2 py-1 text-xs rounded-md transition-colors ${
                        startPage === preset.start && endPage === preset.end
                          ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          : "bg-slate-800/50 text-slate-500 border border-slate-700/50 hover:text-slate-300"
                      }`}
                      disabled={loading}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Re-scrape toggle */}
              <label className="flex items-center gap-3 cursor-pointer group">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={forceRescrape}
                    onChange={(e) => setForceRescrape(e.target.checked)}
                    className="sr-only peer"
                    disabled={loading}
                  />
                  <div className="w-10 h-6 bg-slate-700 rounded-full peer peer-checked:bg-emerald-500 transition-colors" />
                  <div className="absolute left-1 top-1 w-4 h-4 bg-slate-400 rounded-full peer-checked:bg-white peer-checked:translate-x-4 transition-all" />
                </div>
                <span className="text-sm text-slate-400 group-hover:text-white transition-colors">
                  Re-scrape existing listings
                </span>
              </label>
            </>
          )}

          <button
            type="submit"
            disabled={loading || loadingLocations || !selectedZupanija}
            className="btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Scraping {selectedDistrict || selectedZupanija}...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Scrape {selectedDistrict || selectedZupanija || "Location"}
              </span>
            )}
          </button>
        </form>
      )}

      {/* Search Page Mode */}
      {mode === "search" && (
        <form onSubmit={handleSearchSubmit} className="space-y-5">
          <div>
            <label htmlFor="searchUrl" className="block text-sm font-medium text-slate-400 mb-2">
              Search Results Page URL
            </label>
            <input
              id="searchUrl"
              type="url"
              value={searchUrl}
              onChange={(e) => setSearchUrl(e.target.value)}
              placeholder="https://www.njuskalo.hr/prodaja-stanova/varazdinska"
              className="input-field w-full"
              disabled={loading}
            />
            <p className="mt-1.5 text-xs text-slate-500">
              Paste any njuskalo.hr search results page URL
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Page Range
              <span className="text-xs text-slate-500 ml-2">
                ({endPage - startPage + 1} pages)
              </span>
            </label>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <label className="block text-xs text-slate-500 mb-1">From</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={startPage}
                  onChange={(e) => {
                    const val = Math.max(1, Math.min(100, parseInt(e.target.value) || 1));
                    setStartPage(val);
                    if (val > endPage) setEndPage(val);
                  }}
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-emerald-400 font-mono font-semibold text-center focus:border-emerald-500 focus:outline-none"
                  disabled={loading}
                />
              </div>
              <div className="text-slate-500 pt-5">→</div>
              <div className="flex-1">
                <label className="block text-xs text-slate-500 mb-1">To</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={endPage}
                  onChange={(e) => {
                    const val = Math.max(1, Math.min(100, parseInt(e.target.value) || 1));
                    setEndPage(val);
                    if (val < startPage) setStartPage(val);
                  }}
                  className="w-full px-3 py-2 bg-slate-800/80 border border-slate-700 rounded-lg text-emerald-400 font-mono font-semibold text-center focus:border-emerald-500 focus:outline-none"
                  disabled={loading}
                />
              </div>
            </div>
            <div className="mt-2 flex gap-2 flex-wrap">
              {[
                { label: "1-5", start: 1, end: 5 },
                { label: "1-10", start: 1, end: 10 },
                { label: "1-25", start: 1, end: 25 },
                { label: "1-50", start: 1, end: 50 },
                { label: "50-100", start: 50, end: 100 },
              ].map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => {
                    setStartPage(preset.start);
                    setEndPage(preset.end);
                  }}
                  className={`px-2 py-1 text-xs rounded-md transition-colors ${
                    startPage === preset.start && endPage === preset.end
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : "bg-slate-800/50 text-slate-500 border border-slate-700/50 hover:text-slate-300"
                  }`}
                  disabled={loading}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-3 cursor-pointer group">
            <div className="relative">
              <input
                type="checkbox"
                checked={forceRescrape}
                onChange={(e) => setForceRescrape(e.target.checked)}
                className="sr-only peer"
                disabled={loading}
              />
              <div className="w-10 h-6 bg-slate-700 rounded-full peer peer-checked:bg-emerald-500 transition-colors" />
              <div className="absolute left-1 top-1 w-4 h-4 bg-slate-400 rounded-full peer-checked:bg-white peer-checked:translate-x-4 transition-all" />
            </div>
            <span className="text-sm text-slate-400 group-hover:text-white transition-colors">
              Re-scrape existing listings
            </span>
          </label>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Extracting Listings...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Extract & Scrape
              </span>
            )}
          </button>
        </form>
      )}

      {/* Individual URLs Mode */}
      {mode === "urls" && (
        <form onSubmit={handleUrlsSubmit} className="space-y-5">
          <div>
            <label htmlFor="urls" className="block text-sm font-medium text-slate-400 mb-2">
              Listing URLs (one per line)
            </label>
            <textarea
              id="urls"
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder="https://www.njuskalo.hr/nekretnine/stan-...&#10;https://www.njuskalo.hr/nekretnine/stan-..."
              className="input-field w-full h-40 font-mono text-sm resize-none"
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Creating Job...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Start Scraping
              </span>
            )}
          </button>
        </form>
      )}

      {/* Success Message */}
      {result && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
          <div className="flex items-center gap-2 text-emerald-400 mb-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="font-semibold">Job Created!</span>
          </div>
          <p className="text-sm text-emerald-300/80">
            Found {result.totalListings} listings total
          </p>
          {(result.newListings !== undefined || result.existingListings !== undefined) && (
            <div className="flex gap-4 mt-2 text-xs">
              {result.newListings !== undefined && (
                <span className="badge badge-success">✨ {result.newListings} new</span>
              )}
              {result.existingListings !== undefined && result.existingListings > 0 && (
                <span className="badge badge-info">
                  ⏭️ {result.existingListings} {forceRescrape ? "re-scraping" : "skipped"}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm flex items-start gap-3">
          <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          {error}
        </div>
      )}
    </div>
  );
}
