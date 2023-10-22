import pgeocode
import pandas as pd
import geopandas as gpd
import streamlit as st
from pathlib import Path
from os import listdir

DATA_FILE = Path('zhvi-sfr-zip/zhvi.feather')
GEOMETRY_DIR = Path('geometries')

st.set_page_config(page_title="Avg SFR Historic Values", layout='wide', page_icon=':house:', initial_sidebar_state='collapsed')

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

if 'chart_list_view' not in st.session_state:
    st.session_state['chart_list_view'] = False

if 'zip_toggle_pos' not in st.session_state:
    st.session_state['zip_toggle_pos'] = False


@st.cache_data(show_spinner='Loading Avg SFR Value Data...', ttl='12h')
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
    st.session_state['default_cities'] = []    
    st.session_state['default_zips'] = sorted(df.index)[0]

    df = None
    state_dict = None
    chosen_state = None
    counties = None
    metro_opts = None


def update_metro():
    chosen_state = st.session_state['chosen_state']
    chosen_metro = st.session_state['chosen_metro']
    
    df = st.session_state['df']
    df = df[(df['State'] == chosen_state) & (df['Metro'] == chosen_metro)]        
    counties = sorted(df['County'].unique())
    
    df = df.loc[df['County'] == counties[0]]
    
    st.session_state['default_metro'] = st.session_state['metro_opts'].index(chosen_metro)
    st.session_state['default_counties'] = counties[0]
    st.session_state['default_cities'] = []
    st.session_state['default_zips'] = sorted(df.index)[0]

    df = None
    chosen_state = None
    chosen_metro = None
    counties = None


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
    st.session_state['default_counties'] = []
    st.session_state['default_cities'] = []
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

    df = None
    chosen_state = None
    chosen_metro = None
    chosen_counties = None
    chosen_cities = None
    chosen_zips = None
    cities = None
    zip_codes = None


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

    df = None
    chosen_state = None
    chosen_metro = None
    chosen_counties = None
    chosen_cities = None
    chosen_zips = None
    zip_codes = None


def update_zip_toggle():
    st.session_state['zip_toggle_pos'] = st.session_state['zip_toggle']


def update_chart_list():
    st.session_state['chart_list_view'] = st.session_state['chart_list']


def load_geometries(state:str):
    for file in listdir(GEOMETRY_DIR):
        state = state.lower()

        if file[0:2] == state:
            return gpd.read_feather(GEOMETRY_DIR / file)


# Load Data
if 'df' not in st.session_state:
    st.session_state['df'] = load_data()
    st.session_state['val_dates'] = sorted(st.session_state['df'].columns[4:])

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
        st.session_state['state_opts'] = sorted(st.session_state['df']['State'].unique())
        slctd_state = st.selectbox('Choose a State', st.session_state['state_opts'], st.session_state['default_state'], key='chosen_state', on_change=update_state)
        st.session_state['filtered_df'] = st.session_state['df'][st.session_state['df']['State'] == slctd_state]
        
        # Load ZIP Geometries for the State
        st.session_state['zip_geos'] = load_geometries(slctd_state)
    # Metroplex Filter
    with r1col2:
        st.session_state['metro_opts'] = sorted(st.session_state['filtered_df']['Metro'].unique())
        
        # Make "Unrecognized Metroplex" the last option
        if 'Unrecognized Metroplex' in st.session_state['metro_opts']:
            st.session_state['metro_opts'].remove('Unrecognized Metroplex')
            st.session_state['metro_opts'].append('Unrecognized Metroplex')
        
        slctd_metro = st.selectbox('Choose a Metroplex', st.session_state['metro_opts'], st.session_state['default_metro'], key='chosen_metro', on_change=update_metro)
        st.session_state['filtered_df'] = st.session_state['filtered_df'][st.session_state['filtered_df']['Metro'] == slctd_metro]

    # County Filter
    with r2col1:
        st.session_state['county_opts'] = sorted(st.session_state['filtered_df']['County'].unique())
        slctd_county = st.multiselect('Choose a County', st.session_state['county_opts'], st.session_state['default_counties'], key='chosen_counties', on_change=update_couties)
        if len(slctd_county) > 0:
            st.session_state['filtered_df'] = st.session_state['filtered_df'][st.session_state['filtered_df']['County'].isin(slctd_county)]

    # City Filter
    with r2col2:
        st.session_state['city_opts'] = sorted(st.session_state['filtered_df']['City'].unique())
        
        slctd_city = st.multiselect('Choose a City', st.session_state['city_opts'], st.session_state['default_cities'], key='chosen_cities', on_change=update_cities)
        if len(slctd_city) > 0:
            st.session_state['filtered_df'] = st.session_state['filtered_df'][st.session_state['filtered_df']['City'].isin(slctd_city)]

    # ZIP Filter Layout
    zip_col1, zip_col2 =st.columns([.25, .75])
    
    # ZIP Filter Toggle
    with zip_col1:
        zip_fltr = st.toggle('Choose ZIPs', key='zip_toggle', value=st.session_state['zip_toggle_pos'], on_change=update_zip_toggle)

    # ZIP Filter
    if zip_fltr:
        zip_slctr = st.multiselect('Choose your ZIP Codes', sorted(st.session_state['filtered_df'].index), st.session_state['default_zips'], key='chosen_zips')
        st.session_state['filtered_df'] = st.session_state['filtered_df'].loc[zip_slctr]

# Create historic dataframe
st.session_state['historic_data'] = st.session_state['filtered_df'].iloc[:,4:].transpose()

# Line Chart
st.subheader('Value History')
st.line_chart(st.session_state['historic_data'])

# Display Map Data Table
if st.checkbox('View the Full List', st.session_state['chart_list_view'], key='chart_list', on_change=update_chart_list):
    st.dataframe(
        st.session_state['filtered_df'].sort_values(st.session_state['filtered_df'].columns[-1], ascending=False).drop(columns=['Metro', 'County', 'State'])
    )

# Empty Unused Variables
r1col1 = None
r1col2 = None
r2col1 = None
r2col2 = None
slctd_state = None
slctd_metro = None
slctd_county = None
slctd_city = None
zip_fltr = None
zip_slctr = None
zip_col1 = None
zip_col2 = None
