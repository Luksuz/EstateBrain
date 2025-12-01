"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Listing, ListingFilter } from "@/types/listing";
import { ListingCard } from "@/components/listings/ListingCard";
import { ListingFilters } from "@/components/listings/ListingFilters";

export default function ListingsPage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ListingFilter>({});
  const [page, setPage] = useState(0);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const limit = 12;

  const fetchListings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getListings(filters, limit, page * limit);
      setListings(response.listings);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load listings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchListings();
  }, [filters, page]);

  const handleFilterChange = (newFilters: ListingFilter) => {
    setFilters(newFilters);
    setPage(0);
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="relative p-4 lg:p-8">
      {/* Header */}
      <header className="mb-6 animate-fade-in">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold text-white mb-2">
              Listings
            </h1>
            <p className="text-slate-400">
              Browse all {total} properties in our database
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* View Toggle */}
            <div className="flex items-center bg-slate-800/50 rounded-xl p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                </svg>
              </button>
            </div>
            <Link href="/admin" className="btn-primary flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Listings
            </Link>
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="mb-6 glass rounded-2xl p-4 animate-fade-in stagger-1" style={{ opacity: 0 }}>
        <ListingFilters filters={filters} onFilterChange={handleFilterChange} />
      </div>

      {/* Results Info */}
      <div className="flex items-center justify-between mb-6 animate-fade-in stagger-2" style={{ opacity: 0 }}>
        <div className="flex items-center gap-3">
          <span className="text-slate-400">
            {loading ? "Loading..." : (
              <>Showing <span className="text-white font-medium">{listings.length}</span> of <span className="text-white font-medium">{total}</span> properties</>
            )}
          </span>
        </div>
        <select className="input-field text-sm py-2">
          <option>Newest first</option>
          <option>Price: Low to High</option>
          <option>Price: High to Low</option>
          <option>Area: Largest first</option>
        </select>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 glass rounded-xl border border-rose-500/30 text-rose-300 text-center mb-6 animate-fade-in">
          <svg className="w-6 h-6 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className={viewMode === 'grid' ? "grid sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6" : "space-y-4"}>
          {[...Array(8)].map((_, i) => (
            <div key={i} className="glass rounded-2xl overflow-hidden animate-pulse">
              <div className={viewMode === 'grid' ? "h-52" : "h-32"} style={{ background: 'rgba(51, 65, 85, 0.3)' }} />
              <div className="p-5 space-y-3">
                <div className="h-6 bg-slate-800/50 rounded-lg w-1/2" />
                <div className="h-5 bg-slate-800/50 rounded-lg" />
                <div className="h-4 bg-slate-800/50 rounded-lg w-3/4" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && listings.length === 0 && (
        <div className="text-center py-16 glass rounded-2xl animate-fade-in">
          <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl flex items-center justify-center">
            <svg className="w-10 h-10 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No listings found</h3>
          <p className="text-slate-400 mb-6 max-w-sm mx-auto">
            Try adjusting your filters or scrape some new listings to get started
          </p>
          <div className="flex items-center justify-center gap-3">
            <button 
              onClick={() => setFilters({})} 
              className="btn-secondary"
            >
              Clear Filters
            </button>
            <Link href="/admin" className="btn-primary">
              Scrape Listings
            </Link>
          </div>
        </div>
      )}

      {/* Grid View */}
      {!loading && listings.length > 0 && viewMode === 'grid' && (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
          {listings.map((listing, i) => (
            <div
              key={listing.id}
              className={`animate-fade-in stagger-${Math.min(i + 1, 8)}`}
              style={{ opacity: 0 }}
            >
              <ListingCard listing={listing} />
            </div>
          ))}
        </div>
      )}

      {/* List View */}
      {!loading && listings.length > 0 && viewMode === 'list' && (
        <div className="space-y-4">
          {listings.map((listing, i) => {
            const primaryImage = listing.images?.[0]?.large || listing.images?.[0]?.thumbnail;
            const displayArea = listing.living_area_m2 || listing.metadata_area_m2;
            
            return (
              <Link
                key={listing.id}
                href={`/listings/${listing.id}`}
                className={`flex gap-6 glass rounded-2xl p-4 card-hover animate-fade-in stagger-${Math.min(i + 1, 8)}`}
                style={{ opacity: 0 }}
              >
                {/* Image */}
                <div className="w-48 h-32 flex-shrink-0 rounded-xl overflow-hidden bg-slate-800/50">
                  {primaryImage ? (
                    <img src={primaryImage} alt={listing.title || ''} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-600">
                      <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                      </svg>
                    </div>
                  )}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-semibold text-white mb-1 line-clamp-1">{listing.title || 'Untitled'}</h3>
                      {listing.location_city && (
                        <p className="text-sm text-slate-400 flex items-center gap-1">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          </svg>
                          {listing.location_city}{listing.location_district && `, ${listing.location_district}`}
                        </p>
                      )}
                    </div>
                    <div className="text-xl font-bold gradient-text whitespace-nowrap">
                      €{(listing.price_eur || 0).toLocaleString()}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 mt-3">
                    {displayArea && (
                      <span className="flex items-center gap-1.5 text-sm text-slate-300">
                        <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                        </svg>
                        {displayArea} m²
                      </span>
                    )}
                    {listing.bedroom_count && (
                      <span className="flex items-center gap-1.5 text-sm text-slate-300">
                        🛏️ {listing.bedroom_count} bed
                      </span>
                    )}
                    {listing.bathroom_count && (
                      <span className="flex items-center gap-1.5 text-sm text-slate-300">
                        🚿 {listing.bathroom_count} bath
                      </span>
                    )}
                    {listing.is_new_construction && (
                      <span className="badge badge-success">New Build</span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-10">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="btn-secondary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Previous
          </button>
          
          <div className="flex items-center gap-1 px-2">
            {[...Array(Math.min(5, totalPages))].map((_, i) => {
              let pageNum = i;
              if (totalPages > 5) {
                if (page < 3) {
                  pageNum = i;
                } else if (page > totalPages - 3) {
                  pageNum = totalPages - 5 + i;
                } else {
                  pageNum = page - 2 + i;
                }
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-10 h-10 rounded-xl font-medium text-sm transition-all ${
                    page === pageNum
                      ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-lg shadow-emerald-500/25"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                  }`}
                >
                  {pageNum + 1}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="btn-secondary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
            <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

