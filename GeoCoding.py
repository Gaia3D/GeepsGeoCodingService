#-*- coding: utf-8 -*-
from flask import Flask
from flask import request
from flask import Response
from flask import render_template
import urllib2
import json
from threading import Thread
from pyproj import Proj
from math import sqrt
import logging

# 로깅 모드 설정
logging.basicConfig(level=logging.INFO)

# 로깅 형식 지정
# http://gyus.me/?p=418
logger = logging.getLogger("failLogger")
formatter = logging.Formatter('[%(levelname)s] %(asctime)s > %(message)s')
fileHandler = logging.FileHandler("/temp/GeoCoding.log")
streamHandler = logging.StreamHandler()
fileHandler.setFormatter(formatter)
streamHandler.setFormatter(formatter)
logger.addHandler(fileHandler)
logger.addHandler(streamHandler)


#import chardet

# 한글로 된 인자들을 받을때 오류가 생기지 않게 기본 문자열을 utf-8로 지정
# http://libsora.so/posts/python-hangul/
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


app = Flask(__name__)


# 전역변수
gSourceList = ['auto', 'vworld', 'vworld_new', 'daum', 'naver', 'google']
gOutputList = ['json']
gCrsList = ['epsg:4326', 'epsg:5173', 'epsg:5174', 'epsg:5175', 'epsg:5176', 'epsg:5177', 'epsg:5178', 'epsg:5179',
            'epsg:5180', 'epsg:5181', 'epsg:5182', 'epsg:5183', 'epsg:5184', 'epsg:5185', 'epsg:5186', 'epsg:5187',
            'epsg:5188', 'epsg:3857', 'epsg:900913', 'epsg:32651', 'epsg:32652']

gKeyIndexDict = dict()
gQueryDict = dict()
gResFilterDict = dict()
gFieldXDict = dict()
gFieldYDict = dict()
gFieldAddressDict = dict()

# 키 정보들은 별도 파일에서 불러옴
from KeyFile import *
"""
# 보안을 위해 키 파일을 분리하여 git에 올라기지 않도록 함
gKeyListDict = dict()
gKeyListDict['vworld'] = ['********-****-*********-************']
gKeyListDict['vworld_new'] = gKeyListDict['vworld']
gKeyListDict['daum'] = ['********************************']
gKeyListDict['naver'] = ['********************************']
gKeyListDict['google'] = ['']
"""

gKeyIndexDict['vworld'] = 0
gQueryDict['vworld'] = "http://apis.vworld.kr/jibun2coord.do?q={q}&apiKey={key}&domain=http://175.116.155.143&output=json&epsg=4326"
gResFilterDict['vworld'] = "[dic]"
gFieldXDict['vworld'] = "item['EPSG_4326_X']"
gFieldYDict['vworld'] = "item['EPSG_4326_Y']"
gFieldAddressDict['vworld'] = "item['JUSO']"

gKeyIndexDict['vworld_new'] = 0
gQueryDict['vworld_new'] = "http://apis.vworld.kr/new2coord.do?q={q}&apiKey={key}&domain=http://175.116.155.143&output=json&epsg=4326"
gResFilterDict['vworld_new'] = "[dic]"
gFieldXDict['vworld_new'] = "item['EPSG_4326_X']"
gFieldYDict['vworld_new'] = "item['EPSG_4326_Y']"
gFieldAddressDict['vworld_new'] = "item['JUSO']"

gKeyIndexDict['daum'] = 0
gQueryDict['daum'] = "https://apis.daum.net/local/geo/addr2coord?output=json&apikey={key}&q={q}"
gResFilterDict['daum'] = "dic['channel']['item']"
gFieldXDict['daum'] = "item['lng']"
gFieldYDict['daum'] = "item['lat']"
gFieldAddressDict['daum'] = "item['title']"

gKeyIndexDict['naver'] = 0
gQueryDict['naver'] = "http://openapi.map.naver.com/api/geocode.php?output=json&encording=utf-8&key={key}&encoding=utf-8&coord=latlng&query={q}"
gResFilterDict['naver'] = "dic['item']"
gFieldXDict['naver'] = "item['point']['x']"
gFieldYDict['naver'] = "item['point']['y']"
gFieldAddressDict['naver'] = "item['address']"

gKeyIndexDict['google'] = 0
gQueryDict['google'] = "http://maps.googleapis.com/maps/api/geocode/json?address={q}"
gResFilterDict['google'] = "dic['results']"
gFieldXDict['google'] = "item['geometry']['location']['lng']"
gFieldYDict['google'] = "item['geometry']['location']['lat']"
gFieldAddressDict['google'] = "item['formatted_address']"

# 거리 계산을 위한 좌표계
gProj5179 = Proj(init='epsg:5179')


@app.route("/geocoding/service_page", methods=['GET'])
def service_page():
    return render_template("service_page.html")


@app.route("/geocoding/capabilities", methods=['GET'])
def getcapabilities():
    capabilities = {
        "sources": gSourceList,
        "outputs": gOutputList,
        "projections": gCrsList
    }
    return make_response(capabilities)


# 실제 GeoCoding 서비스
@app.route("/geocoding/api", methods=['GET'])
def geo_coding():
    try:
        q = request.args.get('q', None)
        source = request.args.get('source', 'auto').lower()
        output = request.args.get('output', 'json').lower()
        crs = request.args.get('crs', 'epsg:4326').lower()

        # TODO: 입력 주소의 정제가 필요

        # 인자 검사
        if not q:
            raise Exception("'q' argument is necessary.")

        if source not in gSourceList:
            raise Exception("invalid 'source' argument: {}.".format(source))

        if output not in gOutputList:
            raise Exception("invalid 'output' argument: {}.".format(output))

        if crs not in gCrsList:
            raise Exception("invalid 'crs' argument: {}.".format(crs))

        # q 인자의 코드페이지 판단
        # http://egloos.zum.com/mcchae/v/10726217
        # http://stackoverflow.com/questions/4239666/getting-bytes-from-unicode-string-in-python
        """
        chars = q.encode()
        char_detect = chardet.detect(chars)
        # 하지만 EUC-KR도 99% 확률로 UTF-8로 나와 좌절.
        # q2 = unicode(chars, 'euc-kr').encode('utf-8')
        detect_res = '[CHARDET] Encoding: {}, Confidence: {}'\
            .format(char_detect['encoding'], char_detect['confidence']*100)
        print detect_res
        """

        # 각 서비스의 조회 결과 담을 리스트
        result = list()

        # auto의 경우 여러 서비스에 동시 문의
        # TODO: 병렬처리 안되어 성능 심각
        if source == "auto":
            # 쓰레드 이용하여 동시 호출: 네트워크 타임에서의 동시처리를 기대하지만 GIL 때문에 될지...
            th1 = Thread(query(q, 'vworld', result))
            th2 = Thread(query(q, 'vworld_new', result))
            th3 = Thread(query(q, 'daum', result))
            th4 = Thread(query(q, 'naver', result))

            th1.start()
            th2.start()
            th3.start()
            th4.start()
            th1.join()
            th2.join()
            th3.join()
            th4.join()

            # 모두 실패한 경우 조회허용수가 얼마 안되는 구글신에 문의
            if len(result) < 1:
                query(q, 'google', result)

        else: # source가 지정된 경우
            query(q, source, result)

        # 좌표계 지정된 경우 처리 필요
        prj = Proj(init=crs)

        ### RETURN ###
        # 하나도 응답이 없는 경우 실패로 리턴
        if len(result) <= 0:
            # 실패시 로그로 남기자
            # http://gyus.me/?p=418
            logger.info("ALL fail | {}".format(q))

            return make_response({"q": q, "x": None, "y": None, "lng": None, "lat": None, "address": None,
                                  "sd": -1, "geojson": None})

        ### RETURN ###
        # 입력 주소값과 완전 동일한 주소를 반환하면 틀림 없는 것으로 판정
        for res in result:
            address = res["address"]
            if address == q:
                if crs == "epsg:4326":
                    x, y = res["x"], res["y"]
                else:
                    x, y = prj(res["x"], res["y"])

                geojson = make_geojson(x, y, res["address"], res["service"], 0)
                return make_response(
                    {
                        "q": q, "x": x, "y": y, "lng": res["x"], "lat": res["y"], "address": res["address"],
                        "sd": 0,
                        "geojson": geojson
                    }
                )

        ### RETURN ###
        # 결과가 한 개인 경우
        if len(result) == 1:
            res = result[0]
            if crs == "epsg:4326":
                x, y = res["x"], res["y"]
            else:
                x, y = prj(res["x"], res["y"])

            geojson = make_geojson(x, y, res["address"], res["service"], 0)
            return make_response(
                {
                    "q": q, "x": x, "y": y, "lng": res["x"], "lat": res["y"], "address": res["address"],
                    "sd": 0,
                    "geojson": geojson
                }
            )

        # 오차범위로 줄어들거나 2개만 남을 때까지 반복해 실행
        while True:
            # Naver 좌표계로 변환하여 거리측정 준비
            points = list()
            min_x = min_y = max_x = max_y = None
            sum_x = sum_y = 0
            for res in result:
                lng, lat = res['x'], res['y']
                x, y = gProj5179(lng, lat)
                points.append([x, y])
                min_x = min_x if min(min_x, x) else x  # 삼항연산자: http://gentooboy.tistory.com/102
                min_y = min_y if min(min_y, y) else y
                max_x = max_x if max(max_x, x) else x
                max_y = max_y if max(max_y, y) else y
                sum_x += x
                sum_y += y
            avg_x = sum_x / len(points)
            avg_y = sum_y / len(points)

            # 공간거리 편차 계산
            sum_dev_sq = 0
            for pnt in points:
                sum_dev_sq += (avg_x-pnt[0])**2 + (avg_y-pnt[1])**2
            sd = sqrt(sum_dev_sq / len(points))

            ### RETURN ###
            # 표준편차가 50을 넘지 않거나 결과가 2개 뿐이 없는 경우
            if sd <= 50 or len(result) <= 2:
                service = None
                address = None
                base_data = list()
                sum_x = sum_y = 0

                for i in range(len(result)):
                    res = result[i]
                    if not service:
                        service = str(res["service"])
                    else:
                        service = "{}|{}".format(service, res["service"])

                    # 긴 주소가 맞는 것으로 판단
                    if not address:
                        address = str(res["address"])
                    else:
                        if len(res["address"]) > len(address):
                            address = str(res["address"])
                    deviation = sqrt((avg_x-points[i][0])**2 + (avg_y-points[i][1])**2)

                    if crs == "epsg:4326":
                        x, y = res["x"], res["y"]
                    else:
                        x, y = prj(res["x"], res["y"])
                    sum_x += x
                    sum_y += y

                    geojson = make_geojson(x, y, res["address"], res["service"], int(deviation))
                    base_data.append(geojson)

                return make_response(
                    {
                        "q": q, "x": x, "y": y, "lng": res["x"], "lat": res["y"], "address": address,
                        "sd": int(sd),
                        "geojson": make_geojson(sum_x/len(base_data), sum_y/len(base_data), address, service, 0),
                        "basedata": {
                            "type": "FeatureCollection",
                            "features": base_data
                        }
                    }
                )

            # 통계적으로 튀는 값을 판별하는 방식이 있음
            # http://egloos.zum.com/bioscience/v/5716716
            # 하지만 그냥 편차가 가장 큰 놈을 제거하고 반복
            max_dev = None
            max_dev_index = None
            for i in range(len(result)):
                deviation = sqrt((avg_x-points[i][0])**2 + (avg_y-points[i][1])**2)
                if not max_dev or deviation > max_dev:
                    max_dev_index = i
                    max_dev = deviation

            result.remove(result[max_dev_index])

        ## END WHILE

        res_string = ""
        for res in result:
            res_string += "{}[{}]: ({},{}) - {}<br/>".format(
                res["service"], res["seq"], res["x"], res["y"], res["address"]
            )

        return res_string

    except Exception as err:
        logger.error(err)
        return "[ERROR] {}".format(err)


# dict을 json으로 변환하며 mimetype과 charset을 지정
def make_response(dictionary):
    ret = Response(json.dumps(dictionary, ensure_ascii=False), mimetype='application/json')
    ret.content_encoding = 'utf-8'
    return ret


# geojson용 dict 만들기
def make_geojson(x, y, address, service, deviation):
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [x, y]
        },
        "properties": {
            "address": address,
            "service": service,
            "deviation": deviation
        }
    }


def format_res(res, name):
    if res:
        return "{}:\t({},{}) - {}<br/>".format(name, res['x'], res['y'], res['address'])
    else:
        return "{}:\tError<br/>".format(name)


def query(q, service_name, result):
    try:
        # TODO: 원본주서 전처리가 필요하다.


        # 각 서비스별 키를 돌려가며 사용
        i = gKeyIndexDict[service_name] + 1
        if i >= len(gKeyListDict[service_name]):
            gKeyIndexDict[service_name] = i = 0
        else:
            gKeyIndexDict[service_name] = i

        # 한글주소가 문제 없도록 인코딩
        # http://stackoverflow.com/questions/3563126/url-encoding-decoding-with-python
        encoded_str = urllib2.quote(q.encode("utf-8"))
        key = gKeyListDict[service_name][i]
        url = gQueryDict[service_name].format(q=encoded_str, key=key)
        #print url

        #f = urllib2.urlopen(url)
        # Accept-Language에 따라 응답이 달라지는 구글을 위해
        header = {'Accept-Language': 'ko,en-US;q=0.8,en;q=0.6'}
        req = urllib2.Request(url, headers=header)
        f = urllib2.urlopen(req)
        res = f.read()
        f.close()
        #print res
        dic = json.loads(res, "utf-8")
        # json을 dict로 변환한 경우 그냥 보면 한글이 깨져 보이지만 실제는 문제 없다.
        # http://khanrc.tistory.com/entry/%ED%95%9C%EA%B8%80-in-the-dictionary-feat-pretty

        items = eval(gResFilterDict[service_name])
        for i in range(len(items)):
            item = items[i]
            res_address = eval(gFieldAddressDict[service_name])
            # TODO: 출력 주소의 정제가 필요
            result.append(
                {
                    'service': service_name,
                    'seq': i,
                    'x': float(eval(gFieldXDict[service_name])),
                    'y': float(eval(gFieldYDict[service_name])),
                    'address': res_address,
                    'org': item
                }
            )
            break  # 유사 주소를 여러개 반환하는 Naver 때문에 1개만 반환

        # TODO: 결과의 유사도 판단이 필요하다
        # http://iam312.pe.kr/m/post/277

    except urllib2.HTTPError, e:
        raise Exception('HTTPError = ' + str(e.code))
    except urllib2.URLError, e:
        raise Exception('URLError = ' + str(e.reason))
    except Exception:
        # 변환 실패의 경우 예상 포맷대로 들어오지 않음
        logger.debug("{} fail | {}".format(service_name, q))
        return None


#############################
# 서비스 실행
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)
