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
    
def transform_geos(df1, df2, id1, id2, col2, mode):
    '''
    col2: column to transform
    mode: 
        mean is area weighted mean
        sum is sum??
    '''
    overlap = []
    for row1 in df1.iterrows():
        geo1 = row1[1]['geometry']
        #print(row_cd[1]['BoroCD'])
        for row2 in df2.iterrows():
            geo2 = row2[1]['geometry']
            i = geo1.intersection(geo2)
            #print(i)
            if not i.is_empty:
                #print(i.area)
                overlap.append({id1 : row1[1][id1],
                                id2 : row2[1][id2],
                                'area_overlap' : i.area,
                                'geo2_area' : geo2.area,
                                col2 : row2[1][col2]})
    df_overlap = pd.DataFrame(overlap, columns = [id1, id2, 'area_overlap', 'geo2_area', col2])
    if mode == 'mean':
        df_overlap['total_overlap'] = df_overlap.groupby(id1)['area_overlap'].transform(sum)
        df_overlap['percentage'] = df_overlap['area_overlap']/df_overlap['total_overlap']
        partial = 'partial_' + col2
        df_overlap[partial] = df_overlap[col2] * df_overlap['percentage']
        df_out = pd.DataFrame(df_overlap.groupby(id1)[partial].sum()).reset_index()
        df_out.rename(columns = {partial : col2}, inplace = True)
        return df_out
    elif mode == 'sum':
        df_overlap['partial'] = (df_overlap['area_overlap'] / df_overlap['geo2_area']) * df_overlap[col2]
        df_out = pd.DataFrame(df_overlap.groupby(id1)['partial'].sum()).reset_index()
        df_out.rename(columns = {'partial' : col2}, inplace = True)
        return df_out
    else:
        raise Exception("Mode must be 'mean' or 'sum'.")