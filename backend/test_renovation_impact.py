#!/usr/bin/env python3
"""
Test the impact of renovation level on price predictions.
Uses the same property with renovation levels 1-10.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_renovation_levels():
    from app.services.ml_router_helpers import get_filtered_listings, build_features_from_request
    from app.services.ml_service import MLService, ModelType
    
    # Get listings and train model
    print("Loading listings and training model...")
    listings = await get_filtered_listings()
    print(f"Loaded {len(listings)} listings")
    
    ml_service = MLService()
    result = ml_service.train_and_evaluate(
        listings=listings,
        model_type=ModelType.AUTO,
        test_size=0.1,
    )
    print(f"Model trained: {result.model_type} (R²={result.r2_score:.1%})")
    print()
    
    # Fixed property parameters (from user's input)
    base_property = {
        "living_area_m2": 75,
        "bedroom_count": 3,
        "bathroom_count": 1,
        "outdoor_area_m2": 3,
        "distance_from_center": 0.5,  # Varaždin city center
        "is_new_construction": False,
        "has_garage": False,
        "location_district": "Varaždin",
    }
    
    print("=" * 70)
    print("RENOVATION LEVEL IMPACT TEST")
    print("=" * 70)
    print(f"Property: {base_property['living_area_m2']}m², {base_property['bedroom_count']} beds, "
          f"{base_property['bathroom_count']} bath, {base_property['outdoor_area_m2']}m² outdoor")
    print(f"Location: {base_property['location_district']} (distance: {base_property['distance_from_center']}km)")
    print(f"Type: {'New Construction' if base_property['is_new_construction'] else 'Resale'}, "
          f"{'Has Garage' if base_property['has_garage'] else 'No Garage'}")
    print("=" * 70)
    print()
    
    results = []
    
    print(f"{'Renovation':<12} {'Predicted Price':>15} {'Δ from Level 5':>15} {'% Change':>12}")
    print("-" * 54)
    
    baseline_price = None
    
    for renovation_level in range(1, 11):
        features = build_features_from_request(
            living_area_m2=base_property["living_area_m2"],
            bedroom_count=base_property["bedroom_count"],
            bathroom_count=base_property["bathroom_count"],
            outdoor_area_m2=base_property["outdoor_area_m2"],
            renovation_level=renovation_level,
            distance_from_center=base_property["distance_from_center"],
            is_new_construction=base_property["is_new_construction"],
            has_garage=base_property["has_garage"],
            location_district=base_property["location_district"],
        )
        
        predicted_price = ml_service.predict(ModelType.AUTO, features)
        results.append((renovation_level, predicted_price))
        
        # Level 5 as baseline (average)
        if renovation_level == 5:
            baseline_price = predicted_price
        
        if baseline_price:
            diff = predicted_price - baseline_price
            pct = (diff / baseline_price) * 100 if baseline_price > 0 else 0
            diff_str = f"€{diff:+,.0f}"
            pct_str = f"{pct:+.1f}%"
        else:
            diff_str = "—"
            pct_str = "—"
        
        print(f"Level {renovation_level:<5} €{predicted_price:>13,.0f} {diff_str:>15} {pct_str:>12}")
    
    print("-" * 54)
    print()
    
    # Calculate statistics
    prices = [r[1] for r in results]
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price
    avg_change_per_level = price_range / 9  # 9 steps from 1 to 10
    
    print("📊 ANALYSIS")
    print("=" * 54)
    print(f"Lowest price (Level 1):   €{min_price:,.0f}")
    print(f"Highest price (Level 10): €{max_price:,.0f}")
    print(f"Price range:              €{price_range:,.0f}")
    print(f"Avg change per level:     €{avg_change_per_level:,.0f}")
    print(f"Total impact:             {((max_price - min_price) / min_price) * 100:.1f}%")
    print()
    
    # Impact interpretation
    print("💡 INSIGHTS")
    print("=" * 54)
    
    if price_range < 5000:
        print("• Renovation level has MINIMAL impact on this property type")
        print("• Other factors (area, location, bedrooms) dominate pricing")
    elif price_range < 15000:
        print("• Renovation level has MODERATE impact on price")
        print(f"• Each renovation point adds ~€{avg_change_per_level:,.0f} to value")
    else:
        print("• Renovation level has SIGNIFICANT impact on price")
        print(f"• Each renovation point adds ~€{avg_change_per_level:,.0f} to value")
        print("• Investing in renovation could substantially increase value")
    
    print()
    print(f"• Level 1→5 (poor→average): €{results[4][1] - results[0][1]:+,.0f}")
    print(f"• Level 5→10 (average→excellent): €{results[9][1] - results[4][1]:+,.0f}")
    
    # Check for diminishing returns
    first_half = results[4][1] - results[0][1]  # 1-5
    second_half = results[9][1] - results[4][1]  # 5-10
    
    print()
    if abs(first_half) > abs(second_half) * 1.2:
        print("⚠️ Diminishing returns: Upgrading from poor to average condition")
        print("   yields MORE value than average to excellent")
    elif abs(second_half) > abs(first_half) * 1.2:
        print("📈 Premium effect: Higher renovation levels yield")
        print("   GREATER returns (luxury market effect)")
    else:
        print("📊 Linear relationship: Each renovation level improvement")
        print("   adds roughly the same value")

if __name__ == "__main__":
    asyncio.run(test_renovation_levels())

