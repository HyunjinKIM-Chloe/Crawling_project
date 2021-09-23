import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
import camping_modeling.config as config
from urllib.request import Request, urlopen
import xmltodict
import json
from pandas import json_normalize


class GocampingApi:
    def __init__(self):
        # self.secretKey = config['API_KEYS']['PUBLIC_API_KEY']
        self.secretKey = config.Config.PUBLIC_API_KEY

    def gocampingAPI(self):
        url = 'http://api.visitkorea.or.kr/openapi/service/rest/GoCamping/basedList?'
        param = 'ServiceKey='+self.secretKey+'&MobileOS=ETC&MobileApp=AppTest&numOfRows=4000'

        request = Request(url+param)
        request.get_method = lambda: 'GET'
        response = urlopen(request)
        rescode = response.getcode()

        if rescode == 200:
            responseData = response.read()
            rD = xmltodict.parse(responseData)
            rDJ = json.dumps(rD)
            rDD = json.loads(rDJ)

            camp_api_df = json_normalize(rDD['response']['body']['items']['item'])
            camp_api_df.to_csv(config.Config.PATH + "gocampapi_test.csv", encoding='utf-8-sig')
            return camp_api_df

if __name__ == '__main__':
    ga = GocampingApi()
    ga.gocampingAPI()