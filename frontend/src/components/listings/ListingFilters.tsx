"use client";

import { useState } from "react";
import {
  ListingFilter,
  ConstructionPhase,
  HeatingSystem,
  ConstructionPhaseLabels,
  HeatingSystemLabels,
} from "@/types/listing";

interface ListingFiltersProps {
  filters: ListingFilter;
  onFilterChange: (filters: ListingFilter) => void;
}

export function ListingFilters({ filters, onFilterChange }: ListingFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const updateFilter = (key: keyof ListingFilter, value: any) => {
    const newFilters = { ...filters, [key]: value || undefined };
    onFilterChange(newFilters);
  };

  const clearFilters = () => {
    onFilterChange({});
  };

  const hasActiveFilters = Object.values(filters).some(
    (v) => v !== undefined && v !== ""
  );

  const activeFilterCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== ""
  ).length;

  return (
    <div>
      {/* Toggle Row */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-3 text-slate-300 hover:text-white transition-colors"
        >
          <div className="w-8 h-8 rounded-lg bg-slate-800/50 flex items-center justify-center">
            <svg
              className={`w-4 h-4 transition-transform ${isExpanded ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
          </div>
          <span className="font-medium">Filters</span>
          {hasActiveFilters && (
            <span className="px-2.5 py-0.5 text-xs font-medium bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/20">
              {activeFilterCount} active
            </span>
          )}
        </button>

        <div className="flex items-center gap-3">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Clear all
            </button>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            {isExpanded ? "Collapse" : "Expand"}
          </button>
        </div>
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-slate-800/50">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Construction Phase */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                Construction Phase
              </label>
              <select
                value={filters.construction_phase || ""}
                onChange={(e) =>
                  updateFilter("construction_phase", e.target.value as ConstructionPhase | "")
                }
                className="input-field w-full text-sm py-2.5"
              >
                <option value="">All Phases</option>
                {Object.entries(ConstructionPhaseLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            {/* Heating System */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                Heating System
              </label>
              <select
                value={filters.heating_system || ""}
                onChange={(e) =>
                  updateFilter("heating_system", e.target.value as HeatingSystem | "")
                }
                className="input-field w-full text-sm py-2.5"
              >
                <option value="">All Types</option>
                {Object.entries(HeatingSystemLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            {/* Price Range */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                Min Price (€)
              </label>
              <input
                type="number"
                value={filters.min_price || ""}
                onChange={(e) =>
                  updateFilter("min_price", e.target.value ? Number(e.target.value) : undefined)
                }
                placeholder="0"
                className="input-field w-full text-sm py-2.5"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                Max Price (€)
              </label>
              <input
                type="number"
                value={filters.max_price || ""}
                onChange={(e) =>
                  updateFilter("max_price", e.target.value ? Number(e.target.value) : undefined)
                }
                placeholder="Any"
                className="input-field w-full text-sm py-2.5"
              />
            </div>

            {/* Area Range */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                Min Area (m²)
              </label>
              <input
                type="number"
                value={filters.min_area || ""}
                onChange={(e) =>
                  updateFilter("min_area", e.target.value ? Number(e.target.value) : undefined)
                }
                placeholder="0"
                className="input-field w-full text-sm py-2.5"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                Max Area (m²)
              </label>
              <input
                type="number"
                value={filters.max_area || ""}
                onChange={(e) =>
                  updateFilter("max_area", e.target.value ? Number(e.target.value) : undefined)
                }
                placeholder="Any"
                className="input-field w-full text-sm py-2.5"
              />
            </div>

            {/* Location */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                City
              </label>
              <input
                type="text"
                value={filters.location_city || ""}
                onChange={(e) => updateFilter("location_city", e.target.value)}
                placeholder="Any location"
                className="input-field w-full text-sm py-2.5"
              />
            </div>

            {/* Bedrooms */}
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">
                Min Bedrooms
              </label>
              <input
                type="number"
                value={filters.min_bedrooms || ""}
                onChange={(e) =>
                  updateFilter("min_bedrooms", e.target.value ? Number(e.target.value) : undefined)
                }
                placeholder="Any"
                className="input-field w-full text-sm py-2.5"
              />
            </div>
          </div>

          {/* Toggle Options */}
          <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-slate-800/50">
            <label className="flex items-center gap-2.5 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={filters.is_new_construction === true}
                  onChange={(e) =>
                    updateFilter("is_new_construction", e.target.checked ? true : undefined)
                  }
                  className="sr-only peer"
                />
                <div className="w-10 h-6 bg-slate-700 rounded-full peer peer-checked:bg-emerald-500 transition-colors" />
                <div className="absolute left-1 top-1 w-4 h-4 bg-slate-400 rounded-full peer-checked:bg-white peer-checked:translate-x-4 transition-all" />
              </div>
              <span className="text-sm text-slate-400 group-hover:text-white transition-colors">
                New Construction Only
              </span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={filters.require_ml_features === true}
                  onChange={(e) =>
                    updateFilter("require_ml_features", e.target.checked ? true : undefined)
                  }
                  className="sr-only peer"
                />
                <div className="w-10 h-6 bg-slate-700 rounded-full peer peer-checked:bg-cyan-500 transition-colors" />
                <div className="absolute left-1 top-1 w-4 h-4 bg-slate-400 rounded-full peer-checked:bg-white peer-checked:translate-x-4 transition-all" />
              </div>
              <span className="text-sm text-slate-400 group-hover:text-white transition-colors flex items-center gap-1.5">
                ML-Ready Only
                <span className="text-[10px] px-1.5 py-0.5 bg-cyan-500/20 text-cyan-400 rounded-md" title="Only show listings with: price, area, bedrooms, bathrooms, location">
                  ?
                </span>
              </span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
