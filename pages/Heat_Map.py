import pgeocode
import pandas as pd
import geopandas as gpd
import streamlit as st
import pydeck as pdk
from pathlib import Path
from os import listdir
from datetime import datetime as dt

DATA_FILE = Path('../zhvi-sfr-zip/zhvi.feather')
GEOMETRY_DIR = Path('../geometries')

st.set_page_config(page_title="Avg SFR Values Heat Map", layout='wide', page_icon=':house:', initial_sidebar_state='collapsed')

if 'zip_state' not in st.session_state:
    st.session_state['zip_state'] = 'Alaska'

if 'default_state' not in st.session_state:
    st.session_state['default_state'] = 0

if 'default_metro' not in st.session_state:
    st.session_state['default_metro'] = 0

if 'default_counties' not in st.session_state:
    st.session_state['default_counties'] = ['Anchorage Borough']

if 'default_cities' not in st.session_state:
    st.session_state['default_cities'] = []

if 'default_zips' not in st.session_state:
    st.session_state['default_zips'] = ['99501']

if 'zip_toggle_pos' not in st.session_state:
    st.session_state['zip_toggle_pos'] = False

if 'map_toggle_pos' not in st.session_state:
    st.session_state['map_toggle_pos'] = False

if 'date_slider' not in st.session_state:
    st.session_state['date_slider'] = None


@st.cache_data(show_spinner='Loading Avg SFR Value Data...')
def load_data():
    # Checking Zillow File
    zillow_raw_df = pd.read_feather(DATA_FILE)
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
    
    # Interpolate Gap Months
    date_df = zillow_raw_df.iloc[:,4:].interpolate(axis=1)
    zillow_raw_df = zillow_raw_df.iloc[:, :4].merge(date_df, 'left', left_index=True, right_index=True)
    
    # Round Values to Nearest Dollar
    zillow_raw_df.iloc[:, 4:] = zillow_raw_df.iloc[:, 4:].round(0)
    
    # Mark Unrecognized Metroplexes
    zillow_raw_df.loc[:, 'Metro'] = zillow_raw_df.loc[:, 'Metro'].fillna('Unrecognized Metroplex')
    
    return zillow_raw_df


def update_state():
    df = st.session_state['df']
    chosen_state = st.session_state['chosen_state']
    
    state_dict = {
        'AK':'Alaska', 'AL':'Alabama', 'AR':'Arkansas', 'AZ':'Arizona', 'CA':'California',
        'CO':'Colorado', 'CT':'Connecticut', 'DC':'District of Columbia', 'DE':'Delaware',
        'FL':'Florida', 'GA':'Georgia', 'HI':'Hawaii', 'IA':'Iowa', 'ID':'Idaho',
        'IL':'Illinois', 'IN':'Indiana', 'KS':'Kansas', 'KY':'Kentucky', 'LA':'Louisiana',
        'MA':'Massachusetts', 'MD':'Maryland', 'ME':'Maine', 'MI':'Michigan', 'MN':'Minnesota',
        'MO':'Missouri', 'MS':'Mississippi', 'MT':'Montana', 'NC':'North Carolina',
        'ND':'North Dakota', 'NE':'Nebraska', 'NH':'New Hampshire','NJ':'New Jersey',
        'NM':'New Mexico', 'NV':'Nevada', 'NY':'New York', 'OH':'Ohio', 'OK':'Oklahoma',
        'OR':'Oregon', 'PA':'Pennsylvania', 'RI':'Rhode Island', 'SC':'South Carolina',
        'SD':'South Dakota', 'TN':'Tennessee', 'TX':'Texas', 'UT':'Utah', 'VA':'Virginia',
        'VT':'Vermont', 'WA':'Washington', 'WI':'Wisconsin', 'WV':'West Virginia', 'WY':'Wyoming'
    }
    
    df = df.loc[df['State'] == chosen_state]
    metro_opts = sorted(df['Metro'].unique())
    
    # Make "Unrecognized Metroplex" the last option
    if 'Unrecognized Metroplex' in metro_opts:
        metro_opts.remove('Unrecognized Metroplex')
        metro_opts.append('Unrecognized Metroplex')

    df = df.loc[df['Metro'] == metro_opts[0]]
    counties = sorted(df['County'].unique())

    df = df.loc[df['County'] == counties[0]]

    st.session_state['zip_state'] = state_dict[chosen_state]
    st.session_state['default_state'] = list(state_dict.values()).index(st.session_state['zip_state'])
    st.session_state['default_metro'] = 0
    st.session_state['default_counties'] = sorted(df['County'].unique())[0]
    st.session_state['default_cities']=[]    
    st.session_state['default_zips'] = sorted(df.index)[0]


def update_metro():
    chosen_state = st.session_state['chosen_state']
    chosen_metro = st.session_state['chosen_metro']
    
    df = st.session_state['df']
    df = df[(df['State'] == chosen_state) & (df['Metro'] == chosen_metro)]        
    counties = sorted(df['County'].unique())
    
    df = df.loc[df['County'] == counties[0]]
    
    st.session_state['default_metro'] = metros.index(chosen_metro)
    st.session_state['default_counties'] = counties[0]
    st.session_state['default_cities']=[]
    st.session_state['default_zips'] = sorted(df.index)[0]


def update_couties():
    chosen_state = st.session_state['chosen_state']
    chosen_metro = st.session_state['chosen_metro']
    chosen_counties = st.session_state['chosen_counties']
    chosen_cities = st.session_state['chosen_cities']
    
    if 'chosen_zips' in st.session_state:
        chosen_zips = st.session_state['chosen_zips']
    else:
        chosen_zips = []
    
    # Re-Initialize Default Counties/Cities
    st.session_state['default_counties']=[]
    st.session_state['default_cities']=[]
    st.session_state['default_zips'] = []
    
    df = st.session_state['df']
    df = df.loc[(df['State'] == chosen_state) & (df['Metro'] == chosen_metro)]
    
    # Update Default Counties
    st.session_state['default_counties'] = chosen_counties
    
    # Update Default Cities
    if len(chosen_counties) > 0:
        df = df.loc[df['County'].isin(chosen_counties)]
        cities = sorted(df['City'].unique())
        
        for city in chosen_cities:
            if city in cities:
                st.session_state['default_cities'].append(city)
    else:
        st.session_state['default_cities'] = chosen_cities
    
    if len(st.session_state['default_cities']) > 0:
        df = df.loc[df['City'].isin(chosen_cities)]

    zip_codes = sorted(df.index)
    for zip_code in chosen_zips:
        if zip_code in zip_codes:
            st.session_state['default_zips'].append(zip_code)

    if len(st.session_state['default_zips']) == 0:
        st.session_state['default_zips'] = zip_codes[0]


def update_cities():
    chosen_state = st.session_state['chosen_state']
    chosen_metro = st.session_state['chosen_metro']
    chosen_counties = st.session_state['chosen_counties']
    chosen_cities = st.session_state['chosen_cities']
    st.session_state['default_zips'] = []

    if 'chosen_zips' in st.session_state:
        chosen_zips = st.session_state['chosen_zips']
    else:
        chosen_zips = []

    df = st.session_state['df']
    df = df[(df['State'] == chosen_state) & (df['Metro'] == chosen_metro)]
    
    if len(chosen_counties) > 0:
        df = df.loc[df['County'].isin(chosen_counties)]
    
    if len(chosen_cities) > 0:
        df = df.loc[df['City'].isin(chosen_cities)]
    
    zip_codes = sorted(df.index)
    for zip_code in chosen_zips:
        if zip_code in zip_codes:
            st.session_state['default_zips'].append(zip_code)

    if len(st.session_state['default_zips']) == 0:
        st.session_state['default_zips'] = zip_codes[0]
    
    st.session_state['default_cities'] = st.session_state['chosen_cities']


def update_zip_toggle():
    st.session_state['zip_toggle_pos'] = st.session_state['zip_toggle']


def update_map_toggle():
    st.session_state['map_toggle_pos'] = st.session_state['map_toggle']


def update_chosen_date():
    st.session_state['date_slider'] = st.session_state['chosen_date']


@st.cache_data(show_spinner=f'Loading {st.session_state.zip_state} ZIP Code Map...')
def load_geometries(state:str):
    for file in listdir(GEOMETRY_DIR):
        state = state.lower()

        if file[0:2] == state:
            return gpd.read_feather(GEOMETRY_DIR / file)


# Load Data
zillow_data = load_data()
st.session_state['df'] = zillow_data
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
        slctd_state = st.selectbox('Choose a State', states, st.session_state['default_state'], key='chosen_state', on_change=update_state)
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
        
        slctd_metro = st.selectbox('Choose a Metroplex', metros, st.session_state['default_metro'], key='chosen_metro', on_change=update_metro)
        zillow_data = zillow_data[zillow_data['Metro'] == slctd_metro]

    # County Filter
    with r2col1:
        counties = sorted(zillow_data['County'].unique())
        slctd_county = st.multiselect('Choose a County', counties, st.session_state['default_counties'], key='chosen_counties', on_change=update_couties)
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

        slctd_city = st.multiselect('Choose a City', cities, st.session_state['default_cities'], key='chosen_cities', on_change=update_cities)
        if len(slctd_city) > 0:
            zillow_data = zillow_data[zillow_data['City'].isin(slctd_city)]

    # ZIP Filter Layout
    zip_col1, zip_col2 =st.columns([.25, .75])

    # ZIP Filter Toggle
    with zip_col1:
        zip_fltr = st.toggle('Choose ZIPs', key='zip_toggle', value=st.session_state['zip_toggle_pos'], on_change=update_zip_toggle)

    # ZIP Filter
    if zip_fltr:
        zip_slctr = st.multiselect('Choose your ZIP Codes', sorted(zillow_data.index), st.session_state['default_zips'], key='chosen_zips')
        zillow_data = zillow_data.loc[zip_slctr]

# Select Value Date
st.subheader('Select a Value Date')

if st.session_state['date_slider'] != None:
    date_fltr = st.select_slider('Select Date (YYYY-MM-DD)', val_dates, st.session_state['date_slider'], key='chosen_date', on_change=update_chosen_date)
else:
    date_fltr = st.select_slider('Select Date (YYYY-MM-DD)', val_dates, val_dates[-1], key='chosen_date', on_change=update_chosen_date)

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
    map_toggle = st.toggle('3D Map', key='map_toggle', value=st.session_state['map_toggle_pos'], on_change=update_map_toggle)

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
