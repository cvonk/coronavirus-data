import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import time
import plotly.graph_objects as go
from urllib.request import urlopen
import json

INPUT_URL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/"
df_lookup = pd.read_csv(INPUT_URL+"UID_ISO_FIPS_LookUp_Table.csv")

def transform_and_standardize(df, var_name):
    df = df.drop(columns=['Lat', 'Long']).merge(
        df_lookup.rename(columns={'Country_Region': 'Country/Region', 'Province_State': 'Province/State'})[['Country/Region', 'Province/State', 'iso3','Population']],
        how='outer',
        on=['Country/Region', 'Province/State']
    ).dropna(subset=["iso3"])
    df = df.groupby(['iso3','Country/Region']).sum().reset_index()
    df = df.melt(id_vars=[df.columns[0],df.columns[1],df.columns[-1]], 
        value_vars=df.columns[2:-1], 
        var_name='date', 
        value_name=var_name
    ).dropna()
    df['date']=pd.to_datetime(df['date'])
    return df.sort_values(by=['iso3', 'date'])

def transform_and_standardize_us(df, var_name):
    if var_name is 'deaths':
        df=df.drop(columns=['Population'])
    df = df.drop(columns=['UID','iso2','iso3','Country_Region','code3']).groupby(['FIPS','Admin2','Province_State','Lat','Long_']).sum().reset_index()
    df = df.melt(id_vars=[df.columns[0],df.columns[1],df.columns[2],df.columns[3],df.columns[4]], 
        value_vars=df.columns[5:], 
        var_name='date', 
        value_name=var_name
    ).dropna()
    df['date']=pd.to_datetime(df['date'])
    return df.sort_values(by=['FIPS', 'date'])

df_confirmed = transform_and_standardize(pd.read_csv(INPUT_URL+"csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"), 'confirmed')
df_deaths = transform_and_standardize(pd.read_csv(INPUT_URL+"csse_covid_19_time_series/time_series_covid19_deaths_global.csv"), 'deaths')
df_recovered = transform_and_standardize(pd.read_csv(INPUT_URL+"csse_covid_19_time_series/time_series_covid19_recovered_global.csv"), 'recovered')
df = df_confirmed.merge(df_deaths,how='outer',on=['date', 'iso3', 'Population','Country/Region']).merge(df_recovered,how='outer',on=['date', 'iso3', 'Population','Country/Region'])
for col in ['confirmed', 'deaths', 'recovered']:
    df[f'{col}_rate'] = (df[col]/df['Population']*100000000).astype('int64')

df_confirmed_us = transform_and_standardize_us(pd.read_csv(INPUT_URL+"csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"), 'confirmed')
df_deaths_us = transform_and_standardize_us(pd.read_csv(INPUT_URL+"csse_covid_19_time_series/time_series_covid19_deaths_US.csv"), 'deaths').drop(columns=['Lat','Long_'])
df_us=df_confirmed_us.merge(df_deaths_us,how='outer',on=['date', 'FIPS', 'Admin2','Province_State'])
df_us=df_us.merge(df_lookup[['FIPS','Population']],
                  how='outer',
                  on=['FIPS']).dropna()
df_us = df_us.astype({'FIPS':'int','confirmed':'int','deaths':'int','Population':'int'})
df_states=df_us.drop(columns=['FIPS']).groupby(['Province_State','date',]).sum().reset_index()
for col in ['confirmed', 'deaths']:
    df_states[f'{col}_rate'] = (df_states[col]/df_states['Population']*100000000).astype('int64')
    df_us[f'{col}_rate'] = (df_us[col]/df_us['Population']*100000000).astype('int64')
abbreviations={
    "Alabama": ["01", "AL"],
    "Alaska": ["02", "AK"],
    "Arizona": ["04", "AZ"],
    "Arkansas": ["05", "AR"],
    "California": ["06", "CA"],
    "Colorado": ["08", "CO"],
    "Connecticut": ["09", "CT"],
    "Delaware": ["10", "DE"],
    "District of Columbia": ["11", "DC"],
    "Florida": ["12", "FL"],
    "Georgia": ["13", "GA"],
    "Hawaii": ["15", "HI"],
    "Idaho": ["16", "ID"],
    "Illinois": ["17", "IL"],
    "Indiana": ["18", "IN"],
    "Iowa": ["19", "IA"],
    "Kansas": ["20", "KS"],
    "Kentucky": ["21", "KY"],
    "Louisiana": ["22", "LA"],
    "Maine": ["23", "ME"],
    "Maryland": ["24", "MD"],
    "Massachusetts": ["25", "MA"],
    "Michigan": ["26", "MI"],
    "Minnesota": ["27", "MN"],
    "Mississippi": ["28", "MS"],
    "Missouri": ["29", "MO"],
    "Montana": ["30", "MT"],
    "Nebraska": ["31", "NE"],
    "Nevada": ["32", "NV"],
    "New Hampshire": ["33", "NH"],
    "New Jersey": ["34", "NJ"],
    "New Mexico": ["35", "NM"],
    "New York": ["36", "NY"],
    "North Carolina": ["37", "NC"],
    "North Dakota": ["38", "ND"],
    "Ohio": ["39", "OH"],
    "Oklahoma": ["40", "OK"],
    "Oregon": ["41", "OR"],
    "Pennsylvania": ["42", "PA"],
    "Rhode Island": ["44", "RI"],
    "South Carolina": ["45", "SC"],
    "South Dakota": ["46", "SD"],
    "Tennessee": ["47", "TN"],
    "Texas": ["48", "TX"],
    "Utah": ["49", "UT"],
    "Vermont": ["50", "VT"],
    "Virginia": ["51", "VA"],
    "Washington": ["53", "WA"],
    "West Virginia": ["54", "WV"],
    "Wisconsin": ["55", "WI"],
    "Wyoming": ["56", "WY"]
}
df_states['number']=df_states['Province_State'].map(lambda x: abbreviations[x][0])
df_states['abbreviation']=df_states['Province_State'].map(lambda x: abbreviations[x][1])
df_us['number']=df_us['Province_State'].map(lambda x: abbreviations[x][0])
df_us['FIPS']=df_us['FIPS'].astype(str).str.zfill(5)
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)
df_geo=dict()
for county in counties['features']:
    area=county['properties']['STATE']
    df_geo.setdefault(area,{'type':'FeatureCollection', 'features':[]})
    df_geo[area]['features'].append(county)

data='confirmed'
scope='usa'
dates=df_us['date'].unique()
area='06'
df_geo_area=df_geo[area]

fig=go.Figure(layout={
            'paper_bgcolor':'rgba(0,0,0,0)',
            'plot_bgcolor':'rgba(0,0,0,0)',
            'margin':{'l':0,'r':0,'t':0,'b':0,'pad':0},
            'uirevision':True,
            'geo':{'uirevision':True,
                   'bgcolor':'rgba(0,0,0,0)',
                   'showcountries':True, 'countrycolor': 'white', 'countrywidth': 15,
                   'showsubunits':True, 'subunitcolor': 'white', 'subunitwidth': 1,
                   'showcoastlines': True, 'coastlinecolor': 'white', 'coastlinewidth': 15,
                   'showland':False,
                   'showlakes':False,
                   'scope':scope,
                   'showframe': False,
                   },
            'hovermode':'closest'
        })
for date_parsed in dates:
    df_by_date=df_us.query('number==@area').query('date==@date_parsed').to_dict('list')
    df_geo_area=df_geo[area]
    #fig.update_layout(title={
    #    'text':str(date_parsed)[:10],
    #    'x':0.02,
    #    'y':0.98,
    #    'yanchor':'top',
    #    'xanchor':'left',
    #    'font_size':70,
    #    'font_color':'white',
    #})

    fig.update(data=({
        'type':'scattergeo',
        'lat':df_by_date['Lat'],
        'lon':df_by_date['Long_'],
        'text':df_by_date['Admin2'],
        'customdata':["USA"]*len(df_by_date[data]),
        'marker':{
            'size':[x/100 for x in df_by_date[data]],
            'opacity':0.6,
            'sizemode':'area',
            'color':'rgb(0,0,0)',
            'line_width':0
        }
    },{
        'type':'choropleth',
        'geojson':df_geo_area,
        'locations':df_by_date['FIPS'],
        'z':df_by_date[f'{data}_rate'],
        'zmin':0,
        'zmax':1000000,
        'text':df_by_date['Admin2'],
        'customdata':["USA"]*len(df_by_date[data]),
        'autocolorscale':False,
        'marker_line_color': 'white',
        'marker_line_width': 4,
        'colorscale':[[0.0, 'rgb(255,255,255)'],
                    [1e-06, 'rgb(255,245,240)'],
                    [1e-05, 'rgb(254,224,210)'],
                    [3.2e-05, 'rgb(252,187,161)'],
                    [0.0001, 'rgb(252,146,114)'],
                    [0.00032, 'rgb(251,106,74)'],
                    [0.001, 'rgb(239,59,44)'],
                    [0.01, 'rgb(203,24,29)'],
                    [0.1, 'rgb(165,15,21)'],
                    [1.0, 'rgb(103,0,13)']],
        'showscale':False
    }))
    fig.add_annotation({
        'text':'Map: Johan Vonk; Data: JHU',
        'x':0.98,
        'y':0.02,
        'yanchor':'bottom',
        'xanchor':'right',
        'font_size':30,
        'font_color':'white',
    })
    fig.update_geos(fitbounds="geojson")
    name=f"img/{str(date_parsed)[:10]}.png"
    fig.write_image(name, width=3840, height=2160)
    print(name)