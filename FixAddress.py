#-*- coding: utf-8 -*-
import re

def format_address(org_address):
    out_address = re.sub(u"\s+", u" ", org_address)
    out_address = re.sub(u"^한국\s", u"", out_address)
    out_address = re.sub(u"^서울\s특별시\s", u"서울특별시 ", out_address)
    out_address = re.sub(u"^서울\s", u"서울특별시 ", out_address)
    out_address = re.sub(u"^서울시\s", u"서울특별시 ", out_address)
    out_address = re.sub(u"^인천\s광역시\s", u"인천광역시 ", out_address)
    out_address = re.sub(u"^인천\s", u"인천광역시 ", out_address)
    out_address = re.sub(u"^인천시\s", u"인천광역시 ", out_address)
    out_address = re.sub(u"^대구\s광역시\s", u"대구광역시 ", out_address)
    out_address = re.sub(u"^대구\s", u"대구광역시 ", out_address)
    out_address = re.sub(u"^대구시\s", u"대구광역시 ", out_address)
    out_address = re.sub(u"^울산\s광역시\s", u"울산광역시 ", out_address)
    out_address = re.sub(u"^울산\s", u"울산광역시 ", out_address)
    out_address = re.sub(u"^울산시\s", u"울산광역시 ", out_address)
    out_address = re.sub(u"^부산\s광역시\s", u"부산광역시 ", out_address)
    out_address = re.sub(u"^부산\s", u"부산광역시 ", out_address)
    out_address = re.sub(u"^부산시\s", u"부산광역시 ", out_address)
    out_address = re.sub(u"^광주\s광역시\s", u"광주광역시 ", out_address)
    out_address = re.sub(u"^광주\s", u"광주광역시 ", out_address)
    out_address = re.sub(u"^광주시\s", u"광주광역시 ", out_address)
    out_address = re.sub(u"^대전\s광역시\s", u"대전광역시 ", out_address)
    out_address = re.sub(u"^대전\s", u"대전광역시 ", out_address)
    out_address = re.sub(u"^대전시\s", u"대전광역시 ", out_address)
    out_address = re.sub(u"^경기\s", u"경기도 ", out_address)
    out_address = re.sub(u"^강원\s", u"강원도 ", out_address)
    out_address = re.sub(u"^경남\s", u"경상남도 ", out_address)
    out_address = re.sub(u"^경남도\s", u"경상남도 ", out_address)
    out_address = re.sub(u"^경북\s", u"경상북도 ", out_address)
    out_address = re.sub(u"^경북도\s", u"경상북도 ", out_address)
    out_address = re.sub(u"^제주\s", u"제주특별자치도 ", out_address)
    out_address = re.sub(u"^제주도\s", u"제주특별자치도 ", out_address)
    out_address = re.sub(u"^전남\s", u"전라남도 ", out_address)
    out_address = re.sub(u"^전남도\s", u"전라남도 ", out_address)
    out_address = re.sub(u"^전북\s", u"전라북도 ", out_address)
    out_address = re.sub(u"^전북도\s", u"전라북도 ", out_address)
    out_address = re.sub(u"^충남\s", u"충청남도 ", out_address)
    out_address = re.sub(u"^충남도\s", u"충청남도 ", out_address)
    out_address = re.sub(u"^충북\s", u"충청북도 ", out_address)
    out_address = re.sub(u"^충북도\s", u"충청북도 ", out_address)
    out_address = re.sub(u"\s산(\d+)", u' 산 \g<1>', out_address)
    out_address = re.sub(u"\s(\d+가)\s", u'\g<1> ', out_address)
    out_address = re.sub(u"\s(\d+동)\s", u'\g<1> ', out_address)
    out_address = re.sub(u"\s(\d+리)\s", u'\g<1> ', out_address)
    out_address = re.sub(u"\s(\d+)번지\s*(\d+)호", u'\g<1>-\g<2>', out_address)
    out_address = re.sub(u"(\S)(\d+)번지\s*(\d+)호", u'\g<1> \g<2>-\g<3>', out_address)
    out_address = re.sub(u"\s+(\d+)호", u' \g<1>', out_address)
    out_address = re.sub(u"(\d+)번지\s", u'\g<1>', out_address)
    out_address = re.sub(u"(\d+)번지$", u'\g<1>', out_address)
    out_address = re.sub(u"\(.*\)", u'', out_address)  # 새주소 동명 및 건물명 제거
    out_address = re.sub(u"동(\d+)", u'동 \g<1>', out_address)
    out_address = re.sub(u"리(\d+)", u'리 \g<1>', out_address)
    out_address = re.sub(u"가(\d+)", u'가 \g<1>', out_address)
    out_address = re.sub(u"길(\d+)", u'길 \g<1>', out_address)
    out_address = re.sub(u"(\D+)(\d+\-\d+)$", u'\g<1> \g<2>', out_address)
    out_address = re.sub(u"(\D+)(\d+)$", u'\g<1> \g<2>', out_address)
    out_address = re.sub(u"(\d+)\s*\-\s*(\d+)", u'\g<1>-\g<2>', out_address)  # 번지 주변 빈칸 제거
    out_address = re.sub(u"\s+", u" ", out_address)  # 연속 빈칸을 하나로
    out_address = out_address.strip()  # 처음과 끝의 공백 제거
    out_address = re.sub(u"(\d+)\s+\D+$", u'\g<1>', out_address)  # 번지 뒤 건물명 등 제거

    return out_address


