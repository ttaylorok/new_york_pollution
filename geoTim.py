import fiona
import shapely
from shapely.geometry import asShape
import pandas as pd

def load_geojson(filename):
    '''
    reads geojson file
    '''
    fin = fiona.open(filename,'r')
    features = []
    for rec in fin:
        rec['properties'] = dict(rec['properties'])
        features.append(rec)
    fin.close()
    return {'type' : 'FeatureCollection', 'features' : features}
    

def transform_geojson(geojson, transformer):
    '''
    transforms geojson file
    '''
    transformed_features = []
    for f in geojson['features']:
        #print(f)
        if f['geometry']['type'] == 'MultiPolygon':
            for m in np.arange(len(f['geometry']['coordinates'])):
                for p in np.arange(len(f['geometry']['coordinates'][m])):
                    for c in np.arange(len(f['geometry']['coordinates'][m][p])):
                        #print(*f['geometry']['coordinates'][p][c])
                        x, y = transformer.transform(*f['geometry']['coordinates'][m][p][c])
                        f['geometry']['coordinates'][m][p][c] = (y, x)
            transformed_features.append(f)
        elif f['geometry']['type'] == 'Polygon':
            for p in np.arange(len(f['geometry']['coordinates'])):
                for c in np.arange(len(f['geometry']['coordinates'][p])):
                    #print(*f['geometry']['coordinates'][p][c])
                    x, y = transformer.transform(*f['geometry']['coordinates'][p][c])
                    f['geometry']['coordinates'][p][c] = (y, x)
            transformed_features.append(f)
    return {'type' : 'FeatureCollection', 'features' : transformed_features}

def get_property(json_in, property_name):
    properties = []
    for f in json_in['features']:
        properties.append(f['properties'][property_name])
    return properties

def geojson_to_df(geojson):
    df1 = pd.DataFrame(geojson['features'])
    df2 = pd.json_normalize(df1['properties'])
    df3 = df1['geometry'].apply(lambda x : asShape(x))
    return pd.concat([df2, df3], axis = 1)


def df_to_geojson(df):
    features = []
    for row in df.iterrows():
        r = row[1]
        properties = dict(r[r.index != 'geometry'])
        features.append({'type' : 'Feature',
                         'properties' : properties,
                         'geometry' : shapely.geometry.mapping(r['geometry'])})
    return {'type' : 'FeatureCollection', 'features' : features}

def transform_multi(project, x):
    '''
    fixes problems when trying to transform multipolygons
    '''
    if x.geom_type == 'MultiPolygon':
        gs = []
        for g in x.geoms:
            gs.append(transform(project,g))
        return MultiPolygon(gs)
    else:
        return transform(project,x)