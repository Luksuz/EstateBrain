"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import {
  Listing,
  ConstructionPhase,
  ConstructionPhaseLabels,
  HeatingSystemLabels,
  ParkingTypeLabels,
  BuildingType,
  BuildingTypeLabels,
  getRenovationLevelInfo,
  formatDistance,
} from "@/types/listing";

export default function ListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const [listing, setListing] = useState<Listing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeImage, setActiveImage] = useState(0);

  useEffect(() => {
    const fetchListing = async () => {
      try {
        const data = await api.getListing(resolvedParams.id);
        setListing(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load listing");
      } finally {
        setLoading(false);
      }
    };

    fetchListing();
  }, [resolvedParams.id]);

  const formatPrice = (price?: number) => {
    if (!price) return "Price on request";
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(price);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-slate-400">Loading property details...</p>
        </div>
      </div>
    );
  }

  if (error || !listing) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center glass rounded-2xl p-8 max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 bg-rose-500/20 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">{error || "Listing not found"}</h1>
          <p className="text-slate-400 mb-6">We couldn't find the property you're looking for.</p>
          <Link href="/" className="btn-primary inline-flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const images = listing.images || [];
  const currentImage = images[activeImage]?.large || images[activeImage]?.thumbnail || images[activeImage]?.src;
  const displayArea = listing.living_area_m2 || listing.metadata_area_m2;
  const renovationInfo = getRenovationLevelInfo(listing.renovation_level);

  return (
    <div className="relative p-4 lg:p-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-400 mb-6 animate-fade-in">
        <Link href="/" className="hover:text-white transition-colors">Dashboard</Link>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <Link href="/" className="hover:text-white transition-colors">Listings</Link>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-slate-500 truncate max-w-[200px]">{listing.title || listing.id}</span>
      </div>

      <div className="grid lg:grid-cols-5 gap-8">
        {/* Left Column - Images */}
        <div className="lg:col-span-3 space-y-4">
          {/* Main Image */}
          <div className="relative aspect-[16/10] glass rounded-2xl overflow-hidden animate-fade-in stagger-1" style={{ opacity: 0 }}>
            {currentImage ? (
              <img src={currentImage} alt={listing.title || "Property"} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
                <svg className="w-24 h-24 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              </div>
            )}
            
            {/* Top Badges */}
            <div className="absolute top-4 left-4 flex items-center gap-2">
              {listing.is_new_construction && (
                <span className="px-3 py-1.5 text-sm font-semibold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-full shadow-lg shadow-emerald-500/25">
                  NEW BUILD
                </span>
              )}
              {listing.building_type && (
                <span className={`px-3 py-1.5 text-sm font-medium rounded-full ${
                  listing.building_type === BuildingType.HOUSE 
                    ? "bg-amber-500/90 text-white" 
                    : "bg-violet-500/90 text-white"
                }`}>
                  {listing.building_type === BuildingType.HOUSE ? "🏠" : "🏢"} {BuildingTypeLabels[listing.building_type]}
                </span>
              )}
              {listing.area_conflict && (
                <span className="px-3 py-1.5 text-sm font-medium bg-amber-500/90 text-white rounded-full">
                  ⚠️ Area Discrepancy
                </span>
              )}
            </div>

            {/* Navigation Arrows */}
            {images.length > 1 && (
              <>
                <button
                  onClick={() => setActiveImage((prev) => (prev === 0 ? images.length - 1 : prev - 1))}
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-slate-900/70 backdrop-blur-sm text-white hover:bg-slate-800 transition-colors flex items-center justify-center"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <button
                  onClick={() => setActiveImage((prev) => (prev === images.length - 1 ? 0 : prev + 1))}
                  className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-slate-900/70 backdrop-blur-sm text-white hover:bg-slate-800 transition-colors flex items-center justify-center"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </>
            )}

            {/* Image Counter */}
            {images.length > 1 && (
              <div className="absolute bottom-4 right-4 px-3 py-1.5 bg-slate-900/70 backdrop-blur-sm rounded-full text-sm text-white">
                {activeImage + 1} / {images.length}
              </div>
            )}
          </div>

          {/* Thumbnail Strip */}
          {images.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-2 animate-fade-in stagger-2" style={{ opacity: 0 }}>
              {images.map((img, index) => (
                <button
                  key={index}
                  onClick={() => setActiveImage(index)}
                  className={`relative flex-shrink-0 w-20 h-20 rounded-xl overflow-hidden transition-all ${
                    activeImage === index 
                      ? "ring-2 ring-emerald-500 ring-offset-2 ring-offset-slate-950" 
                      : "opacity-60 hover:opacity-100"
                  }`}
                >
                  <img src={img.thumbnail || img.large || img.src} alt={`Image ${index + 1}`} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}

          {/* Renovation Level Card */}
          {listing.renovation_level && (
            <div className="glass rounded-2xl p-6 animate-fade-in stagger-3" style={{ opacity: 0 }}>
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Renovation Assessment
              </h2>
              
              {/* Visual Bar */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-slate-400">Condition Level</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-bold text-white ${renovationInfo.color}`}>
                    {renovationInfo.label}
                  </span>
                </div>
                <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${renovationInfo.color} transition-all duration-500`}
                    style={{ width: `${(listing.renovation_level / 10) * 100}%` }}
                  />
                </div>
                <p className="text-sm text-slate-400 mt-2">{renovationInfo.description}</p>
              </div>

              {/* Scale Legend */}
              <div className="grid grid-cols-5 gap-1 text-xs text-center">
                <div className="p-2 bg-rose-500/20 rounded-lg">
                  <div className="font-bold text-rose-400">1-2</div>
                  <div className="text-slate-500">Full reno</div>
                </div>
                <div className="p-2 bg-orange-500/20 rounded-lg">
                  <div className="font-bold text-orange-400">3-4</div>
                  <div className="text-slate-500">Major work</div>
                </div>
                <div className="p-2 bg-amber-500/20 rounded-lg">
                  <div className="font-bold text-amber-400">5-6</div>
                  <div className="text-slate-500">Updates</div>
                </div>
                <div className="p-2 bg-lime-500/20 rounded-lg">
                  <div className="font-bold text-lime-400">7-8</div>
                  <div className="text-slate-500">Good</div>
                </div>
                <div className="p-2 bg-emerald-500/20 rounded-lg">
                  <div className="font-bold text-emerald-400">9-10</div>
                  <div className="text-slate-500">Modern</div>
                </div>
              </div>
            </div>
          )}

          {/* Map */}
          {listing.latitude && listing.longitude && (
            <div className="glass rounded-2xl p-6 animate-fade-in stagger-4" style={{ opacity: 0 }}>
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Location
                {listing.location_approximate && (
                  <span className="text-xs font-normal text-amber-400 ml-2">(approximate)</span>
                )}
              </h2>
              
              {/* OpenStreetMap Embed */}
              <div className="relative aspect-[16/9] rounded-xl overflow-hidden bg-slate-800">
                <iframe
                  src={`https://www.openstreetmap.org/export/embed.html?bbox=${listing.longitude - 0.01},${listing.latitude - 0.008},${listing.longitude + 0.01},${listing.latitude + 0.008}&layer=mapnik&marker=${listing.latitude},${listing.longitude}`}
                  className="w-full h-full border-0"
                  loading="lazy"
                  title="Property Location"
                />
                
                {/* Overlay for click to open larger map */}
                <a
                  href={`https://www.openstreetmap.org/?mlat=${listing.latitude}&mlon=${listing.longitude}#map=16/${listing.latitude}/${listing.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="absolute bottom-3 right-3 px-3 py-1.5 bg-slate-900/90 backdrop-blur-sm text-white text-sm rounded-lg hover:bg-slate-800 transition-colors flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  Open in Maps
                </a>
              </div>
              
              {/* Distance info */}
              {listing.distance_from_center !== undefined && listing.distance_from_center !== null && (
                <div className="mt-4 flex items-center justify-between text-sm">
                  <span className="text-slate-400">Distance from {listing.location_district || 'city'} center</span>
                  <span className="text-emerald-400 font-medium">{formatDistance(listing.distance_from_center)}</span>
                </div>
              )}
              
              {/* Coordinates */}
              <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                <span>Coordinates</span>
                <span className="font-mono">{listing.latitude.toFixed(5)}, {listing.longitude.toFixed(5)}</span>
              </div>
            </div>
          )}

          {/* Description */}
          {listing.description && (
            <div className="glass rounded-2xl p-6 animate-fade-in stagger-5" style={{ opacity: 0 }}>
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h7" />
                </svg>
                Description
              </h2>
              <div className="text-slate-300 whitespace-pre-line leading-relaxed text-sm">
                {listing.description}
              </div>
            </div>
          )}
        </div>

        {/* Right Column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Price Card */}
          <div className="glass rounded-2xl p-6 animate-fade-in stagger-2" style={{ opacity: 0 }}>
            <div className="flex items-center justify-between mb-4">
              <div className="text-3xl font-bold gradient-text">{formatPrice(listing.price_eur)}</div>
              {displayArea && listing.price_eur && (
                <div className="text-sm text-slate-400">
                  {Math.round(listing.price_eur / displayArea).toLocaleString()} €/m²
                </div>
              )}
            </div>
            <h1 className="text-xl font-semibold text-white mb-4">{listing.title || "Untitled Listing"}</h1>
            
            {/* Location */}
            {listing.location_city && (
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>
                  {listing.location_city}
                  {listing.location_district && `, ${listing.location_district}`}
                </span>
              </div>
            )}

            {/* Distance from center */}
            {listing.distance_from_center !== undefined && listing.distance_from_center !== null && (
              <div className="flex items-center gap-2 text-slate-400 mb-6">
                <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
                <span>{formatDistance(listing.distance_from_center)} from city center</span>
              </div>
            )}

            {/* CTA Button */}
            <a
              href={listing.url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              View Original Listing
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>

          {/* Key Details */}
          <div className="glass rounded-2xl p-6 animate-fade-in stagger-3" style={{ opacity: 0 }}>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Key Details
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {displayArea && (
                <div className="stat-card">
                  <div className="text-xs text-slate-500 mb-1">Living Area</div>
                  <div className="text-lg font-semibold text-white">{displayArea} m²</div>
                </div>
              )}
              {listing.bedroom_count && (
                <div className="stat-card">
                  <div className="text-xs text-slate-500 mb-1">Bedrooms</div>
                  <div className="text-lg font-semibold text-white">{listing.bedroom_count}</div>
                </div>
              )}
              {listing.bathroom_count && (
                <div className="stat-card">
                  <div className="text-xs text-slate-500 mb-1">Bathrooms</div>
                  <div className="text-lg font-semibold text-white">{listing.bathroom_count}</div>
                </div>
              )}
              {listing.floor_level && (
                <div className="stat-card">
                  <div className="text-xs text-slate-500 mb-1">Floor</div>
                  <div className="text-lg font-semibold text-white">{listing.floor_level}</div>
                </div>
              )}
              {listing.year_built && (
                <div className="stat-card">
                  <div className="text-xs text-slate-500 mb-1">Year Built</div>
                  <div className="text-lg font-semibold text-white">{listing.year_built}</div>
                </div>
              )}
              {listing.outdoor_area_m2 && (
                <div className="stat-card">
                  <div className="text-xs text-slate-500 mb-1">Outdoor Area</div>
                  <div className="text-lg font-semibold text-white">{listing.outdoor_area_m2} m²</div>
                </div>
              )}
            </div>
          </div>

          {/* Property Specs */}
          <div className="glass rounded-2xl p-6 animate-fade-in stagger-4" style={{ opacity: 0 }}>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Specifications
            </h2>
            <div className="space-y-3 text-sm">
              {listing.building_type && (
                <div className="flex items-center justify-between py-2 border-b border-slate-800/50">
                  <span className="text-slate-400">Building Type</span>
                  <span className="text-white font-medium flex items-center gap-1">
                    {listing.building_type === BuildingType.HOUSE ? "🏠" : "🏢"}
                    {BuildingTypeLabels[listing.building_type]}
                  </span>
                </div>
              )}
              {listing.construction_phase !== ConstructionPhase.UNKNOWN && (
                <div className="flex items-center justify-between py-2 border-b border-slate-800/50">
                  <span className="text-slate-400">Construction</span>
                  <span className="text-white font-medium">{ConstructionPhaseLabels[listing.construction_phase]}</span>
                </div>
              )}
              <div className="flex items-center justify-between py-2 border-b border-slate-800/50">
                <span className="text-slate-400">Heating</span>
                <span className="text-white font-medium">{HeatingSystemLabels[listing.heating_system]}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-slate-800/50">
                <span className="text-slate-400">Parking</span>
                <span className="text-white font-medium">{ParkingTypeLabels[listing.parking_type]}</span>
              </div>
              {listing.energy_class && (
                <div className="flex items-center justify-between py-2 border-b border-slate-800/50">
                  <span className="text-slate-400">Energy Class</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    listing.energy_class.startsWith('A') ? 'bg-emerald-500/20 text-emerald-400' :
                    listing.energy_class.startsWith('B') ? 'bg-cyan-500/20 text-cyan-400' :
                    listing.energy_class.startsWith('C') ? 'bg-amber-500/20 text-amber-400' :
                    'bg-rose-500/20 text-rose-400'
                  }`}>
                    {listing.energy_class}
                  </span>
                </div>
              )}
              {listing.interior_arranged !== undefined && listing.interior_arranged !== null && (
                <div className="flex items-center justify-between py-2 border-b border-slate-800/50">
                  <span className="text-slate-400">Interior</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    listing.interior_arranged ? 'bg-teal-500/20 text-teal-400' : 'bg-slate-500/20 text-slate-400'
                  }`}>
                    {listing.interior_arranged ? '🛋️ Furnished' : '📦 Unfurnished'}
                  </span>
                </div>
              )}
              {listing.has_cellar !== undefined && listing.has_cellar !== null && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-slate-400">Storage</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    listing.has_cellar ? 'bg-violet-500/20 text-violet-400' : 'bg-slate-500/20 text-slate-400'
                  }`}>
                    {listing.has_cellar ? '📦 Has Cellar' : 'No Cellar'}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Seller Info */}
          {listing.seller_name && (
            <div className="glass rounded-2xl p-6 animate-fade-in stagger-5" style={{ opacity: 0 }}>
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Listed By
              </h2>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-semibold">
                  {listing.seller_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="font-medium text-white">{listing.seller_name}</div>
                  <div className="text-sm text-slate-400">Seller</div>
                </div>
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="text-center text-xs text-slate-500 animate-fade-in stagger-6" style={{ opacity: 0 }}>
            <p>Listed {formatDate(listing.created_at)}</p>
            <p className="mt-1">ID: {listing.external_id || listing.id}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
