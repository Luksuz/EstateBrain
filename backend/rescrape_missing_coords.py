"""
Re-scrape listings that are missing latitude/longitude coordinates.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def main():
    from app.services.supabase import SupabaseService
    from app.services.firecrawl import FirecrawlService
    from app.services.parser import ListingParser
    from app.services.crozilla_parser import CrozillaListingParser
    
    print("=" * 80)
    print("🔄 RE-SCRAPING LISTINGS WITH MISSING COORDINATES")
    print("=" * 80)
    
    supabase = SupabaseService()
    
    # Find listings missing coordinates
    print("\n📊 Checking database for missing coordinates...")
    
    response = supabase.client.table('listings_v2')\
        .select('id, url, source, title, location_district')\
        .or_('latitude.is.null,longitude.is.null')\
        .execute()
    
    listings = response.data
    
    if not listings:
        print("✅ All listings have coordinates!")
        return
    
    print(f"Found {len(listings)} listings missing coordinates")
    
    # Group by source
    by_source = {}
    for listing in listings:
        source = listing.get('source', 'njuskalo')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(listing)
    
    print("\nBreakdown by source:")
    for source, items in by_source.items():
        print(f"  - {source}: {len(items)} listings")
    
    # Ask for confirmation
    print(f"\n⚠️  This will re-scrape {len(listings)} listings.")
    print("⚠️  This may consume Firecrawl credits.")
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Initialize services
    firecrawl = FirecrawlService()
    njuskalo_parser = ListingParser()
    crozilla_parser = CrozillaListingParser()
    
    # Track results
    success_count = 0
    failed_count = 0
    skipped_count = 0
    failed_urls = []
    
    print(f"\n🚀 Starting re-scrape...")
    print("=" * 80)
    
    for i, listing in enumerate(listings, 1):
        url = listing.get('url')
        listing_id = listing['id']
        source = listing.get('source', 'njuskalo')
        title = listing.get('title', 'Unknown')[:50]
        
        print(f"\n[{i}/{len(listings)}] Processing: {title}...")
        print(f"   URL: {url}")
        print(f"   Source: {source}")
        
        if not url:
            print("   ⚠️  No URL found, skipping")
            skipped_count += 1
            continue
        
        try:
            # Scrape the page
            print("   🔍 Scraping...")
            html = await firecrawl.fetch_html(url)
            
            if not html:
                print("   ❌ Failed to scrape (empty response)")
                failed_count += 1
                failed_urls.append((url, "Empty HTML"))
                continue
            
            # Parse based on source
            if source == 'crozilla':
                parser = crozilla_parser
            else:
                parser = njuskalo_parser
            
            print("   🔍 Parsing...")
            parsed_listing = await parser.parse(html, url)
            
            # Check if we got coordinates
            latitude = parsed_listing.latitude
            longitude = parsed_listing.longitude
            
            if latitude and longitude:
                # Update database
                print(f"   ✅ Found coordinates: {latitude}, {longitude}")
                
                update_data = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'updated_at': datetime.utcnow().isoformat(),
                }
                
                # Also update distance_from_center if we have it
                if hasattr(parsed_listing, 'distance_from_center') and parsed_listing.distance_from_center:
                    update_data['distance_from_center'] = parsed_listing.distance_from_center
                    print(f"   ✅ Updated distance: {parsed_listing.distance_from_center:.2f} km")
                
                supabase.client.table('listings_v2')\
                    .update(update_data)\
                    .eq('id', listing_id)\
                    .execute()
                
                success_count += 1
            else:
                print("   ⚠️  No coordinates found in scraped data")
                failed_count += 1
                failed_urls.append((url, "No coordinates in parsed data"))
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed_count += 1
            failed_urls.append((url, str(e)))
        
        # Small delay to avoid rate limiting
        if i < len(listings):
            await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total processed: {len(listings)}")
    print(f"✅ Successfully updated: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️  Skipped: {skipped_count}")
    
    if failed_urls:
        print(f"\n❌ Failed URLs ({len(failed_urls)}):")
        for url, reason in failed_urls[:10]:  # Show first 10
            print(f"  - {url}")
            print(f"    Reason: {reason}")
        
        if len(failed_urls) > 10:
            print(f"  ... and {len(failed_urls) - 10} more")
    
    print("\n" + "=" * 80)
    print("✅ Re-scraping complete!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

