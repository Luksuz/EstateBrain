"use client";

import { useState, useEffect } from "react";
import { api, MLStats, CorrelationResponse, ModelResult, ModelInfo, NeighborhoodStats } from "@/lib/api";

// Feature name mapping for display
const FEATURE_LABELS: Record<string, string> = {
  // Target
  price_eur: "Price (€)",
  
  // Optimal features (R²=91.77%)
  living_area_m2: "Living Area (m²)",     // Primary predictor
  bedroom_count: "Bedrooms",               // Room count
  distance_from_center: "Distance (km)",   // Location factor
  is_new_construction: "New Construction", // New vs resale
  
  // Additional features (for display)
  bathroom_count: "Bathrooms",
  year_built: "Year Built",
  outdoor_area_m2: "Outdoor Area (m²)",
  renovation_level: "Renovation Level",
  
  // Derived binary features
  has_garage: "Has Garage",
  has_modern_heating: "Modern Heating",
  
  // Neighborhood one-hot encoded features (consolidated)
  "location_district_Kućan Marof": "📍 Kućan Marof",
  "location_district_Novi Marof": "📍 Novi Marof",
  "location_district_Hrašćica": "📍 Hrašćica",
  "location_district_Okolica": "📍 Okolica (Suburbs)",
  "location_district_Varaždin": "📍 Varaždin (Center)",
};

// Helper to get feature label with fallback
function getFeatureLabel(feature: string): string {
  if (FEATURE_LABELS[feature]) return FEATURE_LABELS[feature];
  // Handle dynamic district features
  if (feature.startsWith("location_district_")) {
    const district = feature.replace("location_district_", "");
    return `📍 ${district}`;
  }
  // Default: capitalize and clean up
  return feature.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

// Color scale for correlation
function getCorrelationColor(value: number): string {
  const absValue = Math.abs(value);
  if (value > 0) {
    // Positive correlation - green shades
    if (absValue > 0.7) return "bg-emerald-500";
    if (absValue > 0.5) return "bg-emerald-400";
    if (absValue > 0.3) return "bg-emerald-300";
    return "bg-emerald-200";
  } else {
    // Negative correlation - red shades
    if (absValue > 0.7) return "bg-red-500";
    if (absValue > 0.5) return "bg-red-400";
    if (absValue > 0.3) return "bg-red-300";
    return "bg-red-200";
  }
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<MLStats | null>(null);
  const [correlation, setCorrelation] = useState<CorrelationResponse | null>(null);
  const [modelResult, setModelResult] = useState<ModelResult | null>(null);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [districts, setDistricts] = useState<NeighborhoodStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Data filters
  const [dataFilters, setDataFilters] = useState({
    exclude_new_construction: false,
    only_new_construction: false,
    location_district: "",
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsData, correlationData, modelsData, districtsData] = await Promise.all([
          api.getMLStats(),
          api.getCorrelation(),
          api.getAvailableModels(),
          api.getNeighborhoods(),  // Returns districts now
        ]);
        setStats(statsData);
        setCorrelation(correlationData);
        setAvailableModels(modelsData.models);
        setDistricts(districtsData.neighborhoods);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleTrainModel = async () => {
    try {
      setTraining(true);
      setError(null);
      const result = await api.trainModel({
        model_type: "auto", // Auto-selects best model
        // Data filters
        exclude_new_construction: dataFilters.exclude_new_construction,
        only_new_construction: dataFilters.only_new_construction,
        location_district: dataFilters.location_district || undefined,
      });
      setModelResult(result);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Training failed");
    } finally {
      setTraining(false);
    }
  };

  // Calculate price ranges from stats
  const getPriceRanges = () => {
    if (!stats) return [];
    return [
      { label: "Under €100k", min: 0, max: 100000 },
      { label: "€100k - €200k", min: 100000, max: 200000 },
      { label: "€200k - €300k", min: 200000, max: 300000 },
      { label: "€300k - €500k", min: 300000, max: 500000 },
      { label: "Over €500k", min: 500000, max: Infinity },
    ];
  };

  return (
    <div className="relative p-4 lg:p-8">
      {/* Header */}
      <header className="mb-8 animate-fade-in">
        <h1 className="text-3xl lg:text-4xl font-bold text-white mb-2">
          Analytics & ML
        </h1>
        <p className="text-slate-400">
          Statistics, correlations, and machine learning predictions
        </p>
      </header>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="stat-card animate-pulse">
              <div className="h-10 w-10 bg-slate-800/50 rounded-xl mb-3" />
              <div className="h-4 w-24 bg-slate-800/50 rounded mb-2" />
              <div className="h-8 w-16 bg-slate-800/50 rounded" />
            </div>
          ))}
        </div>
      ) : stats && (
        <>
          {/* Top Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="stat-card animate-fade-in">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-500/5 border border-emerald-500/20 flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <p className="text-sm text-slate-400 mb-1">Total Listings</p>
              <p className="text-3xl font-bold text-white">{stats.total_count}</p>
            </div>

            <div className="stat-card animate-fade-in">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-cyan-500/5 border border-cyan-500/20 flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-sm text-slate-400 mb-1">Average Price</p>
              <p className="text-3xl font-bold text-white">€{Math.round(stats.avg_price).toLocaleString()}</p>
            </div>

            <div className="stat-card animate-fade-in">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-violet-500/5 border border-violet-500/20 flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </div>
              <p className="text-sm text-slate-400 mb-1">Average Area</p>
              <p className="text-3xl font-bold text-white">{Math.round(stats.avg_area)} m²</p>
            </div>

            <div className="stat-card animate-fade-in">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-500/5 border border-amber-500/20 flex items-center justify-center mb-3">
                <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                </svg>
              </div>
              <p className="text-sm text-slate-400 mb-1">Cities Covered</p>
              <p className="text-3xl font-bold text-white">{stats.cities.length}</p>
            </div>
          </div>

          {/* Secondary Stats Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="glass rounded-xl p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Median Price</p>
              <p className="text-xl font-semibold text-white">€{Math.round(stats.median_price).toLocaleString()}</p>
            </div>
            <div className="glass rounded-xl p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Price Range</p>
              <p className="text-xl font-semibold text-white">€{Math.round(stats.min_price).toLocaleString()} - €{Math.round(stats.max_price).toLocaleString()}</p>
            </div>
            <div className="glass rounded-xl p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Avg Bedrooms</p>
              <p className="text-xl font-semibold text-white">{stats.avg_bedrooms.toFixed(1)}</p>
            </div>
            <div className="glass rounded-xl p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">New Construction</p>
              <p className="text-xl font-semibold text-white">{stats.new_construction_pct.toFixed(1)}%</p>
            </div>
          </div>

          {/* Correlation Matrix Section */}
          {correlation && (
            <div className="mb-8">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Price Correlations
                <span className="text-sm font-normal text-slate-400">({correlation.sample_count} samples)</span>
              </h2>
              
              <div className="grid lg:grid-cols-2 gap-6">
                {/* Target Correlations */}
                <div className="glass rounded-2xl p-6">
                  <h3 className="text-sm text-slate-400 mb-4">Features correlated with Price</h3>
                  <div className="space-y-3">
                    {Object.entries(correlation.target_correlations)
                      .filter(([key]) => key !== "price_eur")
                      .map(([feature, value]) => (
                        <div key={feature} className="flex items-center gap-3">
                          <div className="w-40 text-sm text-slate-300 truncate" title={getFeatureLabel(feature)}>
                            {getFeatureLabel(feature)}
                          </div>
                          <div className="flex-1 h-6 bg-slate-800/50 rounded-lg overflow-hidden relative">
                            <div 
                              className={`absolute h-full rounded-lg transition-all ${value >= 0 ? 'bg-gradient-to-r from-emerald-600 to-emerald-400' : 'bg-gradient-to-r from-red-600 to-red-400'}`}
                              style={{ 
                                width: `${Math.abs(value) * 100}%`,
                                left: value >= 0 ? '50%' : `${50 - Math.abs(value) * 50}%`,
                                right: value >= 0 ? 'auto' : '50%'
                              }}
                            />
                            <div className="absolute inset-0 flex items-center justify-center">
                              <span className="text-xs font-medium text-white drop-shadow">
                                {value.toFixed(3)}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                  <div className="mt-4 flex justify-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 rounded bg-red-500"></span> Negative
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 rounded bg-emerald-500"></span> Positive
                    </span>
                  </div>
                </div>

                {/* Full Correlation Matrix (heatmap style) */}
                <div className="glass rounded-2xl p-6 overflow-x-auto">
                  <h3 className="text-sm text-slate-400 mb-4">Correlation Matrix</h3>
                  <div className="min-w-[400px]">
                    <table className="w-full text-xs">
                      <thead>
                        <tr>
                          <th className="p-1"></th>
                          {correlation.feature_names.slice(0, 7).map(f => (
                            <th key={f} className="p-1 text-slate-400 font-normal truncate max-w-[60px]" title={getFeatureLabel(f)}>
                              {getFeatureLabel(f).slice(0, 6)}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {correlation.feature_names.slice(0, 7).map(row => (
                          <tr key={row}>
                            <td className="p-1 text-slate-400 truncate max-w-[80px]" title={getFeatureLabel(row)}>
                              {getFeatureLabel(row).slice(0, 8)}
                            </td>
                            {correlation.feature_names.slice(0, 7).map(col => {
                              const val = correlation.correlation_matrix[row]?.[col] || 0;
                              return (
                                <td 
                                  key={col} 
                                  className={`p-1 text-center rounded ${getCorrelationColor(val)} ${Math.abs(val) > 0.5 ? 'text-white' : 'text-slate-800'}`}
                                  title={`${getFeatureLabel(row)} vs ${getFeatureLabel(col)}: ${val.toFixed(3)}`}
                                >
                                  {val.toFixed(2)}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ML Model Training Section */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Train ML Model
            </h2>
            
            {/* Data Filters */}
            <div className="glass rounded-xl p-4 mb-4">
              <div className="flex flex-wrap items-center gap-4">
                <span className="text-sm text-slate-400">Data Filters:</span>
                
                {/* Construction Type Toggle */}
                <div className="flex items-center gap-2 bg-slate-800/50 rounded-lg p-1">
                  <button
                    onClick={() => setDataFilters(f => ({ ...f, exclude_new_construction: false, only_new_construction: false }))}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                      !dataFilters.exclude_new_construction && !dataFilters.only_new_construction
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    All Properties
                  </button>
                  <button
                    onClick={() => setDataFilters(f => ({ ...f, exclude_new_construction: true, only_new_construction: false }))}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                      dataFilters.exclude_new_construction
                        ? 'bg-amber-500/20 text-amber-400'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Exclude New
                  </button>
                  <button
                    onClick={() => setDataFilters(f => ({ ...f, exclude_new_construction: false, only_new_construction: true }))}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                      dataFilters.only_new_construction
                        ? 'bg-cyan-500/20 text-cyan-400'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Only New
                  </button>
                </div>
                
                {/* Neighborhood Filter */}
                <div className="flex items-center gap-2">
                  <label className="text-xs text-slate-500">Neighborhood:</label>
                  <select
                    value={dataFilters.location_district}
                    onChange={(e) => setDataFilters(f => ({ ...f, location_district: e.target.value }))}
                    className="w-48 px-2 py-1.5 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-xs focus:border-emerald-500/50 focus:outline-none"
                  >
                    <option value="">All Neighborhoods</option>
                    {districts.map((n) => (
                      <option key={n.name} value={n.name}>
                        {n.name} ({n.count}) - €{n.price_per_m2.toLocaleString()}/m²
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Train Model */}
              <div className="glass rounded-2xl p-6">
                <h3 className="text-sm text-slate-400 mb-4">AI Model Training</h3>
                <p className="text-slate-500 text-sm mb-6">
                  The system automatically selects the best model based on your data filters. 
                  Uses 4 optimized features: area, bedrooms, renovation level, and distance from center.
                </p>
                
                <button
                  onClick={handleTrainModel}
                  disabled={training}
                  className="w-full py-4 px-4 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white font-medium rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {training ? (
                    <>
                      <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Training AI Model...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      Train Price Prediction Model
                    </>
                  )}
                </button>
              </div>

              {/* Model Results */}
              <div className="glass rounded-2xl p-6">
                <h3 className="text-sm text-slate-400 mb-4">Results</h3>
                {modelResult ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-slate-800/30 rounded-lg p-3">
                        <p className="text-xs text-slate-500">R² Score</p>
                        <p className={`text-lg font-bold ${modelResult.r2_score > 0.7 ? 'text-emerald-400' : modelResult.r2_score > 0.5 ? 'text-amber-400' : 'text-red-400'}`}>
                          {(modelResult.r2_score * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="bg-slate-800/30 rounded-lg p-3">
                        <p className="text-xs text-slate-500">RMSE</p>
                        <p className="text-lg font-bold text-white">€{Math.round(modelResult.rmse).toLocaleString()}</p>
                      </div>
                      <div className="bg-slate-800/30 rounded-lg p-3">
                        <p className="text-xs text-slate-500">MAE</p>
                        <p className="text-lg font-bold text-white">€{Math.round(modelResult.mae).toLocaleString()}</p>
                      </div>
                      <div className="bg-slate-800/30 rounded-lg p-3">
                        <p className="text-xs text-slate-500">CV Mean</p>
                        <p className="text-lg font-bold text-white">{(modelResult.cv_mean * 100).toFixed(1)}%</p>
                      </div>
                    </div>
                    
                    <p className="text-xs text-slate-500">
                      Trained on {modelResult.sample_count} samples • CV Std: ±{(modelResult.cv_std * 100).toFixed(1)}%
                    </p>

                    {/* Feature Importance */}
                    {modelResult.feature_importance && (
                      <div>
                        <p className="text-xs text-slate-400 mb-2">Feature Importance</p>
                        <div className="space-y-1">
                          {Object.entries(modelResult.feature_importance)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5)
                            .map(([feature, importance]) => (
                              <div key={feature} className="flex items-center gap-2">
                                <div className="w-28 text-xs text-slate-400 truncate" title={getFeatureLabel(feature)}>
                                  {getFeatureLabel(feature)}
                                </div>
                                <div className="flex-1 h-2 bg-slate-800/50 rounded-full overflow-hidden">
                                  <div 
                                    className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-full"
                                    style={{ width: `${importance * 100}%` }}
                                  />
                                </div>
                                <div className="w-12 text-xs text-slate-500 text-right">
                                  {(importance * 100).toFixed(1)}%
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Coefficients for Linear Regression */}
                    {modelResult.coefficients && (
                      <div>
                        <p className="text-xs text-slate-400 mb-2">Coefficients</p>
                        <div className="space-y-1 max-h-32 overflow-y-auto">
                          {Object.entries(modelResult.coefficients)
                            .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                            .slice(0, 5)
                            .map(([feature, coef]) => (
                              <div key={feature} className="flex items-center justify-between text-xs">
                                <span className="text-slate-400">{getFeatureLabel(feature)}</span>
                                <span className={coef >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                                  {coef >= 0 ? '+' : ''}{coef.toFixed(2)}
                                </span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-slate-800/50 flex items-center justify-center">
                      <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </div>
                    <p className="text-sm text-slate-500">Click Train to see model performance results</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* City Distribution */}
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="glass rounded-2xl p-6">
              <h3 className="text-sm text-slate-400 mb-4">Listings by City</h3>
              <div className="space-y-3">
                {Object.entries(stats.city_counts)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 8)
                  .map(([city, count]) => {
                    const maxCount = Math.max(...Object.values(stats.city_counts));
                    return (
                      <div key={city} className="flex items-center gap-3">
                        <div className="w-32 text-sm text-slate-300 truncate">{city}</div>
                        <div className="flex-1 h-6 bg-slate-800/50 rounded-lg overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-lg"
                            style={{ width: `${(count / maxCount) * 100}%` }}
                          />
                        </div>
                        <div className="w-10 text-sm text-white text-right">{count}</div>
                      </div>
                    );
                  })}
              </div>
            </div>

            <div className="glass rounded-2xl p-6">
              <h3 className="text-sm text-slate-400 mb-4">Construction Phase Distribution</h3>
              <div className="space-y-3">
                {Object.entries(stats.construction_phase_counts)
                  .sort((a, b) => b[1] - a[1])
                  .map(([phase, count]) => {
                    const maxCount = Math.max(...Object.values(stats.construction_phase_counts));
                    return (
                      <div key={phase} className="flex items-center gap-3">
                        <div className="w-32 text-sm text-slate-300 truncate">{phase}</div>
                        <div className="flex-1 h-6 bg-slate-800/50 rounded-lg overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-lg"
                            style={{ width: `${(count / maxCount) * 100}%` }}
                          />
                        </div>
                        <div className="w-10 text-sm text-white text-right">{count}</div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
