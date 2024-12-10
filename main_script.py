"""
Election and Military Reserves Analysis Script
-------------------------------------------
This script analyzes the relationship between voting patterns and military reserve service
during the Iron Swords War. It processes data from multiple sources and creates a
visualization comparing coalition/opposition voting rates with reserve duty participation.

Dependencies:
    - pandas
    - numpy
    - pathlib
    - matplotlib
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

def invert(s):
    """
    Reverses a string to handle right-to-left Hebrew text display.
    
    Args:
        s (str): The input string to be reversed
        
    Returns:
        str: The reversed string
    """
    return s[::-1]

# Set up data path
path = Path('./data')

# Load and prepare data
population = pd.read_csv(path / 'pop2.csv')
voting = pd.read_csv(path / 'expc.csv', index_col='שם ישוב')
reserves = pd.read_csv(path / 'reserve_data.csv', index_col='city')

# Merge voting and reserves data
data = pd.merge(voting, reserves, left_index=True, right_index=True, how='left')

# Define party affiliations
coalition = {
    r"מחל" : "The Union",
    r"שס" : "Shas",
    r"ג" : "United Torah Judaism",
    r"ט" : "Religious Zionism and Jewish Power",
    r"ב": "Bait Yehudi",
    r"saar": "New Hope",
    }
opposition = {
    r"פה": "There Is Future",
    r"כן": "The Kingdom Camp",
    r"ל": "Israel Is Our Home",
    r"עם": "United Arab List",
    r"ום": "Hadash-Ta'al",
    r'אמת': 'The Work',
    r"מרצ": "Meretz",
    }

# possible to claim some of saar to coalition, default ratio is 0
SAAR_RATIO_FROM_GANTZ = 0.00
data['saar'] = data['כן'] * SAAR_RATIO_FROM_GANTZ
data['כן'] = data['כן'] * (1 - SAAR_RATIO_FROM_GANTZ)

# Calculate total votes for coalition and opposition
data['coal'] = data[coalition.keys()].sum(axis=1)
data['opp'] = data[opposition.keys()].sum(axis=1)

# remove duplicate index from data
data = data.loc[~data.index.duplicated(keep='first')]

# Filter and clean data
data_analysis = data[data[['coal', 'opp', 'reserve_days']] > 0].copy()
data_analysis.dropna(subset=['coal', 'opp', 'reserve_days'], inplace=True)
data_analysis.dropna(axis=1, inplace=True)

# Calculate various metrics and ratios

data_analysis['kosher'] = data['כשרים']  # Valid votes
data_analysis['coal_reserves_ratio'] = data_analysis['reserve_days'] / data_analysis['coal']
data_analysis['opp_reserves_ratio'] = data_analysis['reserve_days'] / data_analysis['opp']

# Calculate voting ratios
# data_analysis['opp_ratio'] = data_analysis['opp'] / data_analysis['kosher']
data_analysis['coal_ratio'] = data_analysis['coal'] / (data_analysis['coal'] + data_analysis['opp'])
data_analysis['opp_ratio'] = 1 - data_analysis['coal_ratio']

# Calculate weighted reserve days
data_analysis['coal_reserves_times_ratio'] = data_analysis['coal_ratio'] * data_analysis['reserve_days']
data_analysis['opp_reserves_times_ratio'] = data_analysis['opp_ratio'] * data_analysis['reserve_days']

# Initialize results DataFrame
results = pd.DataFrame()

# Process data for both coalition and opposition
for party in ['coal', 'opp']:
    """
    For each party (coalition/opposition):
    1. Create voting ratio bins (0-100% in 5% increments)
    2. Calculate cumulative reserve days for each bin
    3. Calculate cumulative valid votes for each bin
    4. Normalize results relative to the 95th percentile
    """
    data_analysis[party + '_cut'] = pd.cut(
        data_analysis[party + '_ratio'], 
        bins=np.arange(0, 1.05, step=0.05), 
        labels=np.round(np.arange(0,1,step=0.05), 2)
    )
    
    data_analysis.sort_values(by=party + '_cut', inplace=True)
    
    data_analysis[party + '_reserves'] = data_analysis['reserve_days'].cumsum()
    data_analysis[party + '_votes_cumsum'] = data_analysis['kosher'].cumsum()
    
    results[party] = data_analysis[[party + '_reserves', party + '_cut']].groupby(
        party + '_cut', 
        observed=False
    ).agg("max")
    
    # Normalize results
    results[party] /= results.loc[0.95, party]

# Create visualization
fig, ax = plt.subplots(figsize=(12,6), dpi=500)
colors = ['tab:blue', 'tab:red']

# Plot coalition and opposition lines
for party, color, label in zip(['coal', 'opp'], colors, ['קואליציה', 'אופוזיציה']):
    ax.plot(results.index, results[party], label=invert(label), color=color, zorder=3)

# Add reference line
ax.plot(results.index, results.index, color='black', alpha=0.5, label=invert('קו 54 מעלות'), zorder=0)

# Set plot labels and styling
ax.set_title(invert('שיעור הצבעה לקואליציה ושיעור ימי מילואים במלחמת חרבות ברזל'), fontsize=15)
ax.set_ylabel(invert('שיעור מסך ימי המילואים'), fontsize=12)
ax.set_xlabel(invert('שיעור הצבעה לקואליציה/אופוזיציה'), fontsize=12)
ax.legend()
ax.grid(axis='both', alpha=0.3)
plt.figtext(0.8, 0.05, '@tom_sadeh')
plt.tight_layout()
plt.savefig('output.png')

data_analysis[['reserve_days', 'coal_reserves_times_ratio', 'opp_reserves_times_ratio']].sum().to_csv('summary.csv')

data_analysis.to_csv('data_analysis.csv', encoding='utf-8-sig')
results.to_csv('results.csv')