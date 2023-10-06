import pgeocode
import pandas as pd
import geopandas as gpd
import streamlit as st
import pydeck as pdk
from os import listdir
from datetime import datetime as dt

st.set_page_config(page_title="Avg SFR Vals by ZIP", layout="wide", page_icon=":house:")

GEOMETRY_DIR = 'geometries/'


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
    
    zillow_raw_df.iloc[:, 6:] = zillow_raw_df.iloc[:, 6:].round(0)
    
    return zillow_raw_df

@st.cache_data(show_spinner='Loading State ZIP Map...')
def load_geometries(state:str):
    for file in listdir(GEOMETRY_DIR):
        state = state.lower()

        if file[0:2] == state:
            return gpd.GeoDataFrame.from_file(GEOMETRY_DIR + file)


# Load Data
zillow_data = load_data()
val_dates = sorted(zillow_data.columns[6:])

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
        if 'Unrecognized City' in cities:
            cities.remove('Unrecognized City')
            cities.append('Unrecognized City')

        slctd_city = st.multiselect('Choose a City', cities, None)
        if len(slctd_city) > 0:
            zillow_data = zillow_data[zillow_data['City'].isin(slctd_city)]

    # ZIP Filter Layout
    zip_col1, zip_col2 =st.columns([.15, .85])
    
    # ZIP Filter Toggle
    with zip_col1:
        zip_fltr = st.toggle('Choose ZIPs')

    # ZIP Filter
    if zip_fltr:
        zip_slctr = st.multiselect('Choose your ZIP Codes', sorted(zillow_data.index), sorted(zillow_data.index)[0])
        zillow_data = zillow_data.loc[zip_slctr]

# Line Chart
st.subheader('Value History')
historic_data = zillow_data.iloc[:,6:].transpose()
st.line_chart(historic_data)

# Select Value Date
st.subheader('Select a Value Date')
date_fltr = st.select_slider('Select Date (YYYY-MM-DD)', val_dates, val_dates[-1])
date_idx = zillow_data.columns.tolist().index(date_fltr)
dsply_date = dt.strftime(dt.strptime(date_fltr,'%Y-%m-%d'),'%B, %Y')

# Get Highest ZIP Value
hi_zip = zillow_data.loc[zillow_data[date_fltr] == zillow_data[date_fltr].max()].index.tolist()[0]
hi_zip_val = zillow_data[date_fltr].max()

# Get Lowest ZIP Value
lo_zip = zillow_data.loc[zillow_data[date_fltr] == zillow_data[date_fltr].min()].index.tolist()[0]
lo_zip_val = zillow_data[date_fltr].min()

# Get Median ZIP Value
med_zip_idx = abs(zillow_data[date_fltr] - zillow_data[date_fltr].median()).argmin()
med_zip = zillow_data.loc[zillow_data[date_fltr] == zillow_data.iloc[med_zip_idx, date_idx]].index.tolist()[0]
med_val = zillow_data[date_fltr].median()
med_zip_val = zillow_data.iloc[med_zip_idx, date_idx]

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

# Column Layer
column_layer = pdk.Layer(
            'ColumnLayer',
            data=map_geos,
            get_position='[Longitude, Latitude]',
            radius=500,
            elevation_scale=25,
            pickable=True,
            extruded=True,
            get_elevation = 'Value_k',
            get_fill_color = '[255, G_Value, 0, A_Value]',
            )

# GeoJson Layer
geojson_layer = pdk.Layer(
            'GeoJsonLayer',
            data=map_geos,
            opacity=0.5,
            stroked=False,
            filled=True,
            pickable=True,
            get_fill_color='[255, G_Value, 0, A_Value]',
            )

map_layers=[]
custm_col1, custm_col2, custm_col3 = st.columns([.7, .15, .15])

# Customize the Map
with custm_col1:
    st.subheader(f'Your Heat Map of {dsply_date}')

with custm_col2:
    if st.toggle('Show Columns', True):
        map_layers.append(column_layer)

with custm_col3:
    if st.toggle('Highlight ZIPs'):
        map_layers.append(geojson_layer)

# Display 3D Heat Map
st.pydeck_chart(pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=map_geos['Latitude'].median(),
            longitude=map_geos['Longitude'].median(),
            zoom=8,
            pitch=60,
        ),
        layers=map_layers
    ))

# Show Highlight ZIP Values
st.write(f"<h3 style=text-align:center>Your Highlight ZIP Codes of {dsply_date}</h3>", unsafe_allow_html=True)

hl_zips1, hl_zips2, hl_zips3 = st.columns(3)
with hl_zips1:
    st.subheader('Lowest Valued ZIP')
    st.write(f"{lo_zip} {zillow_data.loc[lo_zip, 'City']}, {slctd_state}\n\nValue: ${lo_zip_val:,.0f}")

with hl_zips2:
    st.subheader('Median Valued ZIP')
    st.write(f"{med_zip} {zillow_data.loc[med_zip, 'City']}, {slctd_state}\n\nValue: ${med_zip_val:,.0f}")

with hl_zips3:
    st.subheader('Higest Valued ZIP')
    st.write(f"{hi_zip} {zillow_data.loc[hi_zip, 'City']}, {slctd_state}\n\nValue: ${hi_zip_val:,.0f}")
