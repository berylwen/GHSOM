import numpy as np
import pandas as pd
from pandas import ExcelWriter
#import openpyxl
#from pymongo import MongoClient
import argparse
import get_ghsom_dim

parser = argparse.ArgumentParser(description='manual to this script')
parser.add_argument('--name', type=str, default = None)

# parser.add_argument('--index', type=str, default = None)
args = parser.parse_args()

prefix = args.name
print('prefix=' + prefix)
source_path =prefix.replace('-item-seq','')

layers,max_layer,number_of_digits = get_ghsom_dim.layers(prefix)
# read source file to get data attribute
df_source =  pd.read_csv('./raw-data/%s.csv' % prefix, encoding='utf-8')
#df_source = pd.read_csv('./applications/%s/data/%s_raw.csv' % (prefix,prefix), low_memory=False)   #if with disease
median = df_source.median(axis=1)
df_source['median'] = median
print(df_source['median'])
df_source['clustered_label'] = np.nan
df_source['x_label'] = np.nan  ####
df_source['y_label'] = np.nan  ####
df_source['x_y_label'] = np.nan  ####

print(df_source)

# get cluster start flag

def get_cluster_flag(text_file):
    get_cluster_flag = [i for i, x in enumerate(text_file) if x == '$POS_X']
    get_cluster_flag.append(len(text_file)+1)
    return get_cluster_flag


def format_cluster_info_to_dict(unit_file_name, source_data, saved_data_type=None, structure_type=None, parent_name=None, parent_file_position=None, parent_clustered_string=None, x_clustered_string=None, y_clustered_string=None,x_y_clustered_string=None):
    Groups_info = []
    
    layer_index = 1
    # read .unit file as python list
    unit_file_path = ('./applications/%s/GHSOM/output/%s/' % (source_path,prefix)) + unit_file_name + '.unit'
    print(unit_file_path)
    text_file = open(unit_file_path).read().split()
    # get file secation flag
    flag = get_cluster_flag(text_file)

    # get layer index
    if 'lvl' in unit_file_name:
        layer_index = int(unit_file_name.split('lvl')[1][0])
    else:
        layer_index = 1
    
    #get current file map x,y size
    map_size_x = int(text_file[text_file.index('$XDIM')+1])
    map_size_y = int(text_file[text_file.index('$YDIM')+1])

    # get current file map total size
    map_size = map_size_x * map_size_y

    # check parent node name
    if parent_name == None:
        parent_name = 'Root'
    else:
        parent_name = str(parent_name) + '-' + str(parent_file_position)

    # create clustered x,y string  ####
    if x_clustered_string == None:
        x_clustered_string = ''
    if y_clustered_string == None:
        y_clustered_string = ''
    if x_y_clustered_string == None:
        x_y_clustered_string = ''    

    # create clustered string 
    if parent_clustered_string == None:
        parent_clustered_string = '0.'

    # get current and next index of flag (section by section)
    for i, map_index in zip(range(len(flag)-1), range(map_size)):

        # set section index, get current section range in list
        start_index = flag[i]
        end_index = flag[i+1]
        currentSection = text_file[flag[i]:flag[i+1]]
  
        #print(currentSection)
        # use POST_X and POST_Y to create group name
        x_position = currentSection[currentSection.index('$POS_X')+1]  ####
        y_position = currentSection[currentSection.index('$POS_Y')+1]  ####
        
        group_position = currentSection[currentSection.index(
            '$POS_X')+1] + currentSection[currentSection.index('$POS_Y')+1]
        
        group_data_index = currentSection[currentSection.index(
            '$MAPPED_VECS')+1:currentSection.index('$MAPPED_VECS_DIST')] if '$MAPPED_VECS' in currentSection else []
        
        # get submap file name ,None if there is no submap
        sub_map_file_name = currentSection[currentSection.index(
            '$URL_MAPPED_SOMS')+1] if '$URL_MAPPED_SOMS' in currentSection else 'None'
        # print('Sub map name:',sub_map_file_name)

        map_index_int = map_index+1
        
        digit = 1
        while True:
            if (map_index_int // 10) != 0:
                digit = digit + 1 
                map_index_int = map_index_int // 10
            else:
                break
        # parent_clustered_string = '0.'
        zero =''
        for i in range(number_of_digits[layer_index-1]-digit):
            zero = zero + '0'            
            
        # create cluster string by map index  ####
        x_string = str(x_clustered_string) + '-' + str(x_position)
        y_string = str(y_clustered_string) + '-' + str(y_position)
        x_y_string = str(x_y_clustered_string) + '-' + str(x_position) + 'x' + str(y_position)

        
        cluster_string = str(parent_clustered_string) + zero + str(map_index+1)

        # use group_data_index to get ratio static number
        index = np.array(group_data_index, dtype='int64')
        # print(index)
        current_group_source = df_source.iloc[index, :]

        # get rid of -1(no value) -1 (infinite value)
        current_group_statistic_info = current_group_source.describe().to_dict()

        # if children exist then call function again
        if sub_map_file_name != 'None': 
            format_cluster_info_to_dict(sub_map_file_name, source_data, saved_data_type, structure_type, unit_file_name, group_position, cluster_string, x_string, y_string, x_y_string)  ####
            leaf_node = 0
        else:
            leaf_node = 1
            # if current cluster is leaf node then insert label
            # df_source.iloc[index, :]['clustered_label'] = cluster_string
            df_source.at[index, 'clustered_label'] = cluster_string
            df_source.at[index, 'x_label'] = x_string  ####
            df_source.at[index, 'y_label'] =  y_string  ####
            df_source.at[index, 'x_y_label'] =  x_y_string  ####

            

        # format data base on different visualization ways
        if str(saved_data_type) == 'tree_structure':
            structure = {}
            structure['name'] = unit_file_name + '-' + group_position
            structure['parent'] = parent_name
            if sub_map_file_name != 'None':
                structure['children'] = sub_map_info

        elif str(saved_data_type) == 'result_detail':
            structure = {
                'name': unit_file_name,
                'group_position': group_position,
                'parent_name': parent_name,
                'sub_map_file_name': sub_map_file_name,
                'leaf_node_or_note': leaf_node,
                'statistic_info': current_group_statistic_info,
                'group_data_index': group_data_index,
                'cluster_string': cluster_string
            }

            if str(structure_type) == 'flat':
                # create dictionary for store into mongodb
                Groups_info.append(structure)

    return Groups_info


def get_map_pos(text_file):
    cluster_pos_X_index = [i for i, x in enumerate(text_file) if x == '$POS_X']
    cluster_pos_Y_index = [i for i, x in enumerate(text_file) if x == '$POS_Y']

    pos_X = []
    for i in cluster_pos_X_index:
        pos_X.append(text_file[i+1])

    pos_Y = []
    for i in cluster_pos_Y_index:
        pos_Y.append(text_file[i+1])

    # create column name (as key)
    column_name = []
    for i in range(len(pos_X)):
        name = pos_X[i] + '_' + pos_Y[i]
        column_name.append(name)

    column_position_dict = {'group_position': column_name}

    return column_position_dict


# connect to mongoDB
#client = MongoClient()
#db = client['result']

Groups_info_flat = []
saved_file_type = 'result_detail'
#saved_file_type = 'tree_structure'
result = format_cluster_info_to_dict(
    prefix, df_source, saved_file_type, 'flat')


result_frame = pd.DataFrame(result)
# print(Groups_info_flat)

df_source.to_csv('./applications/%s/data/%s_with_clustered_label.csv' % (source_path, prefix), index=False)
