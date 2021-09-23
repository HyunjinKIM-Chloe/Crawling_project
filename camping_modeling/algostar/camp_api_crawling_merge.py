import re
import numpy as np
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
from sklearn.preprocessing import MinMaxScaler, RobustScaler
import algo_config as config
# import camping_modeling.apis.gocamping_api as ga
# gocamping = ga.GocampingApi()
import gocamp_scrapy as gs
gs = gs.GocampCrawl()


class CampMerge:

    def __init__(self):
        self.path = config.Config.PATH
        self.api_data = config.Config.API_DATA #gocamping.gocampingAPI()
        self.crawl_data = config.Config.CRAWL_DATA  # gs.gocamp_crawler('2021-02-01','createdtime')
        self.nv_data = config.Config.NV_DATA
        self.kk_data = config.Config.KAKAO
        self.dimension = config.Config.DIMENSION

    def camp_api_preprocessing(self):

        global data

        camp_api_data = self.api_data
        camp_crawling_data = self.crawl_data
        camp_api_data['contentId'] = camp_api_data['contentId'].astype('int64')
        merge_file = pd.merge(camp_api_data, camp_crawling_data, how='left', right_on='contentId', left_on='contentId')
        data = merge_file.reset_index(drop=True)
        data['tags'] = data.tags.str.replace(' #', ',')
        data['tags'] = data.tags.str.replace('#', '')
        data['tags'] = data.tags.fillna('정보없음')

        out = []
        seen = set()
        for c in data['tags']:
            words = c.split(',')
            out.append(','.join([w for w in words if w not in seen]))
            seen.update(words)
        data['unique_tag'] = out

        df = ",".join(data.unique_tag.unique())
        df = df.split(",")

        def get_tag(i):
            dfs = data['tags'].str.contains(df[i])
            data[df[i]] = dfs.astype(int)

        for i in range(len(df)):
            get_tag(i)
        tag_data = data.iloc[:, 90:]
        tag_data = pd.concat([data.contentId, tag_data], 1)

        return tag_data

    def camp_api_data_merge(self):

        tag_data = self.camp_api_preprocessing()
        tag_data = tag_data.drop(['친절한', '재미있는', '여유있는'], 1)
        camp_data1 = data[['facltNm', 'contentId', 'insrncAt', 'trsagntNo', 'mangeDivNm', 'manageNmpr', 'sitedStnc','glampInnerFclty',
                           'caravInnerFclty', 'trlerAcmpnyAt', 'caravAcmpnyAt', 'toiletCo', 'swrmCo', 'wtrplCo', 'brazierCl', 'sbrsCl',
                           'sbrsEtc', 'posblFcltyCl', 'extshrCo', 'frprvtWrppCo', 'frprvtSandCo', 'fireSensorCo', 'animalCmgCl']]
        camp_algo_merge = pd.merge(camp_data1, tag_data, how='left', on='contentId')

        def col_count(colname):
            camp_algo_merge[f'{colname}'] = camp_algo_merge[f'{colname}'].str.count(',') + 1
            camp_algo_merge[f'{colname}'] = camp_algo_merge[f'{colname}'].fillna(0)
            camp_algo_merge[f'{colname}'] = camp_algo_merge[f'{colname}'].astype('int')

        for i in ['glampInnerFclty', 'caravInnerFclty', 'sbrsCl', 'sbrsEtc', 'posblFcltyCl']:
            col_count(i)

        camp_algo_merge = camp_algo_merge.rename(columns={'facltNm':'camp'})

        return camp_algo_merge


class ReviewPre(CampMerge):
    def __init__(self):
        super().__init__()

    def review_preprocessing(self):
        """ 카카오 데이터는 네이버 카테고리 학습 후 반영"""

        nv_data = self.nv_data
        kk_data = self.kk_data

        # naver_review_data preprocessing
        nv_data['user_info'] = nv_data['user_info'].fillna(0)
        nv_data = nv_data[nv_data['user_info'] != 0]
        nv_data['user_info'] = nv_data['user_info'].apply(lambda x: x.split('\n')[-1])
        nv_data['visit_info'] = nv_data['visit_info'].apply(lambda x: x.split('번째')[0][-1])
        nv_data = nv_data[nv_data['star'] != 'star']

        nv_data['star'] = nv_data['star'].astype('float64')
        nv_data['user_info'] = nv_data['user_info'].astype('float64')
        nv_data['visit_info'] = nv_data['visit_info'].astype('float64')
        nv_data = nv_data.drop(['addr', 'base_addr', 'user_name', 'visit_info'], 1)
        nv_data = nv_data.rename(columns={'title': 'camp', 'highlight_review': 'review', 'star': 'point', 'user_info': 'avg_point'})

        nv_data = nv_data[['camp', 'review', 'point', 'category', 'avg_point']]
        nv_data['point'] = nv_data['point'].astype('float64')
        nv_data['avg_point'] = nv_data['avg_point'].astype('float64')

        reviews_df = pd.concat([nv_data, kk_data], 0)

        # 가중치 [ point / (point / avg_point) ] * 0.01 → RobustScaler 적용
        reviews_df['weights'] = reviews_df['point'] * (reviews_df['point'] / reviews_df['avg_point'])
        reviews_df = reviews_df.reset_index(drop=True)

        rb = RobustScaler()
        rb_df = rb.fit_transform(reviews_df[['weights']])
        rb_df = pd.DataFrame(rb_df)

        rb_df = rb_df.rename(columns={0: 'weights2'})
        rb_df['weights2'] = rb_df['weights2'] * 0.01

        re_df = pd.concat([reviews_df, rb_df], 1)

        # final_point: point * (1+weights) → MinMaxScaler 적용 후 *5 (0~5 사이의 값)

        re_df['final_point'] = re_df['point'] * (1 + re_df['weights2'])

        mm = MinMaxScaler()
        mm_df = mm.fit_transform(re_df[['final_point']])
        mm_df = pd.DataFrame(mm_df)

        re_df['final_point'] = mm_df * 5
        re_df = re_df.drop(['weights', 'weights2'], 1)
        re_df['final_point'] = round(re_df['final_point'], 1)

        re_df2 = re_df.groupby(['camp', 'category']).mean().reset_index()
        re_df3 = re_df.groupby(['camp', 'category']).size().reset_index(name='count')
        re_df4 = pd.merge(re_df2, re_df3)

        return re_df4


class ReviewCamp(ReviewPre):

    def __init__(self):
        super().__init__()

    def review_camp_merge(self):
        api_data = self.camp_api_data_merge()
        df = self.review_preprocessing()
        df = df[['camp', 'category', 'final_point']]
        df = pd.pivot_table(df, index='camp', columns='category').fillna(0).reset_index()
        review_result = pd.concat([df["camp"], df["final_point"]], 1)

        camp_name = api_data[api_data.duplicated(['camp'])].camp.tolist()
        for i in camp_name:
            review_result = review_result.query(f'camp != "{i}"')
        merge_result = pd.merge(api_data, review_result, how='left', left_on='camp', right_on='camp')

        result1 = merge_result.iloc[:, 44:].fillna(0)
        result2 = merge_result.iloc[:, :44]
        algo_result = pd.concat([result2, result1], 1)
        algo_re_cols = algo_result.iloc[:, 3:].columns.tolist()
        for algo_re_col in algo_re_cols:
            col_names = self.dimension[self.dimension.colname_kor == f'{algo_re_col}']
            col_name = np.unique(col_names.colname)
            algo_result = algo_result.rename(columns={f'{algo_re_col}': f'{"".join(col_name)}'})

        return algo_result