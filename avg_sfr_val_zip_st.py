import pgeocode
import pandas as pd
import geopandas as gpd
import streamlit as st
import pydeck as pdk
from os import listdir
from datetime import datetime as dt

GEOMETRY_DIR = 'geometries/'

st.set_page_config(page_title="Avg SFR Vals by ZIP", layout="wide", page_icon=":house:")


@st.cache_data(show_spinner='Loading Avg SFR Value Data...')
def load_data():
    # Checking Zillow File
    zillow_raw_df = pd.read_csv("../Zillow SFR Avg Values by ZIP (Aug 2023).csv", dtype={'RegionID':'str', 'RegionName':'str'})
    zillow_raw_df = zillow_raw_df.rename(columns={'RegionName':'ZIP', 'CountyName':'County'}).drop(columns=['RegionID', 'SizeRank', 'RegionType','StateName'])

    # Add Lat/Long
    nomi = pgeocode.Nominatim('us')
    zillow_raw_df['City_Nomi'] = nomi.query_postal_code(zillow_raw_df['ZIP'].tolist()).place_name

    zillow_raw_df.loc[zillow_raw_df['City'].notna(), 'City_Calc'] = zillow_raw_df['City']
    zillow_raw_df.loc[zillow_raw_df['City'].isna(), 'City_Calc'] = zillow_raw_df['City_Nomi']
    zillow_raw_df['City'] = zillow_raw_df['City_Calc']
    zillow_raw_df = zillow_raw_df.drop(columns=['City_Calc', 'City_Nomi'])
    
    # Use ZIP as index
    zillow_raw_df.index = zillow_raw_df['ZIP']
    zillow_raw_df = zillow_raw_df.drop(columns='ZIP')
    
    zillow_raw_df.iloc[:, 4:] = zillow_raw_df.iloc[:, 4:].round(0)
    
    return zillow_raw_df


@st.cache_data(show_spinner='Loading State ZIP Map...')
def load_geometries(state:str):
    for file in listdir(GEOMETRY_DIR):
        state = state.lower()

        if file[0:2] == state:
            return gpd.GeoDataFrame.from_file(GEOMETRY_DIR + file)
        

# Load Data
zillow_data = load_data()
val_dates = sorted(zillow_data.columns[4:])

# Page Header
st.write('<h1 style=text-align:center>Average Single Family Residence (SFR) Values</h1>', unsafe_allow_html=True)
st.write('<h4 style=text-align:center>by ZIP Code</h4>', unsafe_allow_html=True)

# Filter Expander
with st.expander('Filter Your ZIP Lookup', expanded=True):
    # Main Filter Layout
    r1col1, r1col2 = st.columns(2)
    r2col1, r2col2 = st.columns(2)

    # State Filter
    with r1col1:
        states = sorted(zillow_data['State'].unique())
        slctd_state = st.selectbox('Choose a State', states, 0)
        zillow_data = zillow_data[zillow_data['State'] == slctd_state]

        # Load ZIP Geometries for the State
        zip_geos = load_geometries(slctd_state)
        
    # Metroplex Filter
    with r1col2:
        zillow_data.loc[:, 'Metro'] = zillow_data.loc[:, 'Metro'].fillna('Unrecognized Metroplex')
        metros = sorted(zillow_data['Metro'].unique())
        
        # Make "Unrecognized Metroplex" the last option
        if 'Unrecognized Metroplex' in metros:
            metros.remove('Unrecognized Metroplex')
            metros.append('Unrecognized Metroplex')
        
        slctd_metro = st.selectbox('Choose a Metroplex', metros, 0)
        zillow_data = zillow_data[zillow_data['Metro'] == slctd_metro]

    # County Filter
    with r2col1:
        counties = sorted(zillow_data['County'].unique())
        slctd_county = st.multiselect('Choose a County', counties, counties[0])
        if len(slctd_county) > 0:
            zillow_data = zillow_data[zillow_data['County'].isin(slctd_county)]

    # City Filter
    with r2col2:
        zillow_data.loc[:, 'City'] = zillow_data.loc[:, 'City'].fillna('Unrecognized City')
        cities = sorted(zillow_data['City'].unique())
        
        # Make "Unrecognized City" the last option
        if 'Unrecognized City' in cities:
            cities.remove('Unrecognized City')
            cities.append('Unrecognized City')

        slctd_city = st.multiselect('Choose a City', cities, None)
        if len(slctd_city) > 0:
            zillow_data = zillow_data[zillow_data['City'].isin(slctd_city)]

    # ZIP Filter Layout
    zip_col1, zip_col2 =st.columns([.25, .75])
    
    # ZIP Filter Toggle
    with zip_col1:
        zip_fltr = st.toggle('Choose ZIPs')

    # ZIP Filter
    if zip_fltr:
        zip_slctr = st.multiselect('Choose your ZIP Codes', sorted(zillow_data.index), sorted(zillow_data.index)[0])
        zillow_data = zillow_data.loc[zip_slctr]

# Create historic dataframe and interpolate missing data
historic_data = zillow_data.iloc[:,4:].transpose()
historic_data=historic_data.interpolate()

# Line Chart
st.subheader('Value History')
st.line_chart(historic_data)
historic_data=historic_data.T

# Transfer interpolated data to Zillow dataframe
zillow_data=zillow_data.iloc[:, 0:4].merge(historic_data, 'left', left_index=True, right_index=True)

# Select Value Date
st.subheader('Select a Value Date')
date_fltr = st.select_slider('Select Date (YYYY-MM-DD)', val_dates, val_dates[-1])
date_idx = zillow_data.columns.tolist().index(date_fltr)
dsply_date = dt.strftime(dt.strptime(date_fltr,'%Y-%m-%d'),'%B, %Y')

# Create Map Dataframe
map_data = pd.DataFrame(index=zillow_data.index)
map_data['Value_k'] = zillow_data[date_fltr]/1000
map_data['G_Value'] = 1000 * (255 / map_data['Value_k'] / 4)
map_data['A_Value'] = 255
map_data.loc[map_data['Value_k'].isna(), 'A_Value'] = 0

# Merge Map Dataframe with Geometry Dataframe
map_geos = map_data.merge(zip_geos, 'left', left_index=True, right_on='ZCTA5CE10')
map_geos.index = map_geos['ZCTA5CE10']
map_geos['Latitude'] = pd.to_numeric(map_geos['INTPTLAT10'])
map_geos['Longitude'] = pd.to_numeric(map_geos['INTPTLON10'])
map_geos = gpd.GeoDataFrame(data=map_geos)
map_geos = map_geos.drop(columns=map_geos.columns[3:-3].tolist())
cols = map_geos.columns.tolist()
cols = cols[:3] + cols[-2:] + cols[-3:-2]
map_geos = map_geos[cols]

# Map Header Layout
custm_col1, custm_col2 = st.columns([.8, .2])

# Customize the Map
with custm_col1:
    st.subheader(f'Your Heat Map of {dsply_date}')

with custm_col2:
    map_toggle = st.toggle('3D Map')

# Use 3D Heat Map
if map_toggle:
    geojson_layer_3d = pdk.Layer(
                'GeoJsonLayer',
                data=map_geos,
                stroked=False,
                pickable=True,
                extruded=True,
                elevation_scale=25,
                get_elevation = 'Value_k',
                get_fill_color='[255, G_Value, 0, A_Value]',
                )
    pitch = 50
    map_layer = geojson_layer_3d

# Use "2D" Heat Map
else:
    geojson_layer_2d = pdk.Layer(
                'GeoJsonLayer',
                data=map_geos,
                opacity=0.7,
                stroked=False,
                pickable=True,
                get_fill_color='[255, G_Value, 0, A_Value]',
                )
    pitch = 0
    map_layer = geojson_layer_2d

# Display 3D Heat Map
st.pydeck_chart(pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=map_geos['Latitude'].median(),
            longitude=map_geos['Longitude'].median(),
            zoom=7.75,
            pitch=pitch,
        ),
        layers=map_layer
    ))

# Show Highlight ZIP Values
st.write(f"<h2 style=text-align:center>Your Highlight ZIP Codes of {dsply_date}</h2>", unsafe_allow_html=True)
val_count = map_data['Value_k'].count()

# Highlight ZIP Layout
hl_zips1, hl_zips2, hl_zips3 = st.columns(3)
with hl_zips1:
    st.subheader('Lowest Valued ZIP')
    
    if val_count > 0:
        # Get Lowest ZIP Value
        lo_zip_list = zillow_data.loc[zillow_data[date_fltr] == zillow_data[date_fltr].min()].index.tolist()
        
        # Display Lowest ZIP Value
        lo_zip = lo_zip_list[0]
        lo_zip_val = zillow_data[date_fltr].min()
        st.write(f"{lo_zip} {zillow_data.loc[lo_zip, 'City']}, {slctd_state}\n\nValue: ${lo_zip_val:,.0f}")
    else:
        'No Value Data'

with hl_zips2:
    st.subheader('Median Valued ZIP')

    if val_count > 0:
        # Get Median ZIP Value
        med_zip_idx = abs(zillow_data[date_fltr] - zillow_data[date_fltr].median()).argmin()
        med_zip_list = zillow_data.loc[zillow_data[date_fltr] == zillow_data.iloc[med_zip_idx, date_idx]].index.tolist()
        
        # Display Median ZIP Value
        med_zip = med_zip_list[0]
        med_val = zillow_data[date_fltr].median()
        med_zip_val = zillow_data.iloc[med_zip_idx, date_idx]
        st.write(f"{med_zip} {zillow_data.loc[med_zip, 'City']}, {slctd_state}\n\nValue: ${med_zip_val:,.0f}")
    else:
        'No Value Data'

with hl_zips3:
    st.subheader('Higest Valued ZIP')

    if val_count > 0:
        # Get Highest ZIP Value
        hi_zip_list = zillow_data.loc[zillow_data[date_fltr] == zillow_data[date_fltr].max()].index.tolist()
        
        # Display Highest ZIP Value
        hi_zip = hi_zip_list[0]
        hi_zip_val = zillow_data[date_fltr].max()
        st.write(f"{hi_zip} {zillow_data.loc[hi_zip, 'City']}, {slctd_state}\n\nValue: ${hi_zip_val:,.0f}")
    else:
        'No Value Data'
