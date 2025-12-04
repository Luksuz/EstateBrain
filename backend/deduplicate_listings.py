#!/usr/bin/env python3
"""
Deduplicate listings: Remove duplicates with same area + price + district.
Keep different districts (those are different apartments).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def deduplicate():
    from app.services.supabase import get_supabase_client
    
    supabase = get_supabase_client()
    
    print("=" * 60)
    print("DEDUPLICATION: Same Area + Price + District")
    print("=" * 60)
    
    # Fetch all listings
    print("\n📥 Fetching all listings...")
    response = supabase.table('listings_v2').select(
        'id, living_area_m2, price_eur, location_district, source, title, url, created_at'
    ).execute()
    
    listings = response.data
    print(f"   Total listings: {len(listings)}")
    
    # Group by (area, price, district)
    from collections import defaultdict
    groups = defaultdict(list)
    
    for listing in listings:
        area = listing.get('living_area_m2')
        price = listing.get('price_eur')
        district = listing.get('location_district') or 'Unknown'
        
        if area is not None and price is not None:
            # Round area to 1 decimal, price to nearest 100 for fuzzy matching
            key = (round(float(area), 1), round(float(price), -2), district)
            groups[key].append(listing)
    
    # Find duplicates
    duplicates_to_remove = []
    kept_count = 0
    
    for key, group in groups.items():
        if len(group) > 1:
            # Sort: prefer njuskalo over crozilla, then by created_at (oldest first)
            group.sort(key=lambda x: (
                0 if x.get('source') == 'njuskalo' else 1,
                x.get('created_at') or ''
            ))
            
            # Keep the first one, mark rest for removal
            kept_count += 1
            for duplicate in group[1:]:
                duplicates_to_remove.append({
                    'id': duplicate['id'],
                    'area': key[0],
                    'price': key[1],
                    'district': key[2],
                    'source': duplicate.get('source'),
                    'title': duplicate.get('title', '')[:50]
                })
        else:
            kept_count += 1
    
    print(f"\n📊 Analysis:")
    print(f"   Unique groups (area + price + district): {len(groups)}")
    print(f"   Listings to KEEP: {kept_count}")
    print(f"   Duplicates to REMOVE: {len(duplicates_to_remove)}")
    
    if not duplicates_to_remove:
        print("\n✅ No duplicates found!")
        return
    
    # Show sample of duplicates
    print(f"\n📋 Sample duplicates to remove (first 10):")
    print("-" * 80)
    for i, dup in enumerate(duplicates_to_remove[:10]):
        print(f"   {i+1}. {dup['area']}m² | €{dup['price']:,.0f} | {dup['district']} | {dup['source']} | {dup['title'][:40]}...")
    
    if len(duplicates_to_remove) > 10:
        print(f"   ... and {len(duplicates_to_remove) - 10} more")
    
    # Group by source for stats
    by_source = defaultdict(int)
    for dup in duplicates_to_remove:
        by_source[dup['source'] or 'unknown'] += 1
    
    print(f"\n📈 Duplicates by source:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"   {source}: {count}")
    
    # Confirm
    print("\n" + "=" * 60)
    confirm = input(f"🗑️  Remove {len(duplicates_to_remove)} duplicates? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Cancelled.")
        return
    
    # Delete duplicates
    print(f"\n🗑️  Removing duplicates...")
    ids_to_remove = [d['id'] for d in duplicates_to_remove]
    
    # Delete in batches
    batch_size = 50
    deleted = 0
    
    for i in range(0, len(ids_to_remove), batch_size):
        batch = ids_to_remove[i:i + batch_size]
        try:
            supabase.table('listings_v2').delete().in_('id', batch).execute()
            deleted += len(batch)
            print(f"   Deleted {deleted}/{len(ids_to_remove)}...")
        except Exception as e:
            print(f"   ⚠️ Error deleting batch: {e}")
    
    print(f"\n✅ Done! Removed {deleted} duplicates.")
    
    # Verify
    final_count = supabase.table('listings_v2').select('id', count='exact').execute()
    print(f"📊 Final listing count: {final_count.count}")

if __name__ == "__main__":
    asyncio.run(deduplicate())

