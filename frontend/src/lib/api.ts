import type { Listing, ListingsResponse, ScrapeJob, ListingFilter, ScrapeSource, SourceInfo } from "@/types/listing";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Location types
export interface LocationData {
  [zupanija: string]: string[];
}

// ML types
export interface MLStats {
  total_count: number;
  avg_price: number;
  median_price: number;
  min_price: number;
  max_price: number;
  avg_area: number;
  median_area: number;
  avg_bedrooms: number;
  cities: string[];
  city_counts: Record<string, number>;
  construction_phase_counts: Record<string, number>;
  new_construction_pct: number;
}

export interface CorrelationResponse {
  correlation_matrix: Record<string, Record<string, number>>;
  target_correlations: Record<string, number>;
  feature_names: string[];
  sample_count: number;
}

export interface ModelResult {
  model_type: string;
  r2_score: number;
  rmse: number;
  mae: number;
  cv_scores: number[];
  cv_mean: number;
  cv_std: number;
  feature_importance: Record<string, number> | null;
  coefficients: Record<string, number> | null;
  predictions: number[] | null;
  actual: number[] | null;
  sample_count: number;
}

export interface TrainRequest {
  model_type: string;
  test_size?: number;
  cv_folds?: number;
  // Regularization
  alpha?: number;
  l1_ratio?: number;
  // Tree params
  max_depth?: number;
  n_estimators?: number;
  learning_rate?: number;
  // KNN
  n_neighbors?: number;
  // SVR
  C?: number;
  kernel?: string;
  // MLP (Neural Network)
  hidden_layer_1?: number;
  hidden_layer_2?: number;
  activation?: string;
  learning_rate_init?: number;
  max_iter?: number;
  // Filters
  min_price?: number;
  max_price?: number;
  min_area?: number;
  max_area?: number;
  location_district?: string;
  // Construction filters
  exclude_new_construction?: boolean;
  only_new_construction?: boolean;
}

export interface NeighborhoodStats {
  name: string;
  count: number;
  avg_price: number;
  price_per_m2: number;
}

export interface DealAnalysis {
  listing_id: string;
  title: string;
  url: string;
  location_district: string | null;
  actual_price: number;
  predicted_price: number;
  difference: number;
  difference_pct: number;
  deal_score: "great_deal" | "good_deal" | "fair" | "overpriced" | "very_overpriced";
  living_area_m2: number | null;
  bedroom_count: number | null;
  bathroom_count: number | null;
  year_built: number | null;
  is_new_construction: boolean;
  image_url: string | null;
}

export interface DealsResponse {
  model_used: string;
  total_analyzed: number;
  good_deals: DealAnalysis[];
  bad_deals: DealAnalysis[];
  average_error_pct: number;
}

export interface ManualPredictRequest {
  model_type: string;
  title?: string;
  actual_price?: number;
  location_district?: string;
  living_area_m2: number;
  bedroom_count?: number;
  bathroom_count?: number;
  outdoor_area_m2?: number;
  year_built?: number;
  is_new_construction?: boolean;
  has_garage?: boolean;
  description?: string;
  images?: string[];  // Base64 encoded compressed images
}

export interface RawDataPredictRequest {
  model_type: string;
  zupanija?: string;
  title?: string;
  price?: string;  // Price string like "150.000 €"
  ad_id?: string;
  highlighted_attributes?: Record<string, string>;
  basic_details?: Record<string, string>;
  description?: string;
  additional_info?: Record<string, string>;
  category_path?: string[];
  images?: string[];  // URLs or base64 encoded
}

export interface RawDataPredictResponse {
  title: string;
  actual_price: number | null;
  predicted_price: number;
  difference: number | null;
  difference_pct: number | null;
  deal_score: "great_deal" | "good_deal" | "fair" | "overpriced" | "very_overpriced" | null;
  features_used: {
    living_area_m2: number;
    bedroom_count: number;
    bathroom_count: number;
    outdoor_area_m2?: number;
    is_new_construction: boolean;
    has_garage?: boolean;
    location: string;
  };
  model_used: string;
  confidence_note: string;
  classified_data: {
    basic_info: {
      title: string | null;
      price_euros: number | null;
      listing_id: string | null;
    };
    location: {
      city: string | null;
      district: string | null;
      floor_level: string | null;
    };
    dimensions: {
      metadata_area_m2: number | null;
      living_area_m2: number | null;
      outdoor_area_m2: number | null;
      area_conflict: boolean | null;
    };
    building_specs: {
      year_built: number | null;
      is_new_construction: boolean | null;
      bedroom_count: number | null;
      bathroom_count: number | null;
      parking_type: string | null;
    };
    condition: {
      construction_phase: string | null;
      heating_system: string | null;
      energy_class: string | null;
    };
  };
  rooms: Array<{
    room_type: string | null;
    image_url: string | null;
    condition: string | null;
    condition_reasoning: string | null;
    features: string[];
    notes: string | null;
    from_description: boolean | null;
  }> | null;
}

export interface PredictFromUrlResponse {
  url: string;
  title: string;
  actual_price: number | null;
  predicted_price: number;
  difference: number | null;
  difference_pct: number | null;
  deal_score: "great_deal" | "good_deal" | "fair" | "overpriced" | "very_overpriced" | null;
  features_used: {
    living_area_m2: number;
    bedroom_count: number;
    bathroom_count: number;
    year_built?: number;
    outdoor_area_m2?: number;
    is_new_construction: boolean;
    has_garage?: boolean;
    location: string;
  };
  model_used: string;
  confidence_note: string;
}

export interface ModelInfo {
  type: string;
  name: string;
  category: string;
  description: string;
  params: string[];
  recommended: boolean;
}

export interface RepredictResponse {
  predicted_price: number;
  model_used: string;
  difference: number | null;
  difference_pct: number | null;
  deal_score: "great_deal" | "good_deal" | "fair" | "overpriced" | "very_overpriced" | null;
  confidence_note: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Locations
  async getAllLocations(): Promise<LocationData> {
    return this.request<LocationData>("/api/locations/all");
  }

  async getZupanije(): Promise<string[]> {
    return this.request<string[]>("/api/locations/zupanije");
  }

  async getDistricts(zupanija: string): Promise<string[]> {
    return this.request<string[]>(`/api/locations/zupanije/${encodeURIComponent(zupanija)}/districts`);
  }

  async getSearchUrl(zupanija: string, district?: string, propertyType: string = "prodaja-stanova"): Promise<{ url: string }> {
    const params = new URLSearchParams();
    params.append("zupanija", zupanija);
    if (district) params.append("district", district);
    params.append("property_type", propertyType);
    return this.request(`/api/locations/search-url?${params.toString()}`);
  }

  // Scrape Jobs
  async createScrapeJob(urls: string[]): Promise<ScrapeJob> {
    return this.request<ScrapeJob>("/api/scrape/jobs", {
      method: "POST",
      body: JSON.stringify({ urls }),
    });
  }

  async getScrapeSources(): Promise<{ sources: SourceInfo[] }> {
    return this.request<{ sources: SourceInfo[] }>("/api/scrape/sources");
  }

  async scrapeFromSearch(
    options: {
      source?: ScrapeSource;
      searchUrl?: string;
      maxPages?: number;
      startPage?: number;
      endPage?: number;
      forceRescrape?: boolean;
      zupanija?: string;
    } = {}
  ): Promise<{
    source: string;
    search_url: string;
    pages_scraped: number;
    total_listings: number;
    new_listings: number;
    existing_listings: number;
    listing_urls: string[];
    job_id: string | null;
  }> {
    return this.request("/api/scrape/from-search", {
      method: "POST",
      body: JSON.stringify({ 
        source: options.source ?? null,
        search_url: options.searchUrl ?? null, 
        max_pages: options.maxPages ?? 1,
        start_page: options.startPage ?? 1,
        end_page: options.endPage ?? null,
        force_rescrape: options.forceRescrape ?? false,
        zupanija: options.zupanija ?? null,
      }),
    });
  }

  async getScrapeJobs(limit = 50, offset = 0): Promise<ScrapeJob[]> {
    return this.request<ScrapeJob[]>(`/api/scrape/jobs?limit=${limit}&offset=${offset}`);
  }

  async getScrapeJob(jobId: string): Promise<ScrapeJob> {
    return this.request<ScrapeJob>(`/api/scrape/jobs/${jobId}`);
  }

  // Listings
  async getListings(
    filters: ListingFilter = {},
    limit = 20,
    offset = 0,
    sortBy = "created_at",
    sortDesc = true
  ): Promise<ListingsResponse> {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());
    params.append("offset", offset.toString());
    params.append("sort_by", sortBy);
    params.append("sort_desc", sortDesc.toString());

    if (filters.min_price) params.append("min_price", filters.min_price.toString());
    if (filters.max_price) params.append("max_price", filters.max_price.toString());
    if (filters.min_area) params.append("min_area", filters.min_area.toString());
    if (filters.max_area) params.append("max_area", filters.max_area.toString());
    if (filters.location_city) params.append("location_city", filters.location_city);
    if (filters.construction_phase) params.append("construction_phase", filters.construction_phase);
    if (filters.heating_system) params.append("heating_system", filters.heating_system);
    if (filters.parking_type) params.append("parking_type", filters.parking_type);
    if (filters.is_new_construction !== undefined) params.append("is_new_construction", filters.is_new_construction.toString());
    if (filters.min_bedrooms) params.append("min_bedrooms", filters.min_bedrooms.toString());
    if (filters.require_ml_features) params.append("require_ml_features", "true");

    return this.request<ListingsResponse>(`/api/listings?${params.toString()}`);
  }

  async getListing(listingId: string): Promise<Listing> {
    return this.request<Listing>(`/api/listings/${listingId}`);
  }

  async deleteListing(listingId: string): Promise<void> {
    await this.request(`/api/listings/${listingId}`, { method: "DELETE" });
  }

  // Machine Learning
  async getMLStats(filters?: {
    min_price?: number;
    max_price?: number;
    min_area?: number;
    max_area?: number;
    location_city?: string;
  }): Promise<MLStats> {
    const params = new URLSearchParams();
    if (filters?.min_price) params.append("min_price", filters.min_price.toString());
    if (filters?.max_price) params.append("max_price", filters.max_price.toString());
    if (filters?.min_area) params.append("min_area", filters.min_area.toString());
    if (filters?.max_area) params.append("max_area", filters.max_area.toString());
    if (filters?.location_city) params.append("location_city", filters.location_city);
    return this.request<MLStats>(`/api/ml/stats?${params.toString()}`);
  }

  async getCorrelation(filters?: {
    min_price?: number;
    max_price?: number;
    min_area?: number;
    max_area?: number;
    location_city?: string;
  }): Promise<CorrelationResponse> {
    const params = new URLSearchParams();
    if (filters?.min_price) params.append("min_price", filters.min_price.toString());
    if (filters?.max_price) params.append("max_price", filters.max_price.toString());
    if (filters?.min_area) params.append("min_area", filters.min_area.toString());
    if (filters?.max_area) params.append("max_area", filters.max_area.toString());
    if (filters?.location_city) params.append("location_city", filters.location_city);
    return this.request<CorrelationResponse>(`/api/ml/correlation?${params.toString()}`);
  }

  async trainModel(request: TrainRequest): Promise<ModelResult> {
    return this.request<ModelResult>("/api/ml/train", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async getAvailableModels(): Promise<{ models: ModelInfo[] }> {
    return this.request<{ models: ModelInfo[] }>("/api/ml/models");
  }

  async getNeighborhoods(): Promise<{ neighborhoods: NeighborhoodStats[] }> {
    return this.request<{ neighborhoods: NeighborhoodStats[] }>("/api/ml/neighborhoods");
  }

  async analyzeDeals(options?: {
    model_type?: string;
    min_price?: number;
    max_price?: number;
    exclude_new_construction?: boolean;
    location_district?: string;
    top_n?: number;
  }): Promise<DealsResponse> {
    const params = new URLSearchParams();
    if (options?.model_type) params.append("model_type", options.model_type);
    if (options?.min_price) params.append("min_price", options.min_price.toString());
    if (options?.max_price) params.append("max_price", options.max_price.toString());
    if (options?.exclude_new_construction) params.append("exclude_new_construction", "true");
    if (options?.location_district) params.append("location_district", options.location_district);
    if (options?.top_n) params.append("top_n", options.top_n.toString());
    return this.request<DealsResponse>(`/api/ml/deals?${params.toString()}`);
  }

  async predictFromUrl(url: string, modelType: string = "ridge"): Promise<PredictFromUrlResponse> {
    return this.request<PredictFromUrlResponse>("/api/ml/predict-url", {
      method: "POST",
      body: JSON.stringify({ url, model_type: modelType }),
    });
  }

  async predictManual(data: ManualPredictRequest): Promise<PredictFromUrlResponse> {
    return this.request<PredictFromUrlResponse>("/api/ml/predict-manual", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async predictFromRawData(data: RawDataPredictRequest): Promise<RawDataPredictResponse> {
    return this.request<RawDataPredictResponse>("/api/ml/predict-from-data", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async repredict(
    modelType: string,
    features: Record<string, unknown>,
    actualPrice?: number,
    title?: string
  ): Promise<RepredictResponse> {
    return this.request<RepredictResponse>("/api/ml/repredict", {
      method: "POST",
      body: JSON.stringify({
        model_type: modelType,
        features,
        actual_price: actualPrice,
        title,
      }),
    });
  }
}

export const api = new ApiClient(API_URL);
