"use client";

import { useState, useRef } from "react";
import { api, PredictFromUrlResponse, ManualPredictRequest, RawDataPredictRequest, RawDataPredictResponse, RepredictResponse } from "@/lib/api";

// Deal score styling
const DEAL_SCORE_STYLES: Record<string, { bg: string; text: string; label: string; emoji: string; gradient: string }> = {
  great_deal: { bg: "bg-emerald-500/20", text: "text-emerald-400", label: "Great Deal!", emoji: "🔥", gradient: "from-emerald-500 to-green-500" },
  good_deal: { bg: "bg-green-500/20", text: "text-green-400", label: "Good Deal", emoji: "✨", gradient: "from-green-500 to-emerald-500" },
  fair: { bg: "bg-slate-500/20", text: "text-slate-400", label: "Fair Price", emoji: "⚖️", gradient: "from-slate-500 to-slate-400" },
  overpriced: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Overpriced", emoji: "⚠️", gradient: "from-amber-500 to-orange-500" },
  very_overpriced: { bg: "bg-red-500/20", text: "text-red-400", label: "Very Overpriced", emoji: "🚨", gradient: "from-red-500 to-rose-500" },
};

// Districts for dropdown
const DISTRICTS = [
  "Varaždin", "Novi Marof", "Ivanec", "Ludbreg", "Lepoglava",
  "Varaždinske Toplice", "Kućan Marof", "Hrašćica", "Sračinec",
  "Gornji Kneginec", "Petrijanec", "Maruševec", "Trnovec Bartolovečki",
];

// Image compression utility
async function compressImage(file: File, maxWidth: number = 800, quality: number = 0.7): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        let { width, height } = img;
        
        // Scale down if needed
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
        
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Failed to get canvas context"));
          return;
        }
        
        ctx.drawImage(img, 0, 0, width, height);
        
        // Convert to base64 with compression
        const base64 = canvas.toDataURL("image/jpeg", quality);
        resolve(base64);
      };
      img.onerror = () => reject(new Error("Failed to load image"));
      img.src = e.target?.result as string;
    };
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

type InputMode = "url" | "manual" | "raw";

export default function PredictPage() {
  const [mode, setMode] = useState<InputMode>("url");
  const [url, setUrl] = useState("");
  const [modelType] = useState("auto"); // Auto-selects best model based on data
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PredictFromUrlResponse | null>(null);
  const [rawResult, setRawResult] = useState<RawDataPredictResponse | null>(null);
  const [repredicting, setRepredicting] = useState(false);
  
  // Manual input fields (simple mode - no LLM)
  const [manualData, setManualData] = useState<ManualPredictRequest>({
    model_type: "auto",
    living_area_m2: 70,
    bedroom_count: 2,
    bathroom_count: 1,
    outdoor_area_m2: 0,
    is_new_construction: false,
    has_garage: false,
    location_district: "Varaždin",
  });
  
  // Image handling
  const [images, setImages] = useState<string[]>([]);
  const [compressing, setCompressing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const rawFileInputRef = useRef<HTMLInputElement>(null);
  
  // Raw data input (LLM mode)
  const [rawData, setRawData] = useState<RawDataPredictRequest>({
    model_type: "auto",
    zupanija: "Varaždinska",
    title: "",
    price: "",
    highlighted_attributes: {},
    basic_details: {},
    description: "",
  });
  const [rawImages, setRawImages] = useState<string[]>([]);
  const [highlightedAttrsText, setHighlightedAttrsText] = useState("");
  const [basicDetailsText, setBasicDetailsText] = useState("");

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    setCompressing(true);
    try {
      const newImages: string[] = [];
      for (let i = 0; i < Math.min(files.length, 20 - images.length); i++) {
        const compressed = await compressImage(files[i], 600, 0.6);
        newImages.push(compressed);
      }
      setImages([...images, ...newImages].slice(0, 20));
    } catch (err) {
      console.error("Image compression failed:", err);
    } finally {
      setCompressing(false);
    }
  };

  const removeImage = (index: number) => {
    setImages(images.filter((_, i) => i !== index));
  };

  // Raw image handling
  const handleRawImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    setCompressing(true);
    try {
      const newImages: string[] = [];
      for (let i = 0; i < Math.min(files.length, 20 - rawImages.length); i++) {
        const compressed = await compressImage(files[i], 600, 0.6);
        newImages.push(compressed);
      }
      setRawImages([...rawImages, ...newImages].slice(0, 20));
    } catch (err) {
      console.error("Image compression failed:", err);
    } finally {
      setCompressing(false);
    }
  };

  const removeRawImage = (index: number) => {
    setRawImages(rawImages.filter((_, i) => i !== index));
  };

  // Parse key:value text into object
  const parseKeyValueText = (text: string): Record<string, string> => {
    const result: Record<string, string> = {};
    const lines = text.split("\n");
    for (const line of lines) {
      const colonIndex = line.indexOf(":");
      if (colonIndex > 0) {
        const key = line.substring(0, colonIndex).trim();
        const value = line.substring(colonIndex + 1).trim();
        if (key && value) {
          result[key] = value;
        }
      }
    }
    return result;
  };

  const handlePredict = async () => {
    if (mode === "url") {
      if (!url.trim()) {
        setError("Please enter a URL");
        return;
      }
      if (!url.includes("njuskalo.hr")) {
        setError("URL must be from njuskalo.hr");
        return;
      }
    } else if (mode === "manual") {
      if (!manualData.living_area_m2 || manualData.living_area_m2 < 10) {
        setError("Please enter a valid living area (min 10m²)");
        return;
      }
    } else if (mode === "raw") {
      if (!rawData.description && !rawData.title && Object.keys(rawData.highlighted_attributes || {}).length === 0) {
        setError("Please enter at least a title, description, or some attributes");
        return;
      }
    }

    try {
      setLoading(true);
      setError(null);
      setResult(null);
      setRawResult(null);

      if (mode === "url") {
        const data = await api.predictFromUrl(url, modelType);
        setResult(data);
      } else if (mode === "manual") {
        const data = await api.predictManual({
          ...manualData,
          model_type: modelType,
          images: images.length > 0 ? images : undefined,
        });
        setResult(data);
      } else if (mode === "raw") {
        // Parse the text fields into objects
        const highlighted = parseKeyValueText(highlightedAttrsText);
        const basic = parseKeyValueText(basicDetailsText);
        
        const data = await api.predictFromRawData({
          ...rawData,
          model_type: modelType,
          highlighted_attributes: Object.keys(highlighted).length > 0 ? highlighted : undefined,
          basic_details: Object.keys(basic).length > 0 ? basic : undefined,
          images: rawImages.length > 0 ? rawImages : undefined,
        });
        setRawResult(data);
      }
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to predict price");
    } finally {
      setLoading(false);
    }
  };

  // Re-predict with different model (no LLM re-classification)
  const handleRepredict = async (newModelType: string) => {
    // Get features from current result
    const currentResult = result || rawResult;
    if (!currentResult) return;
    
    setRepredicting(true);
    try {
      const repredictResult = await api.repredict(
        newModelType,
        currentResult.features_used,
        currentResult.actual_price ?? undefined,
        currentResult.title
      );
      
      // Update the result with new prediction (preserve other data)
      if (result) {
        setResult({
          ...result,
          predicted_price: repredictResult.predicted_price,
          model_used: repredictResult.model_used,
          difference: repredictResult.difference,
          difference_pct: repredictResult.difference_pct,
          deal_score: repredictResult.deal_score,
          confidence_note: repredictResult.confidence_note,
        });
      } else if (rawResult) {
        setRawResult({
          ...rawResult,
          predicted_price: repredictResult.predicted_price,
          model_used: repredictResult.model_used,
          difference: repredictResult.difference,
          difference_pct: repredictResult.difference_pct,
          deal_score: repredictResult.deal_score,
          confidence_note: repredictResult.confidence_note,
        });
      }
      
      // Model type is tracked in result.model_used
    } catch (err) {
      console.error("Re-predict failed:", err);
      setError(err instanceof Error ? err.message : "Failed to re-predict");
    } finally {
      setRepredicting(false);
    }
  };

  const scoreStyle = result?.deal_score ? DEAL_SCORE_STYLES[result.deal_score] : null;
  const isGoodDeal = result?.deal_score === "great_deal" || result?.deal_score === "good_deal";
  const isBadDeal = result?.deal_score === "overpriced" || result?.deal_score === "very_overpriced";

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white flex items-center justify-center gap-3">
          <span className="text-4xl">🔮</span>
          Price Predictor
        </h1>
        <p className="text-slate-400 mt-2 max-w-lg mx-auto">
          Predict fair market value using URL or manual input
        </p>
      </div>

      {/* Mode Selector */}
      <div className="flex justify-center gap-2 flex-wrap">
        <button
          onClick={() => setMode("url")}
          className={`px-5 py-2.5 rounded-xl font-medium transition-all flex items-center gap-2 ${
            mode === "url"
              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
              : "bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:text-white"
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          From URL
        </button>
        <button
          onClick={() => setMode("manual")}
          className={`px-5 py-2.5 rounded-xl font-medium transition-all flex items-center gap-2 ${
            mode === "manual"
              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
              : "bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:text-white"
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Quick Input
        </button>
        <button
          onClick={() => setMode("raw")}
          className={`px-5 py-2.5 rounded-xl font-medium transition-all flex items-center gap-2 ${
            mode === "raw"
              ? "bg-violet-500/20 text-violet-400 border border-violet-500/30"
              : "bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:text-white"
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Raw Data + LLM
        </button>
      </div>

      {/* Input Card */}
      <div className="glass rounded-2xl p-6">
        <div className="space-y-4">
          
          {/* URL Mode */}
          {mode === "url" && (
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Listing URL
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </div>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://www.njuskalo.hr/nekretnine/..."
                    className="w-full pl-10 pr-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl text-white placeholder:text-slate-500 focus:border-emerald-500/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 transition-all"
                    onKeyDown={(e) => e.key === "Enter" && handlePredict()}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Manual Mode */}
          {mode === "manual" && (
            <div className="space-y-6">
              {/* Title & Price */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Title (optional)</label>
                  <input
                    type="text"
                    value={manualData.title || ""}
                    onChange={(e) => setManualData({ ...manualData, title: e.target.value })}
                    placeholder="e.g., Modern 2-bed apartment"
                    className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Listed Price € (optional)</label>
                  <input
                    type="number"
                    value={manualData.actual_price || ""}
                    onChange={(e) => setManualData({ ...manualData, actual_price: parseFloat(e.target.value) || undefined })}
                    placeholder="e.g., 150000"
                    className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                  />
                </div>
              </div>

              {/* Property Details */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                  <span>🏠</span> Property Details
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Living Area m² *</label>
                    <input
                      type="number"
                      value={manualData.living_area_m2}
                      onChange={(e) => setManualData({ ...manualData, living_area_m2: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                      min={10}
                      max={1000}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Bedrooms</label>
                    <input
                      type="number"
                      value={manualData.bedroom_count}
                      onChange={(e) => setManualData({ ...manualData, bedroom_count: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                      min={0}
                      max={20}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Bathrooms</label>
                    <input
                      type="number"
                      value={manualData.bathroom_count}
                      onChange={(e) => setManualData({ ...manualData, bathroom_count: parseInt(e.target.value) || 0 })}
                      className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                      min={0}
                      max={10}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Outdoor m²</label>
                    <input
                      type="number"
                      value={manualData.outdoor_area_m2 || ""}
                      onChange={(e) => setManualData({ ...manualData, outdoor_area_m2: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                      min={0}
                    />
                  </div>
                </div>
              </div>

              {/* Location & Building */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                  <span>📍</span> Location & Building
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">District</label>
                    <select
                      value={manualData.location_district || "Varaždin"}
                      onChange={(e) => setManualData({ ...manualData, location_district: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                    >
                      {DISTRICTS.map((d) => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Year Built</label>
                    <input
                      type="number"
                      value={manualData.year_built || ""}
                      onChange={(e) => setManualData({ ...manualData, year_built: parseInt(e.target.value) || undefined })}
                      placeholder="e.g., 2020"
                      className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none"
                      min={1800}
                      max={2030}
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={manualData.is_new_construction}
                        onChange={(e) => setManualData({ ...manualData, is_new_construction: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/20"
                      />
                      <span className="text-sm text-slate-300">New Build</span>
                    </label>
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={manualData.has_garage}
                        onChange={(e) => setManualData({ ...manualData, has_garage: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500/20"
                      />
                      <span className="text-sm text-slate-300">Has Garage</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Description */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                  <span>📝</span> Description (optional)
                </h3>
                <textarea
                  value={manualData.description || ""}
                  onChange={(e) => setManualData({ ...manualData, description: e.target.value })}
                  placeholder="Paste listing description for AI analysis..."
                  className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-emerald-500/50 focus:outline-none min-h-[100px] resize-y"
                />
              </div>

              {/* Images */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                  <span>📷</span> Images (optional, max 20)
                  <span className="text-xs text-slate-500">Auto-compressed to save tokens</span>
                  {images.length > 0 && <span className="text-xs text-emerald-400">{images.length}/20</span>}
                </h3>
                
                {/* Image Grid */}
                <div className="flex flex-wrap gap-3 mb-3">
                  {images.map((img, index) => (
                    <div key={index} className="relative w-24 h-24 rounded-lg overflow-hidden group">
                      <img src={img} alt={`Upload ${index + 1}`} className="w-full h-full object-cover" />
                      <button
                        onClick={() => removeImage(index)}
                        className="absolute top-1 right-1 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                  
                  {images.length < 20 && (
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={compressing}
                      className="w-24 h-24 rounded-lg border-2 border-dashed border-slate-600 hover:border-emerald-500/50 flex flex-col items-center justify-center gap-1 text-slate-500 hover:text-emerald-400 transition-all"
                    >
                      {compressing ? (
                        <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      ) : (
                        <>
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                          </svg>
                          <span className="text-xs">Add</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
                
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </div>
            </div>
          )}

          {/* Raw Data Mode (LLM Classification) */}
          {mode === "raw" && (
            <div className="space-y-6">
              <div className="bg-violet-500/10 border border-violet-500/30 rounded-xl p-4 text-violet-300 text-sm">
                <p className="font-medium mb-1">🤖 LLM Classification Mode</p>
                <p className="text-violet-400/80">
                  Paste raw listing data from HTML/JSON. The AI will analyze text and images to extract 
                  standardized property details, detect rooms, and estimate condition.
                </p>
              </div>

              {/* Title & Price */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Title</label>
                  <input
                    type="text"
                    value={rawData.title || ""}
                    onChange={(e) => setRawData({ ...rawData, title: e.target.value })}
                    placeholder="Stan u centru Varaždina, 75m2..."
                    className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-violet-500/50 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Price (as shown)</label>
                  <input
                    type="text"
                    value={rawData.price || ""}
                    onChange={(e) => setRawData({ ...rawData, price: e.target.value })}
                    placeholder="150.000 €"
                    className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-violet-500/50 focus:outline-none"
                  />
                </div>
              </div>

              {/* Highlighted Attributes */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                  <span>📊</span> Highlighted Attributes
                  <span className="text-xs text-slate-500">(key: value, one per line)</span>
                </h3>
                <textarea
                  value={highlightedAttrsText}
                  onChange={(e) => setHighlightedAttrsText(e.target.value)}
                  placeholder={`Stambena površina: 75 m²\nBroj soba: 3\nKat: 2. kat`}
                  className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-violet-500/50 focus:outline-none min-h-[80px] resize-y font-mono"
                />
              </div>

              {/* Basic Details */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                  <span>📋</span> Basic Details
                  <span className="text-xs text-slate-500">(key: value, one per line)</span>
                </h3>
                <textarea
                  value={basicDetailsText}
                  onChange={(e) => setBasicDetailsText(e.target.value)}
                  placeholder={`Lokacija: Varaždinska žup., Varaždin, Centar\nGodina izgradnje: 2020\nStanje nekretnine: Novogradnja\nGrijanje: Podno grijanje na plin\nParking: Garaža`}
                  className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-violet-500/50 focus:outline-none min-h-[120px] resize-y font-mono"
                />
              </div>

              {/* Description */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                  <span>📝</span> Full Description
                </h3>
                <textarea
                  value={rawData.description || ""}
                  onChange={(e) => setRawData({ ...rawData, description: e.target.value })}
                  placeholder="Paste the full listing description here. The AI will extract room counts, features, condition details..."
                  className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-violet-500/50 focus:outline-none min-h-[150px] resize-y"
                />
              </div>

              {/* Images for LLM Analysis */}
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                  <span>📷</span> Images for AI Analysis (max 20)
                  <span className="text-xs text-slate-500">AI will detect rooms & condition</span>
                  {rawImages.length > 0 && <span className="text-xs text-violet-400">{rawImages.length}/20</span>}
                </h3>
                
                <div className="flex flex-wrap gap-3 mb-3">
                  {rawImages.map((img, index) => (
                    <div key={index} className="relative w-24 h-24 rounded-lg overflow-hidden group">
                      <img src={img} alt={`Upload ${index + 1}`} className="w-full h-full object-cover" />
                      <button
                        onClick={() => removeRawImage(index)}
                        className="absolute top-1 right-1 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                  
                  {rawImages.length < 20 && (
                    <button
                      onClick={() => rawFileInputRef.current?.click()}
                      disabled={compressing}
                      className="w-24 h-24 rounded-lg border-2 border-dashed border-violet-600/50 hover:border-violet-500 flex flex-col items-center justify-center gap-1 text-slate-500 hover:text-violet-400 transition-all"
                    >
                      {compressing ? (
                        <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      ) : (
                        <>
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                          </svg>
                          <span className="text-xs">Add</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
                
                <input
                  ref={rawFileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleRawImageUpload}
                  className="hidden"
                />
              </div>

              {/* Županija selector */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Županija (for location context)</label>
                <select
                  value={rawData.zupanija || "Varaždinska"}
                  onChange={(e) => setRawData({ ...rawData, zupanija: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-violet-500/50 focus:outline-none"
                >
                  <option value="Varaždinska">Varaždinska županija</option>
                </select>
              </div>
            </div>
          )}

          {/* Predict Button */}
          <button
            onClick={handlePredict}
            disabled={
              loading || 
              (mode === "url" && !url.trim()) || 
              (mode === "manual" && !manualData.living_area_m2) ||
              (mode === "raw" && !rawData.description && !rawData.title && !highlightedAttrsText && !basicDetailsText)
            }
            className={`w-full py-4 ${mode === "raw" ? "bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 shadow-violet-500/20" : "bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 shadow-emerald-500/20"} text-white font-bold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-lg shadow-lg`}
          >
            {loading ? (
              <>
                <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {mode === "raw" ? "🤖 AI Classifying..." : mode === "url" ? "Analyzing Listing..." : "Predicting Price..."}
              </>
            ) : (
              <>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                {mode === "raw" ? "🤖 Analyze & Predict" : "Predict Price"}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 text-red-400 flex items-center gap-3">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Main Result Card */}
          <div className="glass rounded-2xl overflow-hidden">
            {/* Header with deal score */}
            {scoreStyle && (
              <div className={`bg-gradient-to-r ${scoreStyle.gradient} p-4 flex items-center justify-between`}>
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{scoreStyle.emoji}</span>
                  <div>
                    <div className="text-white font-bold text-xl">{scoreStyle.label}</div>
                    {result.difference_pct !== null && (
                      <div className="text-white/80 text-sm">
                        {result.difference_pct > 0 ? "+" : ""}{result.difference_pct.toFixed(1)}% from fair value
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-white/60 text-xs uppercase tracking-wider">Model</div>
                  <div className="text-white font-semibold">{result.model_used}</div>
                </div>
              </div>
            )}

            <div className="p-6">
              {/* Title */}
              <h2 className="text-lg font-semibold text-white mb-4 line-clamp-2">
                {result.title}
              </h2>

              {/* Model Switcher - Try different models */}
              <div className="mb-6 p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                    <span>🔄</span> Try Different Model
                    <span className="text-xs text-slate-500">(keeps same property data)</span>
                  </h3>
                  {repredicting && (
                    <div className="flex items-center gap-2 text-cyan-400 text-sm">
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Recalculating...
                    </div>
                  )}
                </div>
                <div className="flex gap-2 flex-wrap">
                  {[
                    { value: "ridge", label: "Ridge" },
                    { value: "random_forest", label: "Random Forest" },
                    { value: "xgboost", label: "XGBoost" },
                    { value: "mlp", label: "Neural Network" },
                    { value: "gradient_boosting", label: "Gradient Boost" },
                    { value: "knn", label: "KNN" },
                  ].map((model) => (
                    <button
                      key={model.value}
                      onClick={() => handleRepredict(model.value)}
                      disabled={repredicting || result.model_used === model.value}
                      className={`px-3 py-1.5 text-sm rounded-lg transition-all disabled:opacity-50 ${
                        result.model_used === model.value
                          ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 cursor-default"
                          : "bg-slate-700/50 text-slate-400 border border-slate-600/50 hover:text-white hover:border-slate-500"
                      }`}
                    >
                      {model.label}
                      {result.model_used === model.value && " ✓"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Price Comparison */}
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                {/* Predicted Price */}
                <div className="bg-slate-800/50 rounded-xl p-4 text-center border-2 border-cyan-500/30">
                  <div className="text-xs text-cyan-400 uppercase tracking-wider mb-1">AI Predicted</div>
                  <div className="text-3xl font-bold text-cyan-400">
                    €{result.predicted_price.toLocaleString()}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">Fair market value</div>
                </div>

                {/* Actual Price */}
                {result.actual_price !== null && (
                  <div className={`rounded-xl p-4 text-center border-2 ${
                    isGoodDeal ? "bg-emerald-500/10 border-emerald-500/30" :
                    isBadDeal ? "bg-red-500/10 border-red-500/30" :
                    "bg-slate-800/50 border-slate-700/50"
                  }`}>
                    <div className={`text-xs uppercase tracking-wider mb-1 ${
                      isGoodDeal ? "text-emerald-400" :
                      isBadDeal ? "text-red-400" :
                      "text-slate-400"
                    }`}>Listed Price</div>
                    <div className={`text-3xl font-bold ${
                      isGoodDeal ? "text-emerald-400" :
                      isBadDeal ? "text-red-400" :
                      "text-white"
                    }`}>
                      €{result.actual_price.toLocaleString()}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">Seller asking</div>
                  </div>
                )}

                {/* Difference */}
                {result.difference !== null && (
                  <div className={`rounded-xl p-4 text-center ${
                    isGoodDeal ? "bg-emerald-500/10" :
                    isBadDeal ? "bg-red-500/10" :
                    "bg-slate-800/50"
                  }`}>
                    <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">
                      {isGoodDeal ? "You Save" : isBadDeal ? "Overpaying" : "Difference"}
                    </div>
                    <div className={`text-3xl font-bold ${
                      isGoodDeal ? "text-emerald-400" :
                      isBadDeal ? "text-red-400" :
                      "text-white"
                    }`}>
                      €{Math.abs(result.difference).toLocaleString()}
                    </div>
                    <div className={`text-sm mt-1 ${
                      isGoodDeal ? "text-emerald-400/80" :
                      isBadDeal ? "text-red-400/80" :
                      "text-slate-500"
                    }`}>
                      {result.difference_pct !== null && (
                        <>{Math.abs(result.difference_pct).toFixed(1)}% {isGoodDeal ? "below" : isBadDeal ? "above" : "of"} fair value</>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Features Used */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-slate-400 mb-3">Features Analyzed</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-slate-800/30 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Living Area</div>
                    <div className="text-white font-semibold">
                      {result.features_used.living_area_m2 > 0 
                        ? `${result.features_used.living_area_m2} m²`
                        : "—"
                      }
                    </div>
                  </div>
                  <div className="bg-slate-800/30 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Bedrooms</div>
                    <div className="text-white font-semibold">
                      {result.features_used.bedroom_count || "—"}
                    </div>
                  </div>
                  <div className="bg-slate-800/30 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Bathrooms</div>
                    <div className="text-white font-semibold">
                      {result.features_used.bathroom_count || "—"}
                    </div>
                  </div>
                  <div className="bg-slate-800/30 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Location</div>
                    <div className="text-white font-semibold truncate" title={result.features_used.location}>
                      {result.features_used.location || "—"}
                    </div>
                  </div>
                  {result.features_used.outdoor_area_m2 !== undefined && result.features_used.outdoor_area_m2 > 0 && (
                    <div className="bg-slate-800/30 rounded-lg p-3">
                      <div className="text-xs text-slate-500">Outdoor Area</div>
                      <div className="text-white font-semibold">{result.features_used.outdoor_area_m2} m²</div>
                    </div>
                  )}
                  {result.features_used.renovation_level !== undefined && result.features_used.renovation_level > 0 && (
                    <div className="bg-slate-800/30 rounded-lg p-3">
                      <div className="text-xs text-slate-500">Renovation</div>
                      <div className="text-white font-semibold">{result.features_used.renovation_level}/10</div>
                    </div>
                  )}
                  {result.features_used.distance_from_center !== undefined && result.features_used.distance_from_center > 0 && (
                    <div className="bg-slate-800/30 rounded-lg p-3">
                      <div className="text-xs text-slate-500">Distance</div>
                      <div className="text-white font-semibold">{result.features_used.distance_from_center.toFixed(1)} km</div>
                    </div>
                  )}
                  <div className="bg-slate-800/30 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Type</div>
                    <div className="text-white font-semibold">
                      {result.features_used.is_new_construction ? "New Build" : "Resale"}
                    </div>
                  </div>
                  {result.features_used.has_garage && (
                    <div className="bg-slate-800/30 rounded-lg p-3">
                      <div className="text-xs text-slate-500">Parking</div>
                      <div className="text-white font-semibold">Has Garage ✓</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Confidence Note */}
              <div className={`rounded-lg p-3 flex items-center gap-2 ${
                result.confidence_note === "Good confidence" 
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-amber-500/10 text-amber-400"
              }`}>
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm">{result.confidence_note}</span>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 mt-6">
                {result.url !== "manual-input" && (
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`flex-1 py-3 rounded-xl font-semibold text-center transition-all flex items-center justify-center gap-2 ${
                      isGoodDeal 
                        ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                        : "bg-slate-700 hover:bg-slate-600 text-white"
                    }`}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    {isGoodDeal ? "Go to Deal!" : "View Listing"}
                  </a>
                )}
                <button
                  onClick={() => {
                    setResult(null);
                    if (mode === "url") setUrl("");
                  }}
                  className={`${result.url === "manual-input" ? "flex-1" : ""} px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-semibold transition-all`}
                >
                  New Prediction
                </button>
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <p className="text-xs text-slate-500 text-center">
            💡 Predictions are based on {result.model_used} model trained on local market data. 
            Always conduct your own due diligence before making purchasing decisions.
          </p>
        </div>
      )}

      {/* Raw Data Results (with LLM classification) */}
      {rawResult && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Main Result Card */}
          <div className="glass rounded-2xl overflow-hidden">
            {/* Header with deal score */}
            {rawResult.deal_score && DEAL_SCORE_STYLES[rawResult.deal_score] && (
              <div className={`bg-gradient-to-r ${DEAL_SCORE_STYLES[rawResult.deal_score].gradient} p-4 flex items-center justify-between`}>
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{DEAL_SCORE_STYLES[rawResult.deal_score].emoji}</span>
                  <div>
                    <div className="text-white font-bold text-xl">{DEAL_SCORE_STYLES[rawResult.deal_score].label}</div>
                    {rawResult.difference_pct !== null && (
                      <div className="text-white/80 text-sm">
                        {rawResult.difference_pct > 0 ? "+" : ""}{rawResult.difference_pct.toFixed(1)}% from fair value
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="bg-violet-500/30 px-3 py-1 rounded-full text-violet-200 text-sm">
                    🤖 AI Classified
                  </div>
                  <div className="text-right">
                    <div className="text-white/60 text-xs uppercase tracking-wider">Model</div>
                    <div className="text-white font-semibold">{rawResult.model_used}</div>
                  </div>
                </div>
              </div>
            )}

            <div className="p-6">
              {/* Title */}
              <h2 className="text-lg font-semibold text-white mb-4 line-clamp-2">
                {rawResult.title}
              </h2>

              {/* Model Switcher - Try different models */}
              <div className="mb-6 p-4 bg-slate-800/50 rounded-xl border border-violet-500/20">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                    <span>🔄</span> Try Different Model
                    <span className="text-xs text-slate-500">(keeps AI-extracted data)</span>
                  </h3>
                  {repredicting && (
                    <div className="flex items-center gap-2 text-violet-400 text-sm">
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Recalculating...
                    </div>
                  )}
                </div>
                <div className="flex gap-2 flex-wrap">
                  {[
                    { value: "ridge", label: "Ridge" },
                    { value: "random_forest", label: "Random Forest" },
                    { value: "xgboost", label: "XGBoost" },
                    { value: "mlp", label: "Neural Network" },
                    { value: "gradient_boosting", label: "Gradient Boost" },
                    { value: "knn", label: "KNN" },
                  ].map((model) => (
                    <button
                      key={model.value}
                      onClick={() => handleRepredict(model.value)}
                      disabled={repredicting || rawResult.model_used === model.value}
                      className={`px-3 py-1.5 text-sm rounded-lg transition-all disabled:opacity-50 ${
                        rawResult.model_used === model.value
                          ? "bg-violet-500/20 text-violet-400 border border-violet-500/30 cursor-default"
                          : "bg-slate-700/50 text-slate-400 border border-slate-600/50 hover:text-white hover:border-slate-500"
                      }`}
                    >
                      {model.label}
                      {rawResult.model_used === model.value && " ✓"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Price Comparison */}
              <div className="grid md:grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-800/50 rounded-xl p-4 text-center border-2 border-violet-500/30">
                  <div className="text-xs text-violet-400 uppercase tracking-wider mb-1">AI Predicted</div>
                  <div className="text-3xl font-bold text-violet-400">
                    €{rawResult.predicted_price.toLocaleString()}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">Fair market value</div>
                </div>

                {rawResult.actual_price !== null && (
                  <div className={`rounded-xl p-4 text-center border-2 ${
                    rawResult.deal_score?.includes("deal") ? "bg-emerald-500/10 border-emerald-500/30" :
                    rawResult.deal_score?.includes("overpriced") ? "bg-red-500/10 border-red-500/30" :
                    "bg-slate-800/50 border-slate-700/50"
                  }`}>
                    <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Listed Price</div>
                    <div className="text-3xl font-bold text-white">
                      €{rawResult.actual_price.toLocaleString()}
                    </div>
                  </div>
                )}

                {rawResult.difference !== null && (
                  <div className={`rounded-xl p-4 text-center ${
                    rawResult.deal_score?.includes("deal") ? "bg-emerald-500/10" :
                    rawResult.deal_score?.includes("overpriced") ? "bg-red-500/10" :
                    "bg-slate-800/50"
                  }`}>
                    <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Difference</div>
                    <div className={`text-3xl font-bold ${
                      rawResult.deal_score?.includes("deal") ? "text-emerald-400" :
                      rawResult.deal_score?.includes("overpriced") ? "text-red-400" :
                      "text-white"
                    }`}>
                      €{Math.abs(rawResult.difference).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              {/* LLM Classified Data */}
              <div className="mb-6 p-4 bg-violet-500/10 rounded-xl border border-violet-500/20">
                <h3 className="text-sm font-medium text-violet-400 mb-3 flex items-center gap-2">
                  <span>🤖</span> AI Extracted Data
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div>
                    <span className="text-slate-500">Location: </span>
                    <span className="text-white">{rawResult.classified_data.location.district || rawResult.classified_data.location.city || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Living Area: </span>
                    <span className="text-white">{rawResult.classified_data.dimensions.living_area_m2 || "—"} m²</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Bedrooms: </span>
                    <span className="text-white">{rawResult.classified_data.building_specs.bedroom_count || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Bathrooms: </span>
                    <span className="text-white">{rawResult.classified_data.building_specs.bathroom_count || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Year Built: </span>
                    <span className="text-white">{rawResult.classified_data.building_specs.year_built || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Type: </span>
                    <span className="text-white">{rawResult.classified_data.building_specs.is_new_construction ? "New Build" : "Resale"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Parking: </span>
                    <span className="text-white">{rawResult.classified_data.building_specs.parking_type || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Phase: </span>
                    <span className="text-white">{rawResult.classified_data.condition.construction_phase || "—"}</span>
                  </div>
                </div>
                {rawResult.classified_data.dimensions.area_conflict && (
                  <div className="mt-3 text-amber-400 text-xs flex items-center gap-1">
                    ⚠️ Area conflict detected between metadata and description
                  </div>
                )}
              </div>

              {/* Rooms Detected */}
              {rawResult.rooms && rawResult.rooms.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                    <span>🏠</span> Rooms Detected ({rawResult.rooms.length})
                  </h3>
                  <div className="grid md:grid-cols-2 gap-3">
                    {rawResult.rooms.map((room, idx) => (
                      <div key={idx} className="bg-slate-800/50 rounded-lg p-3 flex gap-3">
                        {room.image_url && (
                          <img 
                            src={room.image_url} 
                            alt={room.room_type || "Room"} 
                            className="w-20 h-20 object-cover rounded-lg flex-shrink-0"
                          />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-white capitalize">
                              {room.room_type?.replace(/_/g, " ") || "Unknown"}
                            </span>
                            {room.from_description && (
                              <span className="text-[10px] px-1.5 py-0.5 bg-slate-700 text-slate-400 rounded">
                                From text
                              </span>
                            )}
                          </div>
                          {room.condition && (
                            <div className={`text-xs mb-1 ${
                              room.condition === "EXCELLENT" || room.condition === "RENOVATED" ? "text-emerald-400" :
                              room.condition === "GOOD" ? "text-green-400" :
                              room.condition === "NEEDS_RENOVATION" || room.condition === "POOR" ? "text-red-400" :
                              "text-slate-400"
                            }`}>
                              {room.condition.replace(/_/g, " ")}
                            </div>
                          )}
                          {room.features && room.features.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {room.features.slice(0, 3).map((f, i) => (
                                <span key={i} className="text-[10px] px-1.5 py-0.5 bg-violet-500/20 text-violet-300 rounded">
                                  {f.replace(/_/g, " ")}
                                </span>
                              ))}
                            </div>
                          )}
                          {room.condition_reasoning && (
                            <p className="text-xs text-slate-500 mt-1 line-clamp-2" title={room.condition_reasoning}>
                              💭 {room.condition_reasoning}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Confidence Note */}
              <div className={`rounded-lg p-3 flex items-center gap-2 ${
                rawResult.confidence_note === "Good confidence" 
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-amber-500/10 text-amber-400"
              }`}>
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm">{rawResult.confidence_note}</span>
              </div>

              {/* New Prediction Button */}
              <button
                onClick={() => {
                  setRawResult(null);
                  setRawData({
                    model_type: "auto",
                    zupanija: "Varaždinska",
                    title: "",
                    price: "",
                    highlighted_attributes: {},
                    basic_details: {},
                    description: "",
                  });
                  setRawImages([]);
                  setHighlightedAttrsText("");
                  setBasicDetailsText("");
                }}
                className="w-full mt-6 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-semibold transition-all"
              >
                New Analysis
              </button>
            </div>
          </div>

          <p className="text-xs text-slate-500 text-center">
            💡 AI classification used {rawResult.model_used} model. Rooms and conditions detected from images and description.
          </p>
        </div>
      )}

      {/* Empty State */}
      {!result && !rawResult && !loading && !error && (
        <div className="glass rounded-2xl p-12 text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-10 h-10 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Ready to Analyze</h3>
          <p className="text-slate-400 max-w-md mx-auto mb-6">
            {mode === "url" 
              ? "Paste a njuskalo.hr listing URL above and our AI will analyze the property to predict its fair market value."
              : mode === "manual"
              ? "Enter property details manually to get an instant price prediction based on similar properties in the area."
              : "Paste raw listing data (title, description, attributes) and images. The AI will classify the property and predict its value."
            }
          </p>
          <div className="flex flex-wrap justify-center gap-2 text-xs">
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full">🏠 Apartments</span>
            <span className="px-3 py-1 bg-cyan-500/10 text-cyan-400 rounded-full">🏡 Houses</span>
            <span className="px-3 py-1 bg-violet-500/10 text-violet-400 rounded-full">🏢 Commercial</span>
          </div>
        </div>
      )}
    </div>
  );
}
