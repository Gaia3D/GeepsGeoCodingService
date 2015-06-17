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
from difflib import SequenceMatcher
import logging

# 주소 정제를 위한 함수를 별도 파일로 분리
from FixAddress import format_address


# 로깅 모드 설정
logging.basicConfig(level=logging.INFO)
LOG_FILE_PATH = "D:/www_python/GeoCoding.log"
#LOG_FILE_PATH = "/temp/GeoCoding.log"

# 로깅 형식 지정
# http://gyus.me/?p=418
logger = logging.getLogger("failLogger")
formatter = logging.Formatter('[%(levelname)s] %(asctime)s > %(message)s')
fileHandler = logging.FileHandler(LOG_FILE_PATH)
# streamHandler = logging.StreamHandler()
fileHandler.setFormatter(formatter)
# streamHandler.setFormatter(formatter)
logger.addHandler(fileHandler)
# logger.addHandler(streamHandler)


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

gProvenceList = [u"서울특별시", u"부산광역시", u"인천광역시", u"대구광역시", u"광주광역시", u"대전광역시",
                 u"울산광역시", u"경기도", u"강원도", u"충청남도", u"충청북도", u"전라남도", u"전라북도", u"경상남도",
                 u"경상북도", u"제주특별자치도"]


@app.route("/test", methods=['GET'])
@app.route("/geocoding/test", methods=['GET'])
def test():
    return 'TEST SUCCESS'


@app.route("/service_page", methods=['GET'])
@app.route("/geocoding/service_page", methods=['GET'])
def service_page():
    return render_template("service_page.html")


@app.route("/capabilities", methods=['GET'])
@app.route("/geocoding/capabilities", methods=['GET'])
def getcapabilities():
    capabilities = {
        "sources": gSourceList,
        "outputs": gOutputList,
        "projections": gCrsList
    }
    return make_response(capabilities)


# 실제 GeoCoding 서비스
@app.route("/api", methods=['GET'])
@app.route("/geocoding/api", methods=['GET'])
def geo_coding():
    try:
        q = request.args.get('q', None)
        source = request.args.get('source', 'auto').lower()
        output = request.args.get('output', 'json').lower()
        crs = request.args.get('crs', 'epsg:4326').lower()
        # 입력된 id가 있으면 보존되게 수정
        id = request.args.get('id', None)
        # 입력 주소 정제를 안하는 옵션 추가
        fix_address = request.args.get('fix_address','').lower()

        # 입력 주소의 정제가 필요
        if fix_address != "off" and fix_address != 'no':
            q = format_address(q)

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
        # http://bbolmin.tistory.com/164
        if source == "auto":
            # 쓰레드 이용하여 동시 호출: 네트워크 타임에서의 동시처리를 기대하지만 GIL 때문에 될지...
            th1 = Thread(target=query, args=(q, 'vworld', result, ))
            th2 = Thread(target=query, args=(q, 'vworld_new', result, ))
            th3 = Thread(target=query, args=(q, 'daum', result, ))
            th4 = Thread(target=query, args=(q, 'naver', result, ))
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
                                  "sd": -1, "sim_ratio": -1, "geojson": None}, id)

        ### RETURN ###
        # 입력 주소값과 완전 동일한 주소를 반환하면 틀림 없는 것으로 판정
        for res in result:
            address = res["address"]
            if get_sim_ratio(q, address) == 1.0:
                if crs == "epsg:4326":
                    x, y = res["x"], res["y"]
                else:
                    x, y = prj(res["x"], res["y"])

                address = res["address"]
                geojson = make_geojson(x, y, res["address"], res["service"], 0)
                return make_response(
                    {
                        "q": q, "x": x, "y": y, "lng": res["x"], "lat": res["y"], "address": address,
                        "sd": 0, "sim_ratio": 100,
                        "geojson": geojson
                    }, id
                )

        ### RETURN ###
        # 결과가 한 개인 경우
        if len(result) == 1:
            res = result[0]
            if crs == "epsg:4326":
                x, y = res["x"], res["y"]
            else:
                x, y = prj(res["x"], res["y"])

            address = res["address"]
            sim_ratio = get_sim_ratio(q, address)
            geojson = make_geojson(x, y, res["address"], res["service"], 0)
            return make_response(
                {
                    "q": q, "x": x, "y": y, "lng": res["x"], "lat": res["y"], "address": address,
                    "sd": 0, "sim_ratio": int(sim_ratio*100),
                    "geojson": geojson
                }, id
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

                max_sim_ratio = 0
                res_x, res_y = None, None
                res_lng, res_lat = None, None
                res_dev = None

                for i in range(len(result)):
                    res = result[i]
                    if not service:
                        service = unicode(res["service"])
                    else:
                        service = "{}|{}".format(service, res["service"])

                    # 결과의 유사도 판단
                    if not address:
                        address = unicode(res["address"])

                    if crs == "epsg:4326":
                        x, y = res["x"], res["y"]
                    else:
                        x, y = prj(res["x"], res["y"])
                    sum_x += x
                    sum_y += y

                    deviation = sqrt((avg_x-points[i][0])**2 + (avg_y-points[i][1])**2)

                    sim_ratio = get_sim_ratio(q, address)
                    if sim_ratio >= max_sim_ratio:
                        address = unicode(res["address"])
                        max_sim_ratio = sim_ratio
                        res_lng, res_lat = res["x"], res["y"]
                        res_x, res_y = x, y
                        res_dev = deviation

                    geojson = make_geojson(x, y, res["address"], res["service"], int(deviation))
                    base_data.append(geojson)

                return make_response(
                    {
                        "q": q, "x": res_x, "y": res_y, "lng": res_lng, "lat": res_lat, "address": address,
                        "sd": int(sd), "sim_ratio": int(max_sim_ratio*100),
                        #"geojson": make_geojson(sum_x/len(base_data), sum_y/len(base_data), address, service, 0),
                        # 평균좌표 대신 유사주소 좌표 사용으로 변경
                        "geojson": make_geojson(res_x, res_y, address, service, int(res_dev)),
                        "basedata": {
                            "type": "FeatureCollection",
                            "features": base_data
                        }
                    }, id
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


# 주소 유사도 판단
def get_sim_ratio(org_addr, out_addr, elseif=None):
    # 결과의 유사도 판단
    # http://stackoverflow.com/questions/17388213/python-string-similarity-with-probability

    org_addr = org_addr.strip()
    out_addr = out_addr.strip()

    # 주소를 4부분으로 나누어 테스트
    org_word_list = org_addr.split(" ")

    if len(org_word_list) == 0:
        org_word_list = ["", "", "", ""]

    # 처음이 시도 리스트에 없는 단어면 시도가 빠진 것으로 판단
    if gProvenceList.count(org_word_list[0]) <= 0:
        org_word_list.insert(0, "")

    if len(org_word_list) == 1:
        org_word_list.extend(["", "", ""])
    elif len(org_word_list) == 2:
        org_word_list.extend(["", ""])
    elif len(org_word_list) == 3:
        org_word_list.extend([""])
    elif len(org_word_list) > 4:
        list1 = org_word_list[:3]
        etc_address = " ".join(org_word_list[3:])
        org_word_list = list1
        org_word_list.append(etc_address)

    out_word_list = out_addr.split(" ")
    if len(out_word_list) == 0:
        out_word_list = ["", "", "", ""]
    elif len(out_word_list) == 1:
        out_word_list.extend(["", "", ""])
    elif len(out_word_list) == 2:
        out_word_list.extend(["", ""])
    elif len(out_word_list) == 3:
        out_word_list.extend([""])
    elif len(out_word_list) > 4:
        list1 = out_word_list[:3]
        etc_address = " ".join(out_word_list[3:])
        out_word_list = list1
        out_word_list.append(etc_address)

    total_sim_ratio = 0
    for i in range(4):
        if org_word_list[i] == "" or out_word_list[i] == "":
            pass
        else:
            total_sim_ratio += SequenceMatcher(None, org_word_list[i], out_word_list[i]).ratio() * 0.25

    # 주소 형식이 완전히 이상한 경우 전체로 테스트
    if total_sim_ratio == 0:
        total_sim_ratio = SequenceMatcher(None, org_addr, out_addr).ratio()

    return total_sim_ratio


# dict을 json으로 변환하며 mimetype과 charset을 지정
def make_response(dictionary, id=None):
    if id:
        dictionary["id"] = id
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
        logger.debug(url)

        #f = urllib2.urlopen(url)
        # Accept-Language에 따라 응답이 달라지는 구글을 위해
        header = {'Accept-Language': 'ko,en-US;q=0.8,en;q=0.6'}
        req = urllib2.Request(url, headers=header)
        f = urllib2.urlopen(req)
        res = f.read()
        f.close()
        # logger.debug(res)
        dic = json.loads(res, "utf-8")
        # json을 dict로 변환한 경우 그냥 보면 한글이 깨져 보이지만 실제는 문제 없다.
        # http://khanrc.tistory.com/entry/%ED%95%9C%EA%B8%80-in-the-dictionary-feat-pretty

        items = eval(gResFilterDict[service_name])
        for i in range(len(items)):
            item = items[i]
            res_address = eval(gFieldAddressDict[service_name])
            # 주소 정제
            address = format_address(res_address)
            result.append(
                {
                    'service': service_name,
                    'seq': i,
                    'x': float(eval(gFieldXDict[service_name])),
                    'y': float(eval(gFieldYDict[service_name])),
                    'address': address,
                    'org': item
                }
            )
            break  # 유사 주소를 여러개 반환하는 Naver 때문에 1개만 반환

    except urllib2.HTTPError, e:
        logger.error('HTTPError = {}: {}'.format(str(e.code), e.geturl()))
        raise Exception('HTTPError = ' + str(e.code))
    except urllib2.URLError, e:
        logger.error('URLError = {}: {}'.format(str(e.reason), e.filename))
        raise Exception('URLError = ' + str(e.reason))
    except Exception:
        # 변환 실패의 경우 예상 포맷대로 들어오지 않음
        logger.debug("{} fail | {}".format(service_name, q))
        return None


#############################
# 서비스 실행
if __name__ == '__main__':
    app.run()

# 기본 서비스로 실행시 flask 한 프로세스 당 1 요청만 처리할 수 있어 성능에 심각한 문제
# http://stackoverflow.com/questions/10938360/how-many-concurrent-requests-does-a-single-flask-process-receive

# Apache WSGI로 실행 필요
# http://flask-docs-kr.readthedocs.org/ko/latest/ko/deploying/mod_wsgi.html
# http://flask.pocoo.org/docs/0.10/deploying/mod_wsgi/
"""
### httpd.conf

# Call Python GeoCoding module by WSGI
LoadModule wsgi_module modules/mod_wsgi-py27-VC9.so
<VirtualHost *>
    ServerName localhost
    WSGIScriptAlias /geocoding d:\www_python\GeepsGeoCodingService\GeoCoding.wsgi
    <Directory d:\www_python\GeepsGeoCodingService>
        Order deny,allow
        Require all granted
    </Directory>
</VirtualHost>
"""