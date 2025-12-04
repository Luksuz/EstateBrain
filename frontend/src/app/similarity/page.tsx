"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { getRenovationLevelInfo, formatDistance } from "@/types/listing";

interface SimilarListing {
  id: string;
  title?: string;
  url: string;
  price_eur?: number;
  living_area_m2?: number;
  outdoor_area_m2?: number;
  bedroom_count?: number;
  bathroom_count?: number;
  renovation_level?: number;
  location_district?: string;
  distance_from_center?: number;
  building_type?: string;
  is_new_construction?: boolean;
  interior_arranged?: boolean;
  has_cellar?: boolean;
  parking_type?: string;
  images: { thumbnail?: string; large?: string }[];
  similarity_score: number;
  match_details: Record<string, { score: number; target?: number; actual?: number }>;
}

interface SimilarityResponse {
  query: Record<string, unknown>;
  total_candidates: number;
  results: SimilarListing[];
}

export default function SimilarityPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SimilarityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [livingArea, setLivingArea] = useState<string>("70");
  const [outdoorArea, setOutdoorArea] = useState<string>("");
  const [bedrooms, setBedrooms] = useState<string>("2");
  const [bathrooms, setBathrooms] = useState<string>("1");
  const [renovationLevel, setRenovationLevel] = useState<string>("8");
  const [district, setDistrict] = useState<string>("");
  const [maxDistance, setMaxDistance] = useState<string>("");
  const [minPrice, setMinPrice] = useState<string>("");
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [isHouse, setIsHouse] = useState<string>("");
  const [isNew, setIsNew] = useState<string>("");
  const [isFurnished, setIsFurnished] = useState<string>("");
  const [hasCellar, setHasCellar] = useState<string>("");
  const [hasGarage, setHasGarage] = useState<string>("");
  const [topN, setTopN] = useState<string>("3");

  const handleSearch = async () => {
    setLoading(true);
    setError(null);

    try {
      const params: Record<string, unknown> = {
        top_n: parseInt(topN) || 3,
      };

      if (livingArea) params.living_area_m2 = parseFloat(livingArea);
      if (outdoorArea) params.outdoor_area_m2 = parseFloat(outdoorArea);
      if (bedrooms) params.bedroom_count = parseInt(bedrooms);
      if (bathrooms) params.bathroom_count = parseInt(bathrooms);
      if (renovationLevel) params.renovation_level = parseInt(renovationLevel);
      if (district) params.location_district = district;
      if (maxDistance) params.max_distance_from_center = parseFloat(maxDistance);
      if (minPrice) params.min_price = parseFloat(minPrice);
      if (maxPrice) params.max_price = parseFloat(maxPrice);
      if (isHouse === "true") params.is_house = true;
      if (isHouse === "false") params.is_house = false;
      if (isNew === "true") params.is_new_construction = true;
      if (isNew === "false") params.is_new_construction = false;
      if (isFurnished === "true") params.is_furnished = true;
      if (isFurnished === "false") params.is_furnished = false;
      if (hasCellar === "true") params.has_cellar = true;
      if (hasGarage === "true") params.has_garage = true;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/ml/similarity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });

      if (!response.ok) throw new Error("Search failed");
      
      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price?: number) => {
    if (!price) return "N/A";
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(price);
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-400";
    if (score >= 75) return "text-lime-400";
    if (score >= 60) return "text-amber-400";
    return "text-rose-400";
  };

  const getScoreBg = (score: number) => {
    if (score >= 90) return "bg-emerald-500";
    if (score >= 75) return "bg-lime-500";
    if (score >= 60) return "bg-amber-500";
    return "bg-rose-500";
  };

  return (
    <div className="relative p-4 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8 animate-fade-in">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white">Property Matcher</h1>
          <p className="text-slate-400">Find similar properties based on your criteria</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Search Form */}
        <div className="lg:col-span-1">
          <div className="glass rounded-2xl p-6 sticky top-4">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <svg className="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
              Search Criteria
            </h2>

            <div className="space-y-4">
              {/* Core Features */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Living Area (m²)</label>
                  <input
                    type="number"
                    value={livingArea}
                    onChange={(e) => setLivingArea(e.target.value)}
                    className="input-field w-full text-sm py-2"
                    placeholder="70"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Outdoor Area (m²)</label>
                  <input
                    type="number"
                    value={outdoorArea}
                    onChange={(e) => setOutdoorArea(e.target.value)}
                    className="input-field w-full text-sm py-2"
                    placeholder="10"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Bedrooms</label>
                  <input
                    type="number"
                    value={bedrooms}
                    onChange={(e) => setBedrooms(e.target.value)}
                    className="input-field w-full text-sm py-2"
                    placeholder="2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Bathrooms</label>
                  <input
                    type="number"
                    value={bathrooms}
                    onChange={(e) => setBathrooms(e.target.value)}
                    className="input-field w-full text-sm py-2"
                    placeholder="1"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Renovation Level (1-10)</label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={renovationLevel || 5}
                  onChange={(e) => setRenovationLevel(e.target.value)}
                  className="w-full accent-violet-500"
                />
                <div className="flex justify-between text-xs text-slate-500 mt-1">
                  <span>1 (Needs work)</span>
                  <span className="text-violet-400 font-medium">{renovationLevel || "Any"}</span>
                  <span>10 (Modern)</span>
                </div>
              </div>

              {/* Location */}
              <div className="pt-2 border-t border-slate-800/50">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">District</label>
                  <select
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                    className="input-field w-full text-sm py-2"
                  >
                    <option value="">Any District</option>
                    <option value="Varaždin">Varaždin</option>
                    <option value="Novi Marof">Novi Marof</option>
                    <option value="Ludbreg">Ludbreg</option>
                    <option value="Ivanec">Ivanec</option>
                    <option value="Varaždinske Toplice">Varaždinske Toplice</option>
                    <option value="Sračinec">Sračinec</option>
                  </select>
                </div>

                <div className="mt-3">
                  <label className="block text-xs font-medium text-slate-500 mb-1">Max Distance from Center (km)</label>
                  <input
                    type="number"
                    value={maxDistance}
                    onChange={(e) => setMaxDistance(e.target.value)}
                    className="input-field w-full text-sm py-2"
                    placeholder="5"
                  />
                </div>
              </div>

              {/* Price Range */}
              <div className="pt-2 border-t border-slate-800/50">
                <label className="block text-xs font-medium text-slate-500 mb-2">Price Range (€)</label>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    value={minPrice}
                    onChange={(e) => setMinPrice(e.target.value)}
                    className="input-field w-full text-sm py-2"
                    placeholder="Min"
                  />
                  <input
                    type="number"
                    value={maxPrice}
                    onChange={(e) => setMaxPrice(e.target.value)}
                    className="input-field w-full text-sm py-2"
                    placeholder="Max"
                  />
                </div>
              </div>

              {/* Filters */}
              <div className="pt-2 border-t border-slate-800/50 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Property Type</label>
                  <select value={isHouse} onChange={(e) => setIsHouse(e.target.value)} className="input-field w-full text-sm py-2">
                    <option value="">Any</option>
                    <option value="false">🏢 Apartment</option>
                    <option value="true">🏠 House</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Construction</label>
                  <select value={isNew} onChange={(e) => setIsNew(e.target.value)} className="input-field w-full text-sm py-2">
                    <option value="">Any</option>
                    <option value="true">New Build</option>
                    <option value="false">Existing</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Interior</label>
                  <select value={isFurnished} onChange={(e) => setIsFurnished(e.target.value)} className="input-field w-full text-sm py-2">
                    <option value="">Any</option>
                    <option value="true">Furnished</option>
                    <option value="false">Unfurnished</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Results</label>
                  <select value={topN} onChange={(e) => setTopN(e.target.value)} className="input-field w-full text-sm py-2">
                    <option value="3">Top 3</option>
                    <option value="5">Top 5</option>
                    <option value="10">Top 10</option>
                  </select>
                </div>
              </div>

              {/* Checkboxes */}
              <div className="pt-2 border-t border-slate-800/50 flex flex-wrap gap-4">
                <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-400 hover:text-white">
                  <input
                    type="checkbox"
                    checked={hasCellar === "true"}
                    onChange={(e) => setHasCellar(e.target.checked ? "true" : "")}
                    className="rounded border-slate-600 bg-slate-800 text-violet-500 focus:ring-violet-500"
                  />
                  Has Cellar
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-400 hover:text-white">
                  <input
                    type="checkbox"
                    checked={hasGarage === "true"}
                    onChange={(e) => setHasGarage(e.target.checked ? "true" : "")}
                    className="rounded border-slate-600 bg-slate-800 text-violet-500 focus:ring-violet-500"
                  />
                  Has Garage
                </label>
              </div>

              {/* Search Button */}
              <button
                onClick={handleSearch}
                disabled={loading}
                className="w-full btn-primary mt-4 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
                    Searching...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    Find Similar Properties
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2">
          {error && (
            <div className="glass rounded-2xl p-6 border border-rose-500/20 bg-rose-500/5 mb-6">
              <p className="text-rose-400">{error}</p>
            </div>
          )}

          {results && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="glass rounded-2xl p-4 flex items-center justify-between">
                <span className="text-slate-400">
                  Found <span className="text-white font-semibold">{results.results.length}</span> similar properties
                  from <span className="text-white font-semibold">{results.total_candidates}</span> candidates
                </span>
              </div>

              {/* Results List */}
              {results.results.map((listing, index) => {
                const renovationInfo = getRenovationLevelInfo(listing.renovation_level);
                const primaryImage = listing.images?.[0]?.large || listing.images?.[0]?.thumbnail;

                return (
                  <div key={listing.id} className="glass rounded-2xl overflow-hidden animate-fade-in" style={{ animationDelay: `${index * 100}ms` }}>
                    <div className="flex flex-col md:flex-row">
                      {/* Image */}
                      <div className="relative w-full md:w-72 h-48 md:h-auto flex-shrink-0">
                        {primaryImage ? (
                          <img src={primaryImage} alt={listing.title || "Property"} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full bg-slate-800 flex items-center justify-center">
                            <svg className="w-12 h-12 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                            </svg>
                          </div>
                        )}
                        
                        {/* Match Score Badge */}
                        <div className="absolute top-3 left-3">
                          <div className={`px-3 py-1.5 rounded-full text-sm font-bold text-white ${getScoreBg(listing.similarity_score)} shadow-lg`}>
                            {listing.similarity_score}% Match
                          </div>
                        </div>

                        {/* Rank Badge */}
                        <div className="absolute top-3 right-3">
                          <div className="w-8 h-8 rounded-full bg-slate-900/80 backdrop-blur-sm flex items-center justify-center text-white font-bold">
                            #{index + 1}
                          </div>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 p-5">
                        <div className="flex items-start justify-between gap-4 mb-3">
                          <div>
                            <h3 className="text-lg font-semibold text-white line-clamp-2">{listing.title || "Untitled"}</h3>
                            <p className="text-sm text-slate-400 mt-1">
                              {listing.location_district}
                              {listing.distance_from_center && ` • ${formatDistance(listing.distance_from_center)} from center`}
                            </p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="text-xl font-bold text-emerald-400">{formatPrice(listing.price_eur)}</div>
                            {listing.living_area_m2 && listing.price_eur && (
                              <div className="text-xs text-slate-500">
                                {Math.round(listing.price_eur / listing.living_area_m2)} €/m²
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Property Stats */}
                        <div className="flex flex-wrap gap-3 mb-4">
                          {listing.living_area_m2 && (
                            <span className="px-2 py-1 bg-slate-800/50 rounded text-sm text-slate-300">
                              {listing.living_area_m2} m²
                            </span>
                          )}
                          {listing.bedroom_count && (
                            <span className="px-2 py-1 bg-slate-800/50 rounded text-sm text-slate-300">
                              {listing.bedroom_count} bed
                            </span>
                          )}
                          {listing.bathroom_count && (
                            <span className="px-2 py-1 bg-slate-800/50 rounded text-sm text-slate-300">
                              {listing.bathroom_count} bath
                            </span>
                          )}
                          {listing.renovation_level && (
                            <span className={`px-2 py-1 rounded text-sm text-white ${renovationInfo.color}`}>
                              {renovationInfo.label}
                            </span>
                          )}
                          {listing.is_new_construction && (
                            <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded text-sm">
                              New Build
                            </span>
                          )}
                        </div>

                        {/* Match Details */}
                        <div className="border-t border-slate-800/50 pt-3">
                          <div className="text-xs text-slate-500 mb-2">Match Breakdown</div>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(listing.match_details).map(([key, detail]) => (
                              <div key={key} className="flex items-center gap-1.5 text-xs">
                                <span className="text-slate-500 capitalize">{key.replace(/_/g, " ")}:</span>
                                <span className={getScoreColor(detail.score)}>{detail.score}%</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex gap-3 mt-4">
                          <Link
                            href={`/listings/${listing.id}`}
                            className="flex-1 btn-primary text-center text-sm py-2"
                          >
                            View Details
                          </Link>
                          <a
                            href={listing.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-sm transition-colors flex items-center gap-2"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                            Original
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {results.results.length === 0 && (
                <div className="glass rounded-2xl p-12 text-center">
                  <svg className="w-16 h-16 text-slate-700 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <h3 className="text-xl font-semibold text-white mb-2">No matches found</h3>
                  <p className="text-slate-400">Try adjusting your criteria or removing some filters</p>
                </div>
              )}
            </div>
          )}

          {/* Empty State */}
          {!results && !loading && (
            <div className="glass rounded-2xl p-12 text-center">
              <div className="w-20 h-20 rounded-full bg-violet-500/10 flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Find Your Perfect Property</h3>
              <p className="text-slate-400 max-w-md mx-auto">
                Enter your desired property specifications and we'll find the most similar listings in our database.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}




