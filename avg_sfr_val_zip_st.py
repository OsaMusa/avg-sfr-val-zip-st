import pgeocode
import pandas as pd
import streamlit as st
import pydeck as pdk
from datetime import datetime as dt

st.set_page_config(page_title="Avg SFR Vals by ZIP", layout="wide")


@st.cache_data
def load_data():
    # Checking Zillow File
    zillow_raw_df = pd.read_csv("../Zillow SFR Avg Values by ZIP (Aug 2023).csv", dtype={'RegionID':'str', 'RegionName':'str'})
    zillow_raw_df = zillow_raw_df.rename(columns={'RegionName':'ZIP', 'CountyName':'County'}).drop(columns=['RegionID', 'SizeRank', 'RegionType','StateName'])

    # Add Lat/Long
    nomi = pgeocode.Nominatim('us')
    zillow_raw_df['Latitude'] = nomi.query_postal_code(zillow_raw_df['ZIP'].tolist()).latitude
    zillow_raw_df['Longitude'] = nomi.query_postal_code(zillow_raw_df['ZIP'].tolist()).longitude
    zillow_raw_df['City_Nomi'] = nomi.query_postal_code(zillow_raw_df['ZIP'].tolist()).place_name

    zillow_raw_df.loc[zillow_raw_df['City'].notna(), 'City_Calc'] = zillow_raw_df['City']
    zillow_raw_df.loc[zillow_raw_df['City'].isna(), 'City_Calc'] = zillow_raw_df['City_Nomi']
    zillow_raw_df['City'] = zillow_raw_df['City_Calc']
    zillow_raw_df = zillow_raw_df.drop(columns=['City_Calc', 'City_Nomi'])
    
    # Reorder the fields
    cols = zillow_raw_df.columns.tolist()
    cols = cols[0:5] + cols[-2:] + cols[5:-2]
    zillow_raw_df = zillow_raw_df[cols]
    
    # Use ZIP as index
    zillow_raw_df.index = zillow_raw_df['ZIP']
    zillow_raw_df = zillow_raw_df.drop(columns='ZIP')
    
    zillow_raw_df.iloc[:, 6:] = zillow_raw_df.iloc[:, 6:].round(0)
    
    return zillow_raw_df


# Load Data
zillow_data = load_data()
val_dates = sorted(zillow_data.columns[6:])

# Page Header
# st.write('<h1 style=text-align:center>Average Single Family Residence (SFR) Values by ZIP Code</h1>', unsafe_allow_html=True)
st.write('<h1 style=text-align:center>Average Single Family Residence (SFR) Values</h1>', unsafe_allow_html=True)
st.write('<h4 style=text-align:center>by ZIP Code</h4>', unsafe_allow_html=True)

# st.subheader('Filter Your ZIP Lookup')
with st.expander('Filter Your ZIP Lookup', expanded=True):
    # Filters
    r1col1, r1col2 = st.columns(2)
    r2col1, r2col2 = st.columns(2)
    with r1col1:
        # State Filter
        states = sorted(zillow_data['State'].unique())
        slctd_state = st.selectbox('Choose a State', states, 0)
        zillow_data = zillow_data[zillow_data['State'] == slctd_state]

    with r1col2:
        # Metroplex Filter
        zillow_data.loc[:, 'Metro'] = zillow_data.loc[:, 'Metro'].fillna('Unrecognized Metroplex')
        metros = sorted(zillow_data['Metro'].unique())
        if 'Unrecognized Metroplex' in metros:
            metros.remove('Unrecognized Metroplex')
            metros.append('Unrecognized Metroplex')
        
        slctd_metro = st.selectbox('Choose a Metroplex', metros, 0)
        zillow_data = zillow_data[zillow_data['Metro'] == slctd_metro]

    with r2col1:
        # County Filter
        counties = sorted(zillow_data['County'].unique())
        slctd_county = st.multiselect('Choose a County', counties, None)
        if len(slctd_county) > 0:
            zillow_data = zillow_data[zillow_data['County'].isin(slctd_county)]

    with r2col2:
        # City Filter
        zillow_data.loc[:, 'City'] = zillow_data.loc[:, 'City'].fillna('Unrecognized City')
        cities = sorted(zillow_data['City'].unique())
        if 'Unrecognized City' in cities:
            cities.remove('Unrecognized City')
            cities.append('Unrecognized City')

        slctd_city = st.multiselect('Choose a City', cities, None)
        if len(slctd_city) > 0:
            zillow_data = zillow_data[zillow_data['City'].isin(slctd_city)]

    # ZIP Filter
    zip_col1, zip_col2 =st.columns([.15, .85])
    with zip_col1:
        zip_fltr = st.toggle('Filter ZIPs?')

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

# Create map dataframe
map_data = zillow_data.loc[:, ('Latitude', 'Longitude')]
map_data['Value_k'] = zillow_data[date_fltr]/1000
map_data['G_Value'] = 1000 * (255 / map_data['Value_k'] / 4)
map_data['Value_k'] = map_data['Value_k'].fillna(0)

# Display 3D Heat Map
st.subheader(f'Your Heat Map of {dsply_date}')
st.pydeck_chart(pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=map_data['Latitude'].mean(),
            longitude=map_data['Longitude'].mean(),
            zoom=8,
            pitch=60,
        ),
        layers=[
            pdk.Layer(
            'ColumnLayer',
            data=map_data,
            get_position='[Longitude, Latitude]',
            radius=1000,
            elevation_scale=25,
            pickable=True,
            extruded=True,
            get_elevation = 'Value_k',
            get_fill_color = ['255', 'G_Value', '0', 'Value_k'],
            ),
        ],
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
