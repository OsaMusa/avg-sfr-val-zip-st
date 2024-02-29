import pgeocode
import pandas as pd
from pathlib import Path

# Get Source Data Path
with open('data_prep\source_path.txt') as file:
    DATA_FILE = Path(file.readline())

# Read Source Data
raw_df = pd.read_csv(DATA_FILE, dtype={'RegionName':'str'})
raw_df = raw_df.rename(columns={'RegionName':'ZIP', 'CountyName':'County'}).drop(columns=['RegionID', 'SizeRank', 'RegionType','StateName'])

# Add Lat/Long
nomi = pgeocode.Nominatim('us')
raw_df['City_Nomi'] = nomi.query_postal_code(raw_df['ZIP'].tolist()).place_name

# Clean City column
raw_df.loc[raw_df['City'].notna(), 'City_Calc'] = raw_df['City']
raw_df.loc[raw_df['City'].isna(), 'City_Calc'] = raw_df['City_Nomi']
raw_df['City'] = raw_df['City_Calc']
raw_df = raw_df.drop(columns=['City_Calc', 'City_Nomi'])

# Use ZIP as index
raw_df.index = raw_df['ZIP']
raw_df = raw_df.drop(columns='ZIP')

# Interpolate Gap Months
date_df = raw_df.iloc[:,4:].interpolate(axis=1)
raw_df = raw_df.iloc[:, :4].merge(date_df, 'left', left_index=True, right_index=True)

# Round Values to Nearest Dollar
raw_df.iloc[:, 4:] = raw_df.iloc[:, 4:].round(0)

# Mark Unrecognized Metroplexes
raw_df.loc[:, 'Metro'] = raw_df.loc[:, 'Metro'].fillna('Unrecognized Metroplex')

# Serialize Data
raw_df.to_feather('zhvi-sfr-zip\zhvi.feather')