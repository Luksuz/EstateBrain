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
  RoomTypeLabels,
  RoomConditionLabels,
  RoomFeatureLabels,
  RoomType,
  RoomCondition,
  RoomFeature,
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
  const [reasoningModal, setReasoningModal] = useState<{ 
    roomIndex: number; 
    reasoning: string;
    roomType: string;
    condition: string;
  } | null>(null);

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

          {/* Description */}
          {listing.description && (
            <div className="glass rounded-2xl p-6 animate-fade-in stagger-4" style={{ opacity: 0 }}>
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

          {/* Rooms Section */}
          {listing.rooms && listing.rooms.length > 0 && (
            <div className="glass rounded-2xl p-6 animate-fade-in stagger-5" style={{ opacity: 0 }}>
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                Room Analysis ({listing.rooms.length})
              </h2>
              
              {/* Room Type Summary */}
              <div className="mb-6 flex flex-wrap gap-2">
                {Object.entries(
                  listing.rooms.reduce((acc, room) => {
                    acc[room.room_type] = (acc[room.room_type] || 0) + 1;
                    return acc;
                  }, {} as Record<string, number>)
                ).map(([type, count]) => (
                  <span
                    key={type}
                    className="px-3 py-1.5 bg-slate-800/50 border border-slate-700/50 rounded-full text-sm text-slate-300"
                  >
                    {RoomTypeLabels[type as RoomType] || type}: {count}
                  </span>
                ))}
              </div>
              
              {/* Room Cards Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                {listing.rooms.map((room, index) => (
                  <div
                    key={index}
                    className="group relative glass-lighter rounded-xl overflow-hidden card-hover"
                  >
                    {/* Room Image */}
                    {room.image_url ? (
                      <div className="aspect-[4/3] relative overflow-hidden">
                        <img
                          src={room.image_url}
                          alt={RoomTypeLabels[room.room_type as RoomType] || room.room_type}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent" />
                        {/* Room Type Badge */}
                        <div className="absolute bottom-2 left-2 px-2 py-1 bg-slate-900/70 backdrop-blur-sm rounded-lg text-xs font-medium text-white">
                          {RoomTypeLabels[room.room_type as RoomType] || room.room_type}
                        </div>
                        {/* Condition Badge with Info Button */}
                        <div className="absolute top-2 right-2 flex items-center gap-1">
                          <div className={`px-2 py-1 rounded-lg text-xs font-medium ${
                            room.condition === 'NEW' || room.condition === 'EXCELLENT' 
                              ? 'bg-emerald-500/80 text-white'
                              : room.condition === 'GOOD' || room.condition === 'FAIR'
                              ? 'bg-amber-500/80 text-white'
                              : room.condition === 'NEEDS_WORK' || room.condition === 'ROH_BAU'
                              ? 'bg-rose-500/80 text-white'
                              : 'bg-slate-600/80 text-slate-200'
                          }`}>
                            {RoomConditionLabels[room.condition] || room.condition}
                          </div>
                          {room.condition_reasoning && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setReasoningModal({ 
                                  roomIndex: index, 
                                  reasoning: room.condition_reasoning!, 
                                  roomType: room.room_type,
                                  condition: room.condition
                                });
                              }}
                              className="w-6 h-6 rounded-full bg-slate-900/70 backdrop-blur-sm text-white hover:bg-emerald-500 transition-colors flex items-center justify-center"
                              title="View AI reasoning"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="aspect-[4/3] bg-slate-800/30 flex items-center justify-center relative">
                        {room.from_description && (
                          <div className="absolute top-2 left-2 px-2 py-1 bg-cyan-500/80 backdrop-blur-sm rounded-lg text-xs font-medium text-white flex items-center gap-1">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Text
                          </div>
                        )}
                        <div className="absolute top-2 right-2 flex items-center gap-1">
                          <div className={`px-2 py-1 rounded-lg text-xs font-medium ${
                            room.condition === 'NEW' || room.condition === 'EXCELLENT' 
                              ? 'bg-emerald-500/80 text-white'
                              : room.condition === 'GOOD' || room.condition === 'FAIR'
                              ? 'bg-amber-500/80 text-white'
                              : room.condition === 'NEEDS_WORK' || room.condition === 'ROH_BAU'
                              ? 'bg-rose-500/80 text-white'
                              : 'bg-slate-600/80 text-slate-200'
                          }`}>
                            {RoomConditionLabels[room.condition] || room.condition}
                          </div>
                        </div>
                        <div className="text-center p-4">
                          <div className="text-3xl mb-1">
                            {room.room_type === 'BEDROOM' ? '🛏️' :
                             room.room_type === 'KITCHEN' ? '🍳' :
                             room.room_type === 'BATHROOM' ? '🚿' :
                             room.room_type === 'TOILET' ? '🚽' :
                             room.room_type === 'LIVING_ROOM' ? '🛋️' :
                             room.room_type === 'BALCONY' ? '🌿' :
                             room.room_type === 'TERRACE' ? '☀️' :
                             room.room_type === 'GARAGE' ? '🚗' :
                             room.room_type === 'EXTERIOR' ? '🏠' :
                             room.room_type === 'FLOOR_PLAN' ? '📐' :
                             room.room_type === 'STORAGE' ? '📦' :
                             room.room_type === 'HALLWAY' ? '🚶' :
                             room.room_type === 'OFFICE' ? '💼' :
                             room.room_type === 'DINING_ROOM' ? '🍽️' :
                             '🚪'}
                          </div>
                          <div className="text-xs font-medium text-slate-400">
                            {RoomTypeLabels[room.room_type as RoomType] || room.room_type}
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Room Details */}
                    {(room.notes || room.features?.length) && (
                      <div className="p-3 space-y-2">
                        {room.notes && (
                          <p className="text-xs text-slate-400 line-clamp-2">{room.notes}</p>
                        )}
                        {room.features && room.features.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {room.features.slice(0, 3).map((feature, i) => (
                              <span key={i} className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded text-[10px] text-emerald-400">
                                {RoomFeatureLabels[feature as RoomFeature] || feature}
                              </span>
                            ))}
                            {room.features.length > 3 && (
                              <span className="px-2 py-0.5 bg-slate-700/50 rounded text-[10px] text-slate-400">
                                +{room.features.length - 3}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
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
              <div className="flex items-center gap-2 text-slate-400 mb-6">
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
                <div className="flex items-center justify-between py-2">
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

      {/* AI Reasoning Modal */}
      {reasoningModal && (
        <div 
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={() => setReasoningModal(null)}
        >
          <div 
            className="relative w-full max-w-lg glass rounded-2xl shadow-2xl overflow-hidden animate-fade-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-800/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">AI Analysis</h3>
                  <p className="text-xs text-slate-400">
                    {RoomTypeLabels[reasoningModal.roomType as RoomType] || reasoningModal.roomType}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setReasoningModal(null)}
                className="w-8 h-8 rounded-lg bg-slate-800/50 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors flex items-center justify-center"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            {/* Modal Body */}
            <div className="p-5">
              {/* Condition Badge */}
              <div className="mb-4 flex items-center gap-2">
                <span className="text-sm text-slate-400">Condition:</span>
                <span className={`badge ${
                  reasoningModal.condition === 'NEW' || reasoningModal.condition === 'EXCELLENT' 
                    ? 'badge-success'
                    : reasoningModal.condition === 'GOOD' || reasoningModal.condition === 'FAIR'
                    ? 'badge-warning'
                    : reasoningModal.condition === 'NEEDS_WORK' || reasoningModal.condition === 'ROH_BAU'
                    ? 'badge-error'
                    : 'badge-info'
                }`}>
                  {RoomConditionLabels[reasoningModal.condition as RoomCondition] || reasoningModal.condition}
                </span>
              </div>
              
              {/* Reasoning Text */}
              <div className="p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
                <p className="text-slate-300 leading-relaxed text-sm">{reasoningModal.reasoning}</p>
              </div>
              <p className="mt-4 text-xs text-slate-500 text-center flex items-center justify-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Generated by AI based on visual analysis
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
