"""
Test script to demonstrate LLM classifier with location context.
This shows exactly what goes INTO the LLM and what comes OUT.

Usage: python test_classifier.py
"""

import asyncio
import json
from datetime import datetime

# Add parent to path
import sys
sys.path.insert(0, '.')

from app.locations_config.locations import get_location_context
from app.services.classifier import ListingClassifier, CLASSIFICATION_PROMPT


def test_location_context():
    """Test and display the location context for Varaždinska."""
    print("=" * 80)
    print("LOCATION CONTEXT FOR VARAŽDINSKA ŽUPANIJA")
    print("=" * 80)
    
    context = get_location_context("Varaždinska")
    
    print(f"\nŽupanija: {context['zupanija']}")
    print(f"City (for 'city' field): {context['city']}")
    print(f"\nDistricts (separate towns - use as neighborhood):")
    for d in context['districts']:
        print(f"  - {d}")
    
    return context


def build_location_context_string(location_context: dict) -> str:
    """Build the location context string that goes into the prompt."""
    if not location_context:
        return "No specific location context provided."
    
    zupanija = location_context.get("zupanija", "")
    city = location_context.get("city", "")
    districts = location_context.get("districts", [])
    
    return f"""
**For this listing, the županija is: {zupanija}**
**The main city (use for 'city' field): {city}**

DISTRICTS (use for 'district' field):
{', '.join(districts) if districts else 'None specified'}

If the location mentions "Centar" or is in the main city, set district to "{city}".
If you see "- Okolica" it means suburbs, extract the actual place name after it.
"""


def create_sample_listing_data():
    """Create sample data similar to what would be scraped from the URL."""
    # This mimics what would be extracted from:
    # https://www.njuskalo.hr/nekretnine/stan-50m2-dvije-spavace-sobe-marof-centar-oglas-48981262
    
    return {
        "title": "Stan 50m2 dvije spavaće sobe - Marof centar",
        "price": "89.000 €",
        "ad_id": "48981262",
        "highlighted_attributes": {
            "Stambena površina": "50 m²",
            "Broj soba": "3",
            "Kat": "2. kat"
        },
        "basic_details": {
            "Lokacija": "Varaždinska žup., Novi Marof, Centar",
            "Kategorija": "Stanovi / Prodaja stanova",
            "Tip nekretnine": "Stan u zgradi",
            "Godina izgradnje": "1985",
            "Stanje nekretnine": "Dobro održavano",
            "Grijanje": "Centralno grijanje",
            "Parking": "Javni parking"
        },
        "description": """Prodaje se stan u centru Novog Marofa, 50m2 stambene površine.

Stan se sastoji od:
- 2 spavaće sobe
- dnevni boravak s kuhinjom
- kupaonica s WC-om
- hodnik

Stan je dobro održavan, ima centralno grijanje i nalazi se na 2. katu zgrade iz 1985. godine.
U blizini su škola, vrtić, trgovine i autobusna stanica.

Cijena: 89.000 EUR
Kontakt: 099 123 4567""",
        "additional_info": {
            "Šifra oglasa": "48981262",
            "Datum objave": "15.11.2024."
        },
        "category_path": ["Nekretnine", "Stanovi", "Prodaja stanova", "Varaždinska žup."],
        "images": []  # No images for this test
    }


def build_full_prompt(raw_data: dict, location_context: dict) -> str:
    """Build the full prompt that would be sent to the LLM."""
    
    # Build location context string
    location_context_str = build_location_context_string(location_context)
    
    # Prepare data for LLM
    description = raw_data.get("description") or ""
    data_for_llm = {
        "title": raw_data.get("title"),
        "price": raw_data.get("price"),
        "ad_id": raw_data.get("ad_id"),
        "highlighted_attributes": raw_data.get("highlighted_attributes") or {},
        "basic_details": raw_data.get("basic_details") or {},
        "description": description[:3000],
        "additional_info": raw_data.get("additional_info") or {},
        "category_path": raw_data.get("category_path") or [],
    }
    
    listing_json = json.dumps(data_for_llm, ensure_ascii=False, indent=2)
    
    # Build the full prompt
    full_prompt = CLASSIFICATION_PROMPT.replace('{listing_json}', listing_json)
    full_prompt = full_prompt.replace('{location_context}', location_context_str)
    full_prompt = full_prompt.replace('{image_instruction}', '## NO IMAGES AVAILABLE - Skip rooms analysis')
    
    return full_prompt


async def test_classifier_with_real_llm(raw_data: dict, location_context: dict):
    """Actually call the LLM and get a response."""
    try:
        classifier = ListingClassifier()
        result = await classifier.classify(raw_data, location_context=location_context)
        return result
    except Exception as e:
        return f"Error calling LLM: {str(e)}"


def save_to_file(content: str, filename: str):
    """Save content to a file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ Saved to: {filename}")


async def main():
    print("\n" + "=" * 80)
    print("LLM CLASSIFIER TEST - VARAŽDINSKA ŽUPANIJA")
    print("=" * 80)
    
    # 1. Get location context
    location_context = test_location_context()
    
    # 2. Create sample listing data
    print("\n" + "=" * 80)
    print("SAMPLE LISTING DATA (simulating scraped data)")
    print("=" * 80)
    
    raw_data = create_sample_listing_data()
    print(json.dumps(raw_data, ensure_ascii=False, indent=2))
    
    # 3. Build the full prompt
    print("\n" + "=" * 80)
    print("FULL PROMPT SENT TO LLM")
    print("=" * 80)
    
    full_prompt = build_full_prompt(raw_data, location_context)
    print(full_prompt[:2000] + "\n... [truncated for display] ...")
    
    # 4. Save everything to files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save input
    input_content = f"""LLM CLASSIFIER TEST - INPUT
Generated: {datetime.now().isoformat()}
URL: https://www.njuskalo.hr/nekretnine/stan-50m2-dvije-spavace-sobe-marof-centar-oglas-48981262
Županija: Varaždinska

{'=' * 80}
LOCATION CONTEXT
{'=' * 80}
{json.dumps(location_context, ensure_ascii=False, indent=2)}

{'=' * 80}
RAW LISTING DATA
{'=' * 80}
{json.dumps(raw_data, ensure_ascii=False, indent=2)}

{'=' * 80}
FULL PROMPT TO LLM
{'=' * 80}
{full_prompt}
"""
    
    save_to_file(input_content, f"llm_input_{timestamp}.txt")
    
    # 5. Try to call the LLM (if API key is configured)
    print("\n" + "=" * 80)
    print("CALLING LLM...")
    print("=" * 80)
    
    result = await test_classifier_with_real_llm(raw_data, location_context)
    
    if isinstance(result, str):
        # Error occurred
        print(f"\n⚠️ {result}")
        output_content = f"Error: {result}"
    else:
        # Success - format the output
        print("\n✅ LLM Response received!")
        print("\nExtracted Location:")
        print(f"  City: {result.location.city}")
        print(f"  District: {result.location.district}")
        print(f"  Floor: {result.location.floor_level}")
        
        print("\nExtracted Data:")
        print(f"  Title: {result.basic_info.title}")
        print(f"  Price: €{result.basic_info.price_euros}")
        print(f"  Area: {result.dimensions.description_living_area_m2} m²")
        print(f"  Bedrooms: {result.building_specs.bedroom_count}")
        print(f"  Bathrooms: {result.building_specs.bathroom_count}")
        print(f"  Year Built: {result.building_specs.year_built}")
        
        output_content = f"""LLM CLASSIFIER TEST - OUTPUT
Generated: {datetime.now().isoformat()}

{'=' * 80}
EXTRACTED LOCATION (CRITICAL TEST)
{'=' * 80}
City: {result.location.city}
District: {result.location.district}
Floor Level: {result.location.floor_level}

EXPECTED:
- City should be "Varaždin" (the županija capital)
- District should be "Novi Marof" (the district where the listing is located)

{'=' * 80}
FULL CLASSIFIED OUTPUT
{'=' * 80}
{json.dumps(result.model_dump(), ensure_ascii=False, indent=2)}
"""
    
    save_to_file(output_content, f"llm_output_{timestamp}.txt")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"\nFiles created:")
    print(f"  - llm_input_{timestamp}.txt")
    print(f"  - llm_output_{timestamp}.txt")


if __name__ == "__main__":
    asyncio.run(main())

