import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import math
import json

### 基础处理函数
def clean_portfolio(portfolio):
    portfolio['duration_hour'] = portfolio['duration']*24
    portfolio = portfolio.rename(columns={'id':'offerid', 'duration':'duration_day'})
    
    portfolio['email'] = [int('email' in l) for l in portfolio.channels.values]
    portfolio['mobile'] = [int('mobile' in l) for l in portfolio.channels.values]
    portfolio['web'] = [int('web' in l) for l in portfolio.channels.values]
    portfolio['social'] = [int('social' in l) for l in portfolio.channels.values]
    portfolio = portfolio.drop('channels',axis=1)
    portfolio = portfolio.reset_index()
    return portfolio

def clean_profile(profile):  
    profile = profile.rename(columns={'id':'cid'})
    
    # 有2000多个年龄异常(118岁)，这部分用户没有收入和性别信息，剔除
    profile = profile.query("age<=100")
    profile['became_member_month'] = profile['became_member_on'].astype(str).apply(lambda x: x[4:6]).astype(int)
    
    # 加字段
    profile['became_member_year'] = profile['became_member_on'].astype(str).apply(lambda x: x[:4]).astype(int)
    profile['became_member_year'] = pd.cut(profile['became_member_year'], bins=[2012,2015,2017,2018])
    profile['age_range'] = pd.cut(profile['age'], bins=[17,35,55,75,100])
    profile['income'] = profile['income']/1000
    profile['income_range'] = pd.cut(profile['income'], bins=[29,45,60,75,90,120])
    
    return profile


def draw_hist_pics(profile1, cols=[], hue='gender'):
    for i,col in enumerate(profile1[cols].columns):
        if col != hue:
            g = sns.FacetGrid(profile1[cols], size = 3,aspect = 1.5, hue = hue,palette='deep'\
                              ,hue_order= sorted(profile1[hue].unique()))
            g.map(plt.hist,col,alpha=0.6)
            plt.title('Distribution of '+ col)
            plt.axvline(profile1.query("gender == 'F'")[col].mean(), c='b')
            plt.axvline(profile1.query("gender == 'M'")[col].mean(), c='orange')
            g.add_legend()
            plt.show();



### 整合表的函数
def parse_offer(value):  
    if 'offer id' in value.keys():
        value = value['offer id']
    elif 'offer_id' in value.keys():
        value = value['offer_id']
    else:
        value = None           
    return  value

def sep_df(transcript,  portfolio):
    
    transcript['offer'] = transcript.value.apply(lambda v : parse_offer(v))
    transcript['amount'] = transcript.value.apply(lambda x : x['amount'] if 'amount' in x.keys() else np.nan)
    
    received = transcript.query("event == 'offer received'")\
                        .rename(columns={'time':'received_time','offer':'received_offer', 'person':'cid'})\
                        .drop(['value','event','amount'],axis=1)
    
    received = pd.merge(received, portfolio, how='left', left_on='received_offer', right_on='offerid')\
                 .drop(['offerid'], axis=1)

    viewed = transcript.query("event == 'offer viewed'")\
                        .rename(columns={'time':'viewed_time','offer':'viewed_offer','person':'cid'})\
                        .drop(['value','event','amount'],axis=1)
    
    transaction = transcript.query("event == 'transaction'")\
                                .rename(columns={'time':'transaction_time','person':'cid'})\
                                .drop(['value','event','offer'],axis=1)
    
    # 完成offer的记录存在少数重复，做去重处理
    completed = transcript.query("event == 'offer completed'")\
                            .rename(columns={'time':'completed_time','offer':'completed_offer','person':'cid'})\
                            .drop(['value','event','amount'],axis=1).drop_duplicates()
    
    completed = pd.merge(completed,transaction,how='left',left_on=['cid','completed_time'],\
                         right_on=['cid','transaction_time']).drop(['completed_time'],axis=1)
    
    #收到offer的用户和交易人数取交集,使计算响应率时基于的用户群一致
    received = received[received.cid.isin(transaction.cid.unique())]
    transaction = transaction[transaction.cid.isin(received.cid.unique())]
    
    return received, viewed,  completed, transaction


def is_valid_viewed(row):
    # 判断是否为有效浏览：offer浏览时间在收到时间之后，并且offer在有效期内
    view_hour_after_receive = row.viewed_time - row.received_time
    
    if view_hour_after_receive <= row.duration_hour and view_hour_after_receive>=0:            
        return 1
    else:
        return 0

def is_valid_comp(row):
    # 判断消费是否受到offer影响：offer在有效期内，offer交易时间在浏览时间之后，并且消费金额满足offer最低消费限制
    trans_hour_after_receive = row.transaction_time - row.received_time
    
    if trans_hour_after_receive <= row.duration_hour and trans_hour_after_receive>=0 \
        and row.transaction_time>=row.viewed_time and row.amount>=row.difficulty:            
        return 1
    else:
        return 0


        
def clean_received_other(received_other, viewed,completed):
    # 保留满足条件的浏览记录
    received_other_view = pd.merge(received_other,viewed,  how='left', left_on=['cid','received_offer'],\
                right_on=['cid','viewed_offer']).drop('viewed_offer',axis=1)
    received_other_view['is_valid_viewed'] = received_other_view .apply(lambda row: is_valid_viewed(row), axis=1)

    # 同一个cid、offer和offer接收时间后续有多次浏览的，只将后续最近一次浏览算作对该offer的浏览
    received_other_view = received_other_view.query("is_valid_viewed==1")
    received_other_view = received_other_view.assign(view_rn = received_other_view\
                                                            .sort_values(by=['viewed_time'], ascending=True)\
                                             .groupby(['cid','received_offer','received_time'])\
                                             .cumcount()+1)
    received_other_view = received_other_view.query("view_rn==1").reset_index().drop('index',axis=1)
    
    
    # 保留满足条件的交易记录，根据用户和completed_offer连接
    received_other_view_comp = pd.merge(received_other_view,completed, how='left', left_on=['cid','received_offer'],\
                            right_on=['cid','completed_offer']).drop('completed_offer',axis=1)
    received_other_view_comp['is_valid_comp'] = received_other_view_comp.apply(lambda row: is_valid_comp(row), axis=1)
    received_other_view_comp = received_other_view_comp.query("is_valid_comp==1")
    
    # 同一个cid、offer和offer接收时间后续有多次交易的，只将后续最近一次交易算作对该offer的最终响应
    received_other_view_comp = received_other_view_comp.assign(comp_rn = received_other_view_comp\
                                         .sort_values(by=['transaction_time'], ascending=True)\
                                         .groupby(['cid','received_offer','received_time','viewed_time'])\
                                         .cumcount()+1)
    received_other_view_comp = received_other_view_comp.query("comp_rn==1").reset_index()\
                                                        .drop(['index'],axis=1)
    
    
    return received_other_view, received_other_view_comp


def clean_received_info(received_info, viewed,transaction):
    
    # 保留满足条件的浏览记录
    received_info_view = pd.merge(received_info,viewed,  how='left', left_on=['cid','received_offer'],\
                right_on=['cid','viewed_offer']).drop('viewed_offer',axis=1)
    received_info_view['is_valid_viewed'] = received_info_view .apply(lambda row: is_valid_viewed(row), axis=1)
    received_info_view = received_info_view.query("is_valid_viewed==1")

    # 同一个cid、offer和offer接收时间后续有多次浏览的，只将后续最近一次浏览算作对该offer的浏览
    received_info_view = received_info_view.assign(view_rn = received_info_view\
                                                            .sort_values(by=['viewed_time'], ascending=True)\
                                             .groupby(['cid','received_offer','received_time'])\
                                             .cumcount()+1)
    received_info_view = received_info_view.query("view_rn==1").reset_index().drop('index',axis=1)
    
    # 保留满足条件的交易记录，根据用户连接
    received_info_view_comp = pd.merge(received_info_view,transaction,how='left',on='cid')
    received_info_view_comp['is_valid_comp'] = received_info_view_comp.apply(lambda row: is_valid_comp(row), axis=1)
    received_info_view_comp = received_info_view_comp.query("is_valid_comp==1")

    # 同一个cid、offer和offer接收时间后续有多次交易的，只将后续最近一次交易算作对该offer的最终响应
    received_info_view_comp = received_info_view_comp.assign(comp_rn = received_info_view_comp\
                                             .sort_values(by=['transaction_time'], ascending=True)\
                                             .groupby(['cid','received_offer','received_time','viewed_time'])\
                                             .cumcount()+1)
    received_info_view_comp = received_info_view_comp.query("comp_rn==1").reset_index().drop('index',axis=1)
    
    
    return received_info_view, received_info_view_comp


def clean_response(received,viewed,completed,transaction,received_info,received_other):

    received_other_view, received_other_view_comp = clean_received_other(received_other,viewed,completed)
    received_info_view, received_info_view_comp = clean_received_info(received_info,viewed,transaction)
    
    # 整合看过的offer和完成的(响应的)offer
    received_view = pd.concat([received_other_view, received_info_view], ignore_index=True)
    received_view_comp = pd.concat([received_other_view_comp,received_info_view_comp], ignore_index=True)
    
    # offer响应记录和交易记录结合
    response1 = received_view_comp[['cid','received_time','received_offer','reward',\
                               'viewed_time','transaction_time','amount','is_valid_comp',\
                            'offeridx','difficulty','duration_day','offer_type','duration_hour',\
                                    'email','mobile','web','social']]
    transaction_response = pd.merge(transaction,response1,how='left',on=['cid','transaction_time','amount'])
    
    # 发现存在一个交易同时受到多种offer影响的情况
    # 比如cid==f1bcf3081d46456696400dce6ca36e11，在transaction_time=504的时候，满足三种offer条件
    transaction_response = transaction_response.assign(reward_rn = transaction_response\
                                         .sort_values(by=['reward'], ascending=False)\
                                         .groupby(['cid','transaction_time','amount'])\
                                         .cumcount()+1) 
    
    # 假设业务逻辑是一次只能使用一种优惠，这里选择reward最高的作为交易响应的offer
    transaction_response = transaction_response.query("reward_rn==1").reset_index().drop('index',axis=1)
    transaction_response['is_offer'] = transaction_response.is_valid_comp.fillna(0).astype(int)
    transaction_response = transaction_response.drop(['is_valid_comp','reward_rn'],axis=1)
    
    
    # 最终offer响应记录，以及和接收offer的记录结合
    response = transaction_response[['cid','received_time','received_offer',\
                               'viewed_time','transaction_time','amount','is_offer']]\
                                .query("is_offer==1").rename(columns={'is_offer':'is_response'})
                            
    received_response = pd.merge(received, response,\
                                 how='left',on=['cid','received_time','received_offer'])
    
    received_response['is_response'] = received_response.is_response.fillna(0).astype(int)

    
    
    # 输出：
    # 1.接收-offer浏览联合表
    # 2.接收-offer浏览且完成联合表
    # 3.交易-offer响应联合表 ** 重要
    # 4.offer响应记录表
    # 5.接收-offer响应联合表 ** 重要
    return received_view, received_view_comp, transaction_response, response, received_response



def clean_cid_stats(received_response_cid, transaction_response_cid):
    received_response_cid1 = received_response_cid.join(pd.get_dummies(received_response_cid['offer_type']))
    
    cid_group1 = received_response_cid1.groupby("cid")
    cid_group2 = received_response_cid1.query("is_response==1").groupby("cid")
    cid_group3 = transaction_response_cid.groupby(["cid"])
    
    # 用户接收offer的统计
    cid_stats1 =  cid_group1.agg({'received_time':'count',
                'bogo':np.sum,
                'discount':np.sum,
                'informational':np.sum,
                'social':np.sum,
                'difficulty':[np.min,np.max,np.mean]
                 })
    cid_stats1.columns = ['_rece_'.join(col).strip() for col in cid_stats1.columns.values]
    
    # 用户响应offer的统计
    cid_stats2 = cid_group2.agg({'bogo':np.sum,
                    'discount':np.sum,
                    'informational':np.sum,
                    'social':np.sum,
                    'difficulty':[np.min,np.max,np.mean],
                    'amount':[np.min, np.max,np.mean,np.sum]
                     })

    cid_stats2.columns = ['_offer_'.join(col).strip() for col in cid_stats2.columns.values]
    
    #用户交易的统计，包括响应offer的交易统计
    cid_stats3 = cid_group3.agg({'amount':[np.min, np.max,np.mean,np.sum],
                               'transaction_time':'count',
                               'is_offer':'sum',
                            })
    cid_stats3.columns = ['_tr_'.join(col).strip() for col in cid_stats3.columns.values]
    
    cid_stats = cid_stats3.join(cid_stats2).join(cid_stats1).reset_index()
    return cid_stats


### 以下为特征处理类函数

def calc_ratio(df, col1, col2, new_ratio_col):
    df[new_ratio_col] = df[col1]/df[col2]
    return df

def add_feature_cols(cid_with_offer):
    # offer交易次数占比，衡量用户总体的活动偏好水平
    col1 = 'is_offer_tr_sum'
    col2 = 'transaction_time_tr_count'
    new_racio_col = 'offer_count_ratio'
    cid_with_offer = calc_ratio( cid_with_offer, col1, col2, new_racio_col)
    
    # offer交易金额占比，衡量用户总体的活动偏好水平
    col1 = 'amount_offer_sum'
    col2 = 'amount_tr_sum'
    new_racio_col = 'offer_amount_ratio'
    cid_with_offer = calc_ratio( cid_with_offer, col1, col2, new_racio_col)
    
    # bogo offer交易次数占总offer次数比例，衡量用户bogo类活动偏好水平
    col1 = 'bogo_offer_sum'
    col2 = 'is_offer_tr_sum'
    new_racio_col = 'bogo_offer_ratio'
    cid_with_offer = calc_ratio( cid_with_offer, col1, col2, new_racio_col)
    
    # discount offer交易次数占总offer次数比例，衡量用户discount类活动偏好水平
    col1 = 'discount_offer_sum'
    col2 = 'is_offer_tr_sum'
    new_racio_col = 'discount_offer_ratio'
    cid_with_offer = calc_ratio( cid_with_offer, col1, col2, new_racio_col)

    # informational offer交易次数占总offer次数比例，衡量用户informational活动偏好水平
    col1 = 'informational_offer_sum'
    col2 = 'is_offer_tr_sum'
    new_racio_col = 'informational_offer_ratio'
    cid_with_offer = calc_ratio( cid_with_offer, col1, col2, new_racio_col)

    # social offer交易次数占总offer次数比例，衡量用户social活动偏好水平
    col1 = 'social_offer_sum'
    col2 = 'is_offer_tr_sum'
    new_racio_col = 'social_offer_ratio'
    cid_with_offer = calc_ratio( cid_with_offer, col1, col2, new_racio_col)

    # 最高offer difficulty与最高offer交易金额的比例，衡量用户对最高difficulty的敏感度，当大于0时，该比例越高，说明对difficulty越敏感
    # difficulty敏感度主要针对 discount和bogo两类活动，所以等于0时表示用户没有参与这两类活动
    col1 = 'difficulty_offer_amax'
    col2 = 'amount_offer_amax'
    new_racio_col = 'difficulty_offer_ratio'
    cid_with_offer = calc_ratio( cid_with_offer, col1, col2, new_racio_col)
    
    return cid_with_offer


### 查看用户群特征
def find_cid_groups(df, feature_groups, metric, condition='==1'):
    col_like = df.query("{0}{1}".format(metric,condition)).groupby(feature_groups)\
                        .agg({metric:['count'],
                              'amount_tr_mean':['mean'],
                              'transaction_time_tr_count':['mean']
                             })
    
    col_like.columns = ['count','tr_amount_mean','tr_count_mean']
    
    col_like_cid_groups = col_like.sort_values(by=['count','tr_count_mean','tr_amount_mean'],ascending=False)\
                                    .reset_index().head(10)
    
    print(col_like.groupby('gender')['count'].sum(), "\n",\
            col_like.groupby('age_range')['count'].sum(), "\n",\
            col_like.groupby('income_range')['count'].sum(), "\n",\
            col_like.groupby('became_member_year')['count'].sum(),"\n",\
         )
    
    return col_like,col_like_cid_groups
