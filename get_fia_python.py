# Load necessary Python libraries
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# The function fiadb_api_POST() gets an FIADB-API report and returns the data
# See description: https://apps.fs.usda.gov/fiadb-api/

def fiadb_api_POST(parameterDictionary):
    # make request
    resp = requests.post(r"https://apps.fs.usda.gov/fiadb-api/fullreport",data=parameterDictionary)
    # parse response to json
    data = resp.json()

    # create output dictionary and populate it with estimate data frames
    outDict = {}
    # append estimates
    outDict['estimates'] = pd.DataFrame(data['estimates'])

    # append subtotals and totals if present
    if 'subtotals' in data.keys():
        subT = {}
        for i in data['subtotals'].keys():
            subT[i] = pd.DataFrame(data['subtotals'][i])
        outDict['subtotals'] = subT
        outDict['totals'] = pd.DataFrame(data['totals'])

    # append metadata
    outDict['metadata'] = data['metadata']
    return outDict

## Example 1: Forestland area by stand age class and ownership group for Maine
# Change the values in arg_list to obtain data

# snum = All of the possible FIA variables. See https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/snum
# wc = State FIPS code/inventory year of data collections. See: https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/wc
# rselected = row estimate grouping definition. See: https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/rselected
# cselected = column estimate grouping definition. See: https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/cselected
# outputFormat = output format. (NJSON is best in R)
requestParameters = {'snum': 2,    # Area of forest land, in acres
                     'wc': 232024, # Maine, 2024
                     'rselected':'Stand age 20 yr classes (0 to 500 plus)', # Row variable
                     'cselected':'Ownership group - Major', # Column variable
                     'outputFormat':'NJSON'} # Output format

# Submit argument list to POST request function
post_data = fiadb_api_POST(parameterDictionary = requestParameters)

# Gather estimates to make data frame
forestland_me = post_data['estimates']

# Often the data frame returned from the API will need to be cleaned and organized before analysis and visualization. 
# In this case, we need to convert some variables to numeric.
# We'll also extract the age class and ownership group from the GRP1 and GRP2 variables, and select only the variables we need for analysis

forestland_me = (forestland_me  
    .assign(
        forest_area  = lambda x: pd.to_numeric(x['ESTIMATE']),
        num_plots    = lambda x: pd.to_numeric(x['PLOT_COUNT']),
        se           = lambda x: pd.to_numeric(x['SE']),
        se_percent   = lambda x: pd.to_numeric(x['SE_PERCENT']),
        var          = lambda x: pd.to_numeric(x['VARIANCE']),
        age_class    = lambda x: x['GRP1'].str[6:],        
        own_group    = lambda x: x['GRP2'].apply(lambda v: "Private" if "Private" in v else "Public")
    )
    [['age_class', 'own_group', 'forest_area', 'num_plots', 'se', 'se_percent', 'var']] 
)

print(forestland_me.head())

# Reorder age class factor levels for plotting
age_levels = [
    "0-20 years", "21-40 years", "41-60 years", "61-80 years", "81-100 years",
    "100-120 years", "121-140 years", "141-160 years", "161-180 years", 
    "181-200 years", "200-220 years"
]
# Plot forestland area by age class and ownership group in Maine
forestland_me['age_class'] = pd.Categorical(
    forestland_me['age_class'], 
    categories=age_levels, 
    ordered=True
)

own_groups = forestland_me['own_group'].unique()

fig, axes = plt.subplots(
    nrows=len(own_groups), ncols=1,
    figsize=(10, 6),
    sharey=False
)

for ax, group in zip(axes, own_groups):
    subset = (forestland_me[forestland_me['own_group'] == group]
              .sort_values('age_class'))
    
    ax.bar(subset['age_class'], subset['forest_area'])
    ax.set_title(group)
    ax.set_xlabel("Stand age class (years)")
    ax.set_ylabel("Forestland area (acres)")
    ax.tick_params(axis='x', rotation=45)
    sns.despine(ax=ax)  # cleaner look, like theme_bw()

fig.suptitle("Maine forestland area", fontsize=13, y=1.01)
plt.tight_layout()
plt.show()

## Example 2: Average volume per acre on timberlands by county and forest type group in Vermont
requestParameters = {'snum': 574175, # Sound bole wood volume of live trees (timber species at least 5 inches d.b.h.), in cubic feet, on timberland
                     'sdenom': 3, # Denominator for per acre estimates (timberland area)
                     'wc': 502024, # Vermont, 2024
                     'rselected':'Forest type group',  # Row variable
                     'cselected':'County code and name', # Column variable
                     'outputFormat':'NJSON'} # Output format

# Submit argument list to POST request function
post_data = fiadb_api_POST(parameterDictionary = requestParameters)

# Gather estimates to make data frame
volume_vt = post_data['estimates']

# Clean and organize the data frame returned from the API. 
# In this case, we need to convert some variables to numeric.
# We'll also extract the forest type group and county from the GRP1 and GRP2 variables, and select only the variables we need for analysis

volume_vt = (volume_vt  
    .assign(
        volume_ac  = lambda x: pd.to_numeric(x['RATIO_ESTIMATE']),
        num_plots  = lambda x: pd.to_numeric(x['NUMERATOR_PLOT_COUNT']),
        se         = lambda x: pd.to_numeric(x['RATIO_SE']),
        se_percent = lambda x: pd.to_numeric(x['RATIO_SE_PERCENT']),
        var        = lambda x: pd.to_numeric(x['RATIO_VAR']),
        forest_type = lambda x: x['GRP1'].str[6:],   
        county      = lambda x: x['GRP2'].str[16:] 
    )
    [['county', 'forest_type', 'num_plots', 'volume_ac', 'se', 'se_percent', 'var']]
)

print(volume_vt.head())

# Plot average volume per acre on timberlands by county and forest type group in Vermont.
# We'll filter to only include estimates based on at least 5 plots.
# We'll add error bars to show the standard error of the estimates.
plot_df = volume_vt[volume_vt['num_plots'] >= 5]

counties = sorted(plot_df['county'].unique())
n_cols = 3
n_rows = -(-len(counties) // n_cols)  # ceiling division

fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, n_rows * 4), sharey=False)
axes = axes.flatten()

for i, (ax, county) in enumerate(zip(axes, counties)):
    subset = plot_df[plot_df['county'] == county].sort_values('forest_type')
    
    colors = sns.color_palette("tab10", n_colors=len(subset))
    
    bars = ax.barh(subset['forest_type'], subset['volume_ac'], color=colors)
    
    # Error bars (geom_errorbar equivalent)
    ax.errorbar(
        x=subset['volume_ac'],
        y=subset['forest_type'],
        xerr=subset['se'],
        fmt='none',
        color='black',
        capsize=3,
        linewidth=0.8
    )
    
    ax.set_title(county, fontsize=10)
    ax.set_xlabel("Volume per acre (cubic feet)")
    ax.set_ylabel("Forest type group")
    sns.despine(ax=ax)

# Hide any unused subplots
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

fig.suptitle("Volume by forest type, Vermont\nMean +/- one SE", fontsize=13)
plt.tight_layout()
plt.show()
