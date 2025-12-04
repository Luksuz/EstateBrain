#!/usr/bin/env python3
"""
Interactive 3D visualization of the dataset using Plotly.
5 optimal features reduced to 3D using PCA.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def visualize_3d():
    from app.services.ml_router_helpers import get_filtered_listings
    import pandas as pd
    import numpy as np
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        print("Installing plotly...")
        os.system("pip install plotly")
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    
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
    df = df[df['price_eur'] > 0]
    print(f"Valid rows: {len(df)}")
    
    X = df[features].values
    y = df['price_eur'].values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # PCA to 3D
    pca = PCA(n_components=3)
    X_3d = pca.fit_transform(X_scaled)
    
    print(f"\nPCA Explained Variance:")
    print(f"  PC1: {pca.explained_variance_ratio_[0]:.1%}")
    print(f"  PC2: {pca.explained_variance_ratio_[1]:.1%}")
    print(f"  PC3: {pca.explained_variance_ratio_[2]:.1%}")
    print(f"  Total: {sum(pca.explained_variance_ratio_):.1%}")
    
    # Create DataFrame for plotting
    plot_df = pd.DataFrame({
        'PC1': X_3d[:, 0],
        'PC2': X_3d[:, 1],
        'PC3': X_3d[:, 2],
        'Price (€)': y,
        'Price Band': pd.cut(y, bins=[0, 150000, 250000, 400000, float('inf')], 
                            labels=['< €150k', '€150-250k', '€250-400k', '> €400k']),
        'Living Area (m²)': df['living_area_m2'].values,
        'Bedrooms': df['bedroom_count'].values,
        'Renovation': df['renovation_level'].values,
        'Distance (km)': df['distance_from_center'].values,
        'Outdoor (m²)': df['outdoor_area_m2'].values,
        'Title': df['title'].values if 'title' in df.columns else [''] * len(df),
        'District': df['location_district'].values if 'location_district' in df.columns else [''] * len(df),
    })
    
    # Format price for hover
    plot_df['Price Display'] = plot_df['Price (€)'].apply(lambda x: f"€{x:,.0f}")
    
    # ============ VISUALIZATION 1: Color by Price ============
    fig1 = px.scatter_3d(
        plot_df, 
        x='PC1', y='PC2', z='PC3',
        color='Price (€)',
        color_continuous_scale='RdYlGn_r',
        hover_data={
            'PC1': False, 'PC2': False, 'PC3': False,
            'Price Display': True,
            'Living Area (m²)': True,
            'Bedrooms': True,
            'Renovation': True,
            'Distance (km)': ':.1f',
            'District': True,
        },
        title='🏠 Real Estate Dataset - 3D View (Color = Price)',
    )
    
    fig1.update_layout(
        scene=dict(
            xaxis_title=f'PC1 ({pca.explained_variance_ratio_[0]:.0%}) - Size',
            yaxis_title=f'PC2 ({pca.explained_variance_ratio_[1]:.0%}) - Location',
            zaxis_title=f'PC3 ({pca.explained_variance_ratio_[2]:.0%}) - Condition',
        ),
        width=1000,
        height=800,
        template='plotly_dark',
    )
    
    fig1.update_traces(marker=dict(size=5, opacity=0.8))
    
    # Save
    output1 = os.path.join(os.path.dirname(__file__), 'viz_3d_price.html')
    fig1.write_html(output1)
    print(f"\n✅ Saved: {output1}")
    
    # ============ VISUALIZATION 2: Color by Price Band ============
    fig2 = px.scatter_3d(
        plot_df, 
        x='PC1', y='PC2', z='PC3',
        color='Price Band',
        color_discrete_map={
            '< €150k': '#2ecc71',
            '€150-250k': '#f1c40f', 
            '€250-400k': '#e67e22',
            '> €400k': '#e74c3c'
        },
        hover_data={
            'PC1': False, 'PC2': False, 'PC3': False,
            'Price Display': True,
            'Living Area (m²)': True,
            'Bedrooms': True,
            'Renovation': True,
            'Distance (km)': ':.1f',
            'District': True,
        },
        title='🏠 Real Estate Dataset - 3D View (Color = Price Band)',
    )
    
    fig2.update_layout(
        scene=dict(
            xaxis_title=f'PC1 ({pca.explained_variance_ratio_[0]:.0%}) - Size',
            yaxis_title=f'PC2 ({pca.explained_variance_ratio_[1]:.0%}) - Location',
            zaxis_title=f'PC3 ({pca.explained_variance_ratio_[2]:.0%}) - Condition',
        ),
        width=1000,
        height=800,
        template='plotly_dark',
        legend_title_text='Price Band',
    )
    
    fig2.update_traces(marker=dict(size=6, opacity=0.8))
    
    output2 = os.path.join(os.path.dirname(__file__), 'viz_3d_bands.html')
    fig2.write_html(output2)
    print(f"✅ Saved: {output2}")
    
    # ============ VISUALIZATION 3: Direct Features (no PCA) ============
    # Use actual features for more intuitive understanding
    fig3 = px.scatter_3d(
        plot_df, 
        x='Living Area (m²)', 
        y='Distance (km)', 
        z='Renovation',
        color='Price (€)',
        color_continuous_scale='RdYlGn_r',
        size='Bedrooms',
        size_max=15,
        hover_data={
            'Price Display': True,
            'Bedrooms': True,
            'Outdoor (m²)': True,
            'District': True,
        },
        title='🏠 Real Estate: Area × Distance × Renovation (Size = Bedrooms)',
    )
    
    fig3.update_layout(
        scene=dict(
            xaxis_title='Living Area (m²)',
            yaxis_title='Distance from Center (km)',
            zaxis_title='Renovation Level (0-10)',
        ),
        width=1000,
        height=800,
        template='plotly_dark',
    )
    
    output3 = os.path.join(os.path.dirname(__file__), 'viz_3d_features.html')
    fig3.write_html(output3)
    print(f"✅ Saved: {output3}")
    
    # ============ VISUALIZATION 4: Animated by Price Band ============
    fig4 = go.Figure()
    
    colors = {
        '< €150k': '#2ecc71',
        '€150-250k': '#f1c40f', 
        '€250-400k': '#e67e22',
        '> €400k': '#e74c3c'
    }
    
    for band in ['< €150k', '€150-250k', '€250-400k', '> €400k']:
        mask = plot_df['Price Band'] == band
        subset = plot_df[mask]
        
        fig4.add_trace(go.Scatter3d(
            x=subset['Living Area (m²)'],
            y=subset['Distance (km)'],
            z=subset['Renovation'],
            mode='markers',
            name=f'{band} ({len(subset)})',
            marker=dict(
                size=6,
                color=colors[band],
                opacity=0.8,
                line=dict(width=0.5, color='white')
            ),
            text=[f"€{p:,.0f}<br>{a}m²<br>{b} bed<br>{d}" 
                  for p, a, b, d in zip(subset['Price (€)'], subset['Living Area (m²)'], 
                                        subset['Bedrooms'], subset['District'])],
            hoverinfo='text+name',
        ))
    
    fig4.update_layout(
        title='🏠 Real Estate Explorer - Interactive 3D',
        scene=dict(
            xaxis_title='Living Area (m²)',
            yaxis_title='Distance from Center (km)',
            zaxis_title='Renovation Level',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),
        ),
        width=1100,
        height=850,
        template='plotly_dark',
        legend=dict(
            title='Price Band (click to toggle)',
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0.5)"
        ),
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                y=0.0,
                x=0.0,
                xanchor="left",
                buttons=[
                    dict(label="Rotate",
                         method="animate",
                         args=[None, {"frame": {"duration": 50, "redraw": True},
                                     "fromcurrent": True,
                                     "transition": {"duration": 0}}]),
                ]
            )
        ]
    )
    
    output4 = os.path.join(os.path.dirname(__file__), 'viz_3d_explorer.html')
    fig4.write_html(output4)
    print(f"✅ Saved: {output4}")
    
    print("\n" + "=" * 60)
    print("📊 VISUALIZATIONS CREATED")
    print("=" * 60)
    print(f"\n1. viz_3d_price.html     - PCA 3D, color by price")
    print(f"2. viz_3d_bands.html     - PCA 3D, color by price band")
    print(f"3. viz_3d_features.html  - Actual features (Area×Distance×Renovation)")
    print(f"4. viz_3d_explorer.html  - Interactive explorer with toggles")
    print(f"\n💡 Open any .html file in your browser to explore!")
    print(f"   - Click & drag to rotate")
    print(f"   - Scroll to zoom")
    print(f"   - Hover for details")
    print(f"   - Click legend to show/hide price bands")
    
    # Open the best one automatically
    import webbrowser
    webbrowser.open(f'file://{output4}')

if __name__ == "__main__":
    asyncio.run(visualize_3d())

