// Enums matching backend

export enum RoomType {
  LIVING_ROOM = "LIVING_ROOM",
  BEDROOM = "BEDROOM",
  KITCHEN = "KITCHEN",
  BATHROOM = "BATHROOM",
  TOILET = "TOILET",
  HALLWAY = "HALLWAY",
  BALCONY = "BALCONY",
  TERRACE = "TERRACE",
  STORAGE = "STORAGE",
  GARAGE = "GARAGE",
  LAUNDRY = "LAUNDRY",
  DINING_ROOM = "DINING_ROOM",
  OFFICE = "OFFICE",
  WALK_IN_CLOSET = "WALK_IN_CLOSET",
  EXTERIOR = "EXTERIOR",
  FLOOR_PLAN = "FLOOR_PLAN",
  OTHER = "OTHER",
}

export enum RoomCondition {
  NEW = "NEW",
  EXCELLENT = "EXCELLENT",
  GOOD = "GOOD",
  FAIR = "FAIR",
  NEEDS_WORK = "NEEDS_WORK",
  ROH_BAU = "ROH_BAU",
  UNKNOWN = "UNKNOWN",
}

export enum RoomFeature {
  FLOOR_HEATING = "FLOOR_HEATING",
  AIR_CONDITIONING = "AIR_CONDITIONING",
  FIREPLACE = "FIREPLACE",
  BUILT_IN_CLOSET = "BUILT_IN_CLOSET",
  BATHTUB = "BATHTUB",
  SHOWER = "SHOWER",
  DOUBLE_SINK = "DOUBLE_SINK",
  KITCHEN_ISLAND = "KITCHEN_ISLAND",
  MODERN_APPLIANCES = "MODERN_APPLIANCES",
  LARGE_WINDOWS = "LARGE_WINDOWS",
  HIGH_CEILING = "HIGH_CEILING",
  PARQUET_FLOOR = "PARQUET_FLOOR",
  TILE_FLOOR = "TILE_FLOOR",
  LAMINATE_FLOOR = "LAMINATE_FLOOR",
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

export interface ImageData {
  id?: string;
  thumbnail?: string;
  large?: string;
  src?: string;
  width?: string;
  height?: string;
}

export interface Room {
  room_type: RoomType;
  image_url?: string;
  condition: RoomCondition;
  condition_reasoning?: string;
  features: string[];
  notes?: string;
  estimated_area_m2?: number;
  from_description?: boolean;
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
  // Condition
  construction_phase: ConstructionPhase;
  heating_system: HeatingSystem;
  energy_class?: string;
  // Content
  description?: string;
  images: ImageData[];
  rooms: Room[];
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
  is_new_construction?: boolean;
  min_bedrooms?: number;
  require_ml_features?: boolean;  // Only return listings with complete ML features
}

// Display labels
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

export const JobStatusLabels: Record<JobStatus, string> = {
  [JobStatus.PENDING]: "Pending",
  [JobStatus.RUNNING]: "Running",
  [JobStatus.COMPLETED]: "Completed",
  [JobStatus.FAILED]: "Failed",
};

export const RoomTypeLabels: Record<RoomType, string> = {
  [RoomType.LIVING_ROOM]: "Living Room",
  [RoomType.BEDROOM]: "Bedroom",
  [RoomType.KITCHEN]: "Kitchen",
  [RoomType.BATHROOM]: "Bathroom",
  [RoomType.TOILET]: "Toilet",
  [RoomType.HALLWAY]: "Hallway",
  [RoomType.BALCONY]: "Balcony",
  [RoomType.TERRACE]: "Terrace",
  [RoomType.STORAGE]: "Storage",
  [RoomType.GARAGE]: "Garage",
  [RoomType.LAUNDRY]: "Laundry",
  [RoomType.DINING_ROOM]: "Dining Room",
  [RoomType.OFFICE]: "Office",
  [RoomType.WALK_IN_CLOSET]: "Walk-in Closet",
  [RoomType.EXTERIOR]: "Exterior",
  [RoomType.FLOOR_PLAN]: "Floor Plan",
  [RoomType.OTHER]: "Other",
};

export const RoomConditionLabels: Record<RoomCondition, string> = {
  [RoomCondition.NEW]: "New",
  [RoomCondition.EXCELLENT]: "Excellent",
  [RoomCondition.GOOD]: "Good",
  [RoomCondition.FAIR]: "Fair",
  [RoomCondition.NEEDS_WORK]: "Needs Work",
  [RoomCondition.ROH_BAU]: "Unfinished",
  [RoomCondition.UNKNOWN]: "Unknown",
};

export const RoomFeatureLabels: Record<RoomFeature, string> = {
  [RoomFeature.FLOOR_HEATING]: "Floor Heating",
  [RoomFeature.AIR_CONDITIONING]: "Air Conditioning",
  [RoomFeature.FIREPLACE]: "Fireplace",
  [RoomFeature.BUILT_IN_CLOSET]: "Built-in Closet",
  [RoomFeature.BATHTUB]: "Bathtub",
  [RoomFeature.SHOWER]: "Shower",
  [RoomFeature.DOUBLE_SINK]: "Double Sink",
  [RoomFeature.KITCHEN_ISLAND]: "Kitchen Island",
  [RoomFeature.MODERN_APPLIANCES]: "Modern Appliances",
  [RoomFeature.LARGE_WINDOWS]: "Large Windows",
  [RoomFeature.HIGH_CEILING]: "High Ceiling",
  [RoomFeature.PARQUET_FLOOR]: "Parquet Floor",
  [RoomFeature.TILE_FLOOR]: "Tile Floor",
  [RoomFeature.LAMINATE_FLOOR]: "Laminate Floor",
};
