"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api, DealsResponse, DealAnalysis, NeighborhoodStats } from "@/lib/api";

// Deal score styling
const DEAL_SCORE_STYLES: Record<string, { bg: string; text: string; label: string; emoji: string }> = {
  great_deal: { bg: "bg-emerald-500/20", text: "text-emerald-400", label: "Great Deal!", emoji: "🔥" },
  good_deal: { bg: "bg-green-500/20", text: "text-green-400", label: "Good Deal", emoji: "✨" },
  fair: { bg: "bg-slate-500/20", text: "text-slate-400", label: "Fair Price", emoji: "⚖️" },
  overpriced: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Overpriced", emoji: "⚠️" },
  very_overpriced: { bg: "bg-red-500/20", text: "text-red-400", label: "Very Overpriced", emoji: "🚨" },
};

function DealCard({ deal, type }: { deal: DealAnalysis; type: "good" | "bad" }) {
  const scoreStyle = DEAL_SCORE_STYLES[deal.deal_score] || DEAL_SCORE_STYLES.fair;
  const isGood = type === "good";
  
  return (
    <div className={`glass rounded-xl overflow-hidden transition-all hover:scale-[1.02] ${
      isGood ? "hover:ring-2 hover:ring-emerald-500/50" : "hover:ring-2 hover:ring-red-500/50"
    }`}>
      {/* Image */}
      <div className="relative h-40 bg-slate-800">
        {deal.image_url ? (
          <img
            src={deal.image_url}
            alt={deal.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-600">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        )}
        
        {/* Deal badge */}
        <div className={`absolute top-2 right-2 px-2 py-1 rounded-lg ${scoreStyle.bg} ${scoreStyle.text} text-xs font-bold`}>
          {scoreStyle.emoji} {scoreStyle.label}
        </div>
        
        {/* Difference badge */}
        <div className={`absolute top-2 left-2 px-2 py-1 rounded-lg font-bold text-sm ${
          isGood ? "bg-emerald-500 text-white" : "bg-red-500 text-white"
        }`}>
          {isGood ? "↓" : "↑"} {Math.abs(deal.difference_pct).toFixed(1)}%
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4">
        <h3 className="text-white font-semibold text-sm line-clamp-2 mb-2" title={deal.title}>
          {deal.title}
        </h3>
        
        {/* Location */}
        {deal.location_district && (
          <div className="flex items-center gap-1 text-xs text-slate-400 mb-3">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {deal.location_district}
          </div>
        )}
        
        {/* Price comparison */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <div>
            <div className="text-xs text-slate-500">Actual Price</div>
            <div className={`text-lg font-bold ${isGood ? "text-emerald-400" : "text-red-400"}`}>
              €{deal.actual_price.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Fair Value</div>
            <div className="text-lg font-bold text-slate-300">
              €{deal.predicted_price.toLocaleString()}
            </div>
          </div>
        </div>
        
        {/* Difference */}
        <div className={`text-center py-2 rounded-lg mb-3 ${isGood ? "bg-emerald-500/10" : "bg-red-500/10"}`}>
          <span className={`font-bold ${isGood ? "text-emerald-400" : "text-red-400"}`}>
            {isGood ? "Save" : "Overpaying"} €{Math.abs(deal.difference).toLocaleString()}
          </span>
        </div>
        
        {/* Property details */}
        <div className="flex flex-wrap gap-2 text-xs mb-3">
          {deal.living_area_m2 && (
            <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">
              📐 {deal.living_area_m2} m²
            </span>
          )}
          {deal.bedroom_count && (
            <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">
              🛏️ {deal.bedroom_count}
            </span>
          )}
          {deal.bathroom_count && (
            <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">
              🚿 {deal.bathroom_count}
            </span>
          )}
          {deal.year_built && (
            <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">
              📅 {deal.year_built}
            </span>
          )}
          {deal.is_new_construction && (
            <span className="px-2 py-1 bg-cyan-500/20 rounded text-cyan-400">
              ✨ New
            </span>
          )}
        </div>
        
        {/* Actions */}
        <div className="flex gap-2">
          <Link
            href={`/listings/${deal.listing_id}`}
            className="flex-1 text-center py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white text-sm transition-colors"
          >
            View Details
          </Link>
          <a
            href={deal.url}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex-1 text-center py-2 rounded-lg text-white text-sm transition-colors ${
              isGood 
                ? "bg-emerald-600 hover:bg-emerald-500" 
                : "bg-slate-700 hover:bg-slate-600"
            }`}
          >
            {isGood ? "🔗 Go to Deal" : "View Listing"}
          </a>
        </div>
      </div>
    </div>
  );
}

export default function DealsPage() {
  const [deals, setDeals] = useState<DealsResponse | null>(null);
  const [districts, setDistricts] = useState<NeighborhoodStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [modelType] = useState("auto"); // Auto-selects best model
  const [excludeNew, setExcludeNew] = useState(false);
  const [district, setDistrict] = useState("");
  const [topN, setTopN] = useState(10);
  
  // Fetch districts on mount
  useEffect(() => {
    const fetchDistricts = async () => {
      try {
        const data = await api.getNeighborhoods();  // Returns districts now
        setDistricts(data.neighborhoods);
      } catch (err) {
        console.error("Failed to fetch districts:", err);
      }
    };
    fetchDistricts();
  }, []);
  
  const analyzeDeals = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await api.analyzeDeals({
        model_type: modelType,
        exclude_new_construction: excludeNew,
        location_district: district || undefined,
        top_n: topN,
      });
      
      setDeals(data);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to analyze deals");
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span className="text-3xl">💰</span>
            Deal Analyzer
          </h1>
          <p className="text-slate-400 mt-1">
            Find undervalued gems and avoid overpriced traps using AI price predictions
          </p>
        </div>
      </div>
      
      {/* Filters Card */}
      <div className="glass rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
          </svg>
          Analysis Settings
        </h2>
        
        <div className="grid md:grid-cols-3 gap-4 mb-4">
          {/* Neighborhood */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Neighborhood</label>
            <select
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
            >
              <option value="">All Neighborhoods</option>
              {districts.map((n) => (
                <option key={n.name} value={n.name}>
                  {n.name} ({n.count})
                </option>
              ))}
            </select>
          </div>
          
          {/* Results count */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Results per Category</label>
            <select
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
              <option value={50}>Top 50</option>
            </select>
          </div>
          
          {/* Exclude new construction */}
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={excludeNew}
                onChange={(e) => setExcludeNew(e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/50"
              />
              <span className="text-sm text-slate-300">Exclude New Construction</span>
            </label>
          </div>
        </div>
        
        <button
          onClick={analyzeDeals}
          disabled={loading}
          className="w-full md:w-auto px-6 py-3 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Analyze Deals
            </>
          )}
        </button>
      </div>
      
      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 text-red-400">
          {error}
        </div>
      )}
      
      {/* Results */}
      {deals && (
        <>
          {/* Stats bar */}
          <div className="glass rounded-xl p-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-xs text-slate-500">Analyzed</div>
                  <div className="text-xl font-bold text-white">{deals.total_analyzed} listings</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Model Used</div>
                  <div className="text-xl font-bold text-cyan-400">{deals.model_used}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Avg. Prediction Error</div>
                  <div className="text-xl font-bold text-amber-400">±{deals.average_error_pct}%</div>
                </div>
              </div>
              <div className="flex gap-4">
                <div className="text-center px-4 py-2 bg-emerald-500/10 rounded-lg">
                  <div className="text-2xl font-bold text-emerald-400">{deals.good_deals.length}</div>
                  <div className="text-xs text-emerald-400">Good Deals</div>
                </div>
                <div className="text-center px-4 py-2 bg-red-500/10 rounded-lg">
                  <div className="text-2xl font-bold text-red-400">{deals.bad_deals.length}</div>
                  <div className="text-xs text-red-400">Overpriced</div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Good Deals Section */}
          <div>
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <span className="text-2xl">🔥</span>
              Good Deals
              <span className="text-sm font-normal text-slate-400">
                — Properties priced below predicted value
              </span>
            </h2>
            
            {deals.good_deals.length > 0 ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {deals.good_deals.map((deal, i) => (
                  <DealCard key={deal.listing_id || i} deal={deal} type="good" />
                ))}
              </div>
            ) : (
              <div className="glass rounded-xl p-8 text-center text-slate-400">
                No underpriced properties found. The market might be fairly priced! 🤷
              </div>
            )}
          </div>
          
          {/* Bad Deals Section */}
          <div>
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <span className="text-2xl">🚨</span>
              Overpriced Listings
              <span className="text-sm font-normal text-slate-400">
                — Properties priced above predicted value
              </span>
            </h2>
            
            {deals.bad_deals.length > 0 ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {deals.bad_deals.map((deal, i) => (
                  <DealCard key={deal.listing_id || i} deal={deal} type="bad" />
                ))}
              </div>
            ) : (
              <div className="glass rounded-xl p-8 text-center text-slate-400">
                No overpriced properties found. Sellers are pricing fairly! 👍
              </div>
            )}
          </div>
        </>
      )}
      
      {/* Empty state */}
      {!deals && !loading && !error && (
        <div className="glass rounded-xl p-12 text-center">
          <div className="text-6xl mb-4">🔍</div>
          <h3 className="text-xl font-bold text-white mb-2">Ready to Find Deals</h3>
          <p className="text-slate-400 max-w-md mx-auto">
            Click &quot;Analyze Deals&quot; to use machine learning to identify undervalued properties 
            and expose overpriced listings.
          </p>
        </div>
      )}
    </div>
  );
}

