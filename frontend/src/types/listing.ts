// Enums matching backend

export enum BuildingType {
  HOUSE = "HOUSE",
  BUILDING = "BUILDING",
}

export enum ConstructionPhase {
  ROH_BAU = "ROH_BAU",
  HIGH_ROH_BAU = "HIGH_ROH_BAU",
  FINISHED_NEW = "FINISHED_NEW",
  OLD_MAINTAINED = "OLD_MAINTAINED",
  NEEDS_RENOVATION = "NEEDS_RENOVATION",
  UNKNOWN = "UNKNOWN",
}

export enum HeatingSystem {
  GAS_FLOOR = "GAS_FLOOR",
  HEAT_PUMP = "HEAT_PUMP",
  ELECTRIC = "ELECTRIC",
  DISTRICT_HEATING = "DISTRICT_HEATING",
  WOOD_PELLET = "WOOD_PELLET",
  UNKNOWN = "UNKNOWN",
}

export enum ParkingType {
  GARAGE = "GARAGE",
  OUTDOOR_OWNED = "OUTDOOR_OWNED",
  PUBLIC_PAID = "PUBLIC_PAID",
  NONE = "NONE",
  UNKNOWN = "UNKNOWN",
}

export enum JobStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
}

export enum ScrapeSource {
  NJUSKALO = "njuskalo",
  CROZILLA = "crozilla",
}

export interface SourceInfo {
  id: string;
  name: string;
  domain: string;
  default_search_url: string;
}

export interface ImageData {
  id?: string;
  thumbnail?: string;
  large?: string;
  src?: string;
  width?: string;
  height?: string;
}

export interface Listing {
  id: string;
  external_id?: string;
  url: string;
  // Basic Info
  title?: string;
  price_eur?: number;
  // Location
  location_city?: string;
  location_district?: string;
  floor_level?: string;
  latitude?: number;
  longitude?: number;
  location_approximate?: boolean;
  distance_from_center?: number;  // km from city center
  // Dimensions
  metadata_area_m2?: number;
  living_area_m2?: number;
  outdoor_area_m2?: number;
  area_conflict?: boolean;
  // Building Specs
  year_built?: number;
  is_new_construction?: boolean;
  bedroom_count?: number;
  bathroom_count?: number;
  parking_type: ParkingType;
  building_type?: BuildingType;
  interior_arranged?: boolean;  // True if furnished/arranged
  has_cellar?: boolean;  // True if includes cellar/storage
  // Condition
  construction_phase: ConstructionPhase;
  renovation_level?: number;  // 1-10 scale
  heating_system: HeatingSystem;
  energy_class?: string;
  // Content
  description?: string;
  images: ImageData[];
  additional_info: Record<string, string[]>;
  // Seller
  seller_name?: string;
  seller_contact?: string;
  scrape_job_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ScrapeJob {
  id: string;
  status: JobStatus;
  urls: string[];
  total_urls: number;
  processed_urls: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ListingsResponse {
  listings: Listing[];
  total: number;
  limit: number;
  offset: number;
}

export interface ListingFilter {
  min_price?: number;
  max_price?: number;
  min_area?: number;
  max_area?: number;
  location_city?: string;
  construction_phase?: ConstructionPhase;
  heating_system?: HeatingSystem;
  parking_type?: ParkingType;
  building_type?: BuildingType;
  interior_arranged?: boolean;  // Filter by furnished/unfurnished
  is_new_construction?: boolean;
  min_bedrooms?: number;
  min_renovation_level?: number;
  max_renovation_level?: number;
  max_distance_from_center?: number;
  require_ml_features?: boolean;  // Only return listings with complete ML features
}

// Display labels
export const BuildingTypeLabels: Record<BuildingType, string> = {
  [BuildingType.HOUSE]: "House",
  [BuildingType.BUILDING]: "Apartment Building",
};

export const ConstructionPhaseLabels: Record<ConstructionPhase, string> = {
  [ConstructionPhase.ROH_BAU]: "Roh-bau (Unfinished)",
  [ConstructionPhase.HIGH_ROH_BAU]: "High Roh-bau",
  [ConstructionPhase.FINISHED_NEW]: "Finished New",
  [ConstructionPhase.OLD_MAINTAINED]: "Old but Maintained",
  [ConstructionPhase.NEEDS_RENOVATION]: "Needs Renovation",
  [ConstructionPhase.UNKNOWN]: "Unknown",
};

export const HeatingSystemLabels: Record<HeatingSystem, string> = {
  [HeatingSystem.GAS_FLOOR]: "Gas Floor Heating",
  [HeatingSystem.HEAT_PUMP]: "Heat Pump",
  [HeatingSystem.ELECTRIC]: "Electric",
  [HeatingSystem.DISTRICT_HEATING]: "District Heating",
  [HeatingSystem.WOOD_PELLET]: "Wood/Pellet",
  [HeatingSystem.UNKNOWN]: "Unknown",
};

export const ParkingTypeLabels: Record<ParkingType, string> = {
  [ParkingType.GARAGE]: "Garage",
  [ParkingType.OUTDOOR_OWNED]: "Outdoor (Owned)",
  [ParkingType.PUBLIC_PAID]: "Public/Paid",
  [ParkingType.NONE]: "None",
  [ParkingType.UNKNOWN]: "Unknown",
};

// Interior arranged labels
export function getInteriorArrangedLabel(arranged?: boolean): { label: string; icon: string } {
  if (arranged === true) {
    return { label: "Furnished", icon: "🛋️" };
  } else if (arranged === false) {
    return { label: "Unfurnished", icon: "📦" };
  }
  return { label: "Unknown", icon: "❓" };
}

export const JobStatusLabels: Record<JobStatus, string> = {
  [JobStatus.PENDING]: "Pending",
  [JobStatus.RUNNING]: "Running",
  [JobStatus.COMPLETED]: "Completed",
  [JobStatus.FAILED]: "Failed",
};

// Helper function to get renovation level label and color
export function getRenovationLevelInfo(level?: number): { label: string; color: string; description: string } {
  if (!level) return { label: "Unknown", color: "bg-slate-500", description: "Not assessed" };
  
  if (level <= 2) {
    return { 
      label: `${level}/10`, 
      color: "bg-rose-500", 
      description: "Needs full renovation" 
    };
  } else if (level <= 4) {
    return { 
      label: `${level}/10`, 
      color: "bg-orange-500", 
      description: "Significant work needed" 
    };
  } else if (level <= 6) {
    return { 
      label: `${level}/10`, 
      color: "bg-amber-500", 
      description: "Some updates needed" 
    };
  } else if (level <= 8) {
    return { 
      label: `${level}/10`, 
      color: "bg-lime-500", 
      description: "Good condition" 
    };
  } else {
    return { 
      label: `${level}/10`, 
      color: "bg-emerald-500", 
      description: "Modern/Move-in ready" 
    };
  }
}

// Helper function to format distance
export function formatDistance(km?: number): string {
  if (!km) return "N/A";
  if (km < 1) {
    return `${Math.round(km * 1000)} m`;
  }
  return `${km.toFixed(1)} km`;
}
