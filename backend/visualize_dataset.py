#!/usr/bin/env python3
"""
Visualize the dataset: 5 optimal features reduced to 2D using PCA.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def visualize():
    from app.services.ml_router_helpers import get_filtered_listings
    import pandas as pd
    import numpy as np
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    
    # Get listings
    print("Loading listings...")
    listings = await get_filtered_listings()
    print(f"Loaded {len(listings)} listings")
    
    df = pd.DataFrame(listings)
    
    # Optimal features
    features = ['living_area_m2', 'bedroom_count', 'outdoor_area_m2', 
                'renovation_level', 'distance_from_center']
    
    # Prepare data
    for col in features + ['price_eur']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=features + ['price_eur'])
    print(f"Valid rows: {len(df)}")
    
    X = df[features].values
    y = df['price_eur'].values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # PCA to 2D
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X_scaled)
    
    print(f"\nPCA Explained Variance:")
    print(f"  PC1: {pca.explained_variance_ratio_[0]:.1%}")
    print(f"  PC2: {pca.explained_variance_ratio_[1]:.1%}")
    print(f"  Total: {sum(pca.explained_variance_ratio_):.1%}")
    
    print(f"\nPCA Components (feature weights):")
    for i, comp in enumerate(pca.components_):
        print(f"  PC{i+1}: ", end="")
        weights = [(features[j], comp[j]) for j in range(len(features))]
        weights.sort(key=lambda x: abs(x[1]), reverse=True)
        for feat, w in weights[:3]:
            print(f"{feat}({w:+.2f}) ", end="")
        print()
    
    # Create figure with multiple plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle('Real Estate Dataset Visualization\n5 Optimal Features → 2D (PCA)', 
                 fontsize=14, fontweight='bold')
    
    # Plot 1: Color by price
    ax1 = axes[0, 0]
    scatter1 = ax1.scatter(X_2d[:, 0], X_2d[:, 1], c=y, cmap='RdYlGn_r', 
                           alpha=0.6, s=50, edgecolors='white', linewidth=0.5)
    ax1.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)')
    ax1.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)')
    ax1.set_title('Color = Price (€)')
    cbar1 = plt.colorbar(scatter1, ax=ax1)
    cbar1.set_label('Price (€)')
    
    # Plot 2: Color by living area
    ax2 = axes[0, 1]
    scatter2 = ax2.scatter(X_2d[:, 0], X_2d[:, 1], c=df['living_area_m2'], 
                           cmap='viridis', alpha=0.6, s=50, edgecolors='white', linewidth=0.5)
    ax2.set_xlabel(f'PC1')
    ax2.set_ylabel(f'PC2')
    ax2.set_title('Color = Living Area (m²)')
    cbar2 = plt.colorbar(scatter2, ax=ax2)
    cbar2.set_label('Area (m²)')
    
    # Plot 3: Color by renovation level
    ax3 = axes[1, 0]
    scatter3 = ax3.scatter(X_2d[:, 0], X_2d[:, 1], c=df['renovation_level'], 
                           cmap='coolwarm', alpha=0.6, s=50, edgecolors='white', linewidth=0.5)
    ax3.set_xlabel(f'PC1')
    ax3.set_ylabel(f'PC2')
    ax3.set_title('Color = Renovation Level (0-10)')
    cbar3 = plt.colorbar(scatter3, ax=ax3)
    cbar3.set_label('Renovation')
    
    # Plot 4: Color by distance from center
    ax4 = axes[1, 1]
    scatter4 = ax4.scatter(X_2d[:, 0], X_2d[:, 1], c=df['distance_from_center'], 
                           cmap='plasma', alpha=0.6, s=50, edgecolors='white', linewidth=0.5)
    ax4.set_xlabel(f'PC1')
    ax4.set_ylabel(f'PC2')
    ax4.set_title('Color = Distance from Center (km)')
    cbar4 = plt.colorbar(scatter4, ax=ax4)
    cbar4.set_label('Distance (km)')
    
    plt.tight_layout()
    
    # Save
    output_path = os.path.join(os.path.dirname(__file__), 'dataset_visualization.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n✅ Saved: {output_path}")
    
    # Also create a price bands visualization
    fig2, ax = plt.subplots(figsize=(12, 8))
    
    # Define price bands
    price_bands = [
        (0, 150000, '< €150k', 'green'),
        (150000, 250000, '€150-250k', 'yellow'),
        (250000, 400000, '€250-400k', 'orange'),
        (400000, float('inf'), '> €400k', 'red'),
    ]
    
    for low, high, label, color in price_bands:
        mask = (y >= low) & (y < high)
        ax.scatter(X_2d[mask, 0], X_2d[mask, 1], label=f'{label} ({mask.sum()})', 
                  alpha=0.6, s=60, edgecolors='white', linewidth=0.5)
    
    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance) - mainly Living Area', fontsize=11)
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance) - mainly Distance/Renovation', fontsize=11)
    ax.set_title('Real Estate Dataset by Price Bands\n(5 features → 2D via PCA)', fontsize=13, fontweight='bold')
    ax.legend(title='Price Band', loc='upper right')
    ax.grid(True, alpha=0.3)
    
    output_path2 = os.path.join(os.path.dirname(__file__), 'dataset_price_bands.png')
    plt.savefig(output_path2, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Saved: {output_path2}")
    
    # Stats summary
    print("\n📊 Dataset Summary:")
    print(f"  Total listings: {len(df)}")
    print(f"  Price range: €{y.min():,.0f} - €{y.max():,.0f}")
    print(f"  Avg price: €{y.mean():,.0f}")
    print(f"  Area range: {df['living_area_m2'].min():.0f} - {df['living_area_m2'].max():.0f} m²")
    
    plt.show()

if __name__ == "__main__":
    asyncio.run(visualize())

