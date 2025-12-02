import Link from "next/link";
import {
  Listing,
  ConstructionPhase,
  ConstructionPhaseLabels,
  BuildingType,
  BuildingTypeLabels,
  getRenovationLevelInfo,
  formatDistance,
  getInteriorArrangedLabel,
} from "@/types/listing";

interface ListingCardProps {
  listing: Listing;
}

export function ListingCard({ listing }: ListingCardProps) {
  const formatPrice = (price?: number) => {
    if (!price) return "Price on request";
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }).format(price);
  };

  const getPhaseColor = (phase: ConstructionPhase) => {
    switch (phase) {
      case ConstructionPhase.FINISHED_NEW:
        return "bg-emerald-500/15 text-emerald-400 border-emerald-500/25";
      case ConstructionPhase.OLD_MAINTAINED:
        return "bg-cyan-500/15 text-cyan-400 border-cyan-500/25";
      case ConstructionPhase.ROH_BAU:
      case ConstructionPhase.HIGH_ROH_BAU:
        return "bg-amber-500/15 text-amber-400 border-amber-500/25";
      case ConstructionPhase.NEEDS_RENOVATION:
        return "bg-rose-500/15 text-rose-400 border-rose-500/25";
      default:
        return "bg-slate-500/15 text-slate-400 border-slate-500/25";
    }
  };

  const primaryImage =
    listing.images?.[0]?.large ||
    listing.images?.[0]?.thumbnail ||
    listing.images?.[0]?.src;

  // Use living_area_m2 as the trusted area
  const displayArea = listing.living_area_m2 || listing.metadata_area_m2;
  const renovationInfo = getRenovationLevelInfo(listing.renovation_level);

  return (
    <Link href={`/listings/${listing.id}`} className="group block h-full">
      <div className="h-full glass rounded-2xl overflow-hidden card-hover">
        {/* Image */}
        <div className="relative h-52 bg-slate-800/50 overflow-hidden">
          {primaryImage ? (
            <img
              src={primaryImage}
              alt={listing.title || "Property"}
              className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900">
              <svg className="w-16 h-16 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
            </div>
          )}

          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900/90 via-slate-900/20 to-transparent" />

          {/* Top Badges */}
          <div className="absolute top-3 left-3 flex items-center gap-2">
            {listing.is_new_construction && (
              <span className="px-2.5 py-1 text-xs font-semibold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-full shadow-lg shadow-emerald-500/25">
                NEW BUILD
              </span>
            )}
            {listing.building_type && (
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                listing.building_type === BuildingType.HOUSE 
                  ? "bg-amber-500/90 text-white" 
                  : "bg-violet-500/90 text-white"
              }`}>
                {listing.building_type === BuildingType.HOUSE ? "🏠" : "🏢"} {BuildingTypeLabels[listing.building_type]}
              </span>
            )}
            {listing.interior_arranged !== undefined && listing.interior_arranged !== null && (
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                listing.interior_arranged 
                  ? "bg-teal-500/90 text-white" 
                  : "bg-slate-500/90 text-white"
              }`}>
                {getInteriorArrangedLabel(listing.interior_arranged).icon} {getInteriorArrangedLabel(listing.interior_arranged).label}
              </span>
            )}
            {listing.area_conflict && (
              <span className="px-2 py-1 text-xs font-medium bg-amber-500/90 text-white rounded-full" title="Area discrepancy detected">
                ⚠️ Check
              </span>
            )}
          </div>

          {/* Renovation Level Badge (top right) */}
          {listing.renovation_level && (
            <div className="absolute top-3 right-3">
              <div className={`px-2.5 py-1 rounded-full text-xs font-bold text-white ${renovationInfo.color}`} title={renovationInfo.description}>
                {renovationInfo.label}
              </div>
            </div>
          )}

          {/* Image Count */}
          {listing.images && listing.images.length > 1 && (
            <div className="absolute bottom-14 right-3">
              <span className="px-2 py-1 text-xs font-medium bg-slate-900/70 text-white rounded-full backdrop-blur-sm flex items-center gap-1">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {listing.images.length}
              </span>
            </div>
          )}

          {/* Bottom Price Overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-4">
            <div className="text-2xl font-bold text-white drop-shadow-lg">
              {formatPrice(listing.price_eur)}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Title */}
          <h3 className="text-white font-semibold line-clamp-2 min-h-[3rem] group-hover:text-emerald-400 transition-colors">
            {listing.title || "Untitled Listing"}
          </h3>

          {/* Details Grid */}
          <div className="flex flex-wrap gap-3">
            {displayArea && (
              <div className="flex items-center gap-1.5 text-sm text-slate-300">
                <div className="w-7 h-7 rounded-lg bg-slate-800/80 flex items-center justify-center">
                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  </svg>
                </div>
                <span>{displayArea} m²</span>
              </div>
            )}
            {listing.bedroom_count && (
              <div className="flex items-center gap-1.5 text-sm text-slate-300">
                <div className="w-7 h-7 rounded-lg bg-slate-800/80 flex items-center justify-center">
                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                </div>
                <span>{listing.bedroom_count} bed</span>
              </div>
            )}
            {listing.distance_from_center !== undefined && listing.distance_from_center !== null && (
              <div className="flex items-center gap-1.5 text-sm text-slate-300">
                <div className="w-7 h-7 rounded-lg bg-slate-800/80 flex items-center justify-center">
                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <span>{formatDistance(listing.distance_from_center)}</span>
              </div>
            )}
          </div>

          {/* Location */}
          {listing.location_city && (
            <div className="flex items-center gap-2 text-sm text-slate-400 pt-2 border-t border-slate-800/50">
              <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="truncate">
                {listing.location_city}
                {listing.location_district && `, ${listing.location_district}`}
              </span>
            </div>
          )}

          {/* Construction Phase Badge */}
          {listing.construction_phase && listing.construction_phase !== ConstructionPhase.UNKNOWN && (
            <div className="pt-1">
              <span className={`inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-full border ${getPhaseColor(listing.construction_phase)}`}>
                {ConstructionPhaseLabels[listing.construction_phase]}
              </span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
