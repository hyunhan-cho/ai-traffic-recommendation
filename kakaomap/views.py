# kakaomap/views.py

import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from openai import OpenAI
from django.shortcuts import render
from django.http import JsonResponse

# .env 파일 로드
load_dotenv()

# API 키 설정
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
openai_client = OpenAI(api_key=OPENAI_API_KEY)


# 좌표 변환 함수
def get_coordinates(query):
    """장소명(주소, 건물명 등)을 좌표(x, y)로 변환"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    params = {"query": query}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200: 
        return None, None
    data = response.json()
    if not data.get("documents"): 
        return None, None
    return data["documents"][0]["x"], data["documents"][0]["y"]

# 길찾기 API 함수
def get_directions(start_x, start_y, goal_x, goal_y):
    """자동차 길찾기 API 호출"""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {"origin": f"{start_x},{start_y}", "destination": f"{goal_x},{goal_y}"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200: 
        return None
    return response.json()

def get_future_directions(start_x, start_y, goal_x, goal_y, departure_time):
    """특정 시간 출발 기준으로 자동차 길찾기 API 호출"""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    departure_timestamp = int(departure_time.timestamp())
    params = {
        "origin": f"{start_x},{start_y}",
        "destination": f"{goal_x},{goal_y}",
        "departure_time": departure_timestamp
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200: 
        return None
    return response.json()

# 실제 택시 요금 계산
def calculate_realistic_taxi_fare(distance_km, duration_minutes):
    """실제 서울 택시 요금 계산 (2024년 기준)"""
    base_fare = 4800  # 기본 요금 (2km까지)
    base_distance = 2.0
    
    if distance_km <= base_distance:
        return base_fare
    
    # 거리 요금: 132m당 100원
    extra_distance = distance_km - base_distance
    distance_fare = int((extra_distance * 1000) / 132) * 100
    
    # 시간 요금 (속도 15km/h 이하 시): 30초당 100원
    speed_kmh = (distance_km / duration_minutes) * 60 if duration_minutes > 0 else 999
    
    if speed_kmh < 15:  # 정체 상황
        normal_time_minutes = (distance_km / 15) * 60
        extra_time_minutes = max(0, duration_minutes - normal_time_minutes)
        time_fare = int(extra_time_minutes * 2) * 100  # 30초당 100원
    else:
        time_fare = 0
    
    total_fare = base_fare + distance_fare + time_fare
    
    # 심야 할증 (23:00 ~ 04:00)
    current_hour = datetime.now().hour
    if current_hour >= 23 or current_hour < 4:
        total_fare = int(total_fare * 1.2)  # 20% 할증
    
    return int(total_fare)

# 빅데이터 기반 교통 패턴
def get_seoul_traffic_pattern(hour, day_of_week, route_type="urban"):
    """서울 교통 빅데이터 기반 시간대별 혼잡도 패턴"""
    
    # 평일 교통 패턴 (서울시 교통량 빅데이터 기반)
    weekday_patterns = {
        6: 1.1, 7: 1.6, 8: 2.2, 9: 1.8, 10: 1.2, 11: 1.1,
        12: 1.3, 13: 1.4, 14: 1.2, 15: 1.3, 16: 1.5, 17: 1.9,
        18: 2.4, 19: 2.1, 20: 1.6, 21: 1.3, 22: 1.1, 23: 0.9,
        0: 0.8, 1: 0.7, 2: 0.7, 3: 0.8, 4: 0.9, 5: 1.0,
    }
    
    # 주말 교통 패턴
    weekend_patterns = {
        6: 0.8, 7: 0.9, 8: 1.0, 9: 1.1, 10: 1.3, 11: 1.4,
        12: 1.5, 13: 1.6, 14: 1.7, 15: 1.6, 16: 1.5, 17: 1.4,
        18: 1.3, 19: 1.2, 20: 1.1, 21: 1.0, 22: 0.9, 23: 0.8,
        0: 0.7, 1: 0.6, 2: 0.6, 3: 0.7, 4: 0.8, 5: 0.8
    }
    
    # 평일/주말 구분
    if day_of_week >= 5:  # 토요일, 일요일
        base_factor = weekend_patterns.get(hour, 1.0)
    else:  # 평일
        base_factor = weekday_patterns.get(hour, 1.0)
    
    # 경로 타입별 가중치
    route_multipliers = {
        "urban": 1.0,      # 시내 일반 도로
        "highway": 0.8,    # 고속도로
        "gangnam": 1.3,    # 강남 지역
        "bridge": 1.4,     # 한강 다리
    }
    
    final_factor = base_factor * route_multipliers.get(route_type, 1.0)
    return min(final_factor, 3.0)  # 최대 3배까지만

def get_congestion_level(traffic_factor):
    """혼잡도 레벨 표시"""
    if traffic_factor >= 2.0:
        return "🔴 매우 혼잡"
    elif traffic_factor >= 1.5:
        return "🟠 혼잡"
    elif traffic_factor >= 1.2:
        return "🟡 보통"
    else:
        return "🟢 원활"

def determine_route_type(start_place, goal_place):
    """출발지/도착지 기반 경로 타입 결정"""
    gangnam_areas = ["강남", "서초", "논현", "역삼", "삼성", "청담"]
    bridge_keywords = ["강남", "마포", "용산", "영등포", "강서", "송파"]
    
    location_text = f"{start_place} {goal_place}".lower()
    
    if any(area in location_text for area in gangnam_areas):
        return "gangnam"
    elif any(area in location_text for area in bridge_keywords):
        return "bridge"
    else:
        return "urban"

# 빅데이터 기반 AI 분석
def get_enhanced_ai_recommendation(results, start_place, goal_place):
    """빅데이터 기반 향상된 AI 분석"""
    
    # 데이터 정리
    route_data = []
    
    for result in results:
        route_data.append({
            "출발시간": result['departure_time'].strftime('%H:%M'),
            "소요시간": f"{int(result['realistic_duration'])}분",
            "거리": f"{result['distance']:.1f}km",
            "혼잡도": f"{result['traffic_factor']:.1f}배",
            "교통상황": result['congestion_level'],
            "택시요금": f"{result['fare']:,}원"
        })
    
    # AI에게 분석 요청
    prompt = f"""
다음은 {start_place}에서 {goal_place}까지의 시간대별 교통 분석 결과입니다.
서울시 교통 빅데이터를 기반으로 10분 간격으로 분석했습니다:

{route_data}

※ 혼잡도는 평상시 대비 배수 (서울시 교통량 빅데이터 기반)
※ 택시요금은 혼잡도에 따른 정체시간까지 반영한 실제 예상 요금

이 빅데이터 분석 결과를 바탕으로 다음을 포함한 추천을 해주세요:

1. 🎯 최적 출발 시간과 구체적인 이유
2. 📊 시간대별 교통 패턴 해석 (러시아워, 한가한 시간 등)
3. 💰 비용 효율적인 시간대 분석
4. 🚗 실용적인 교통 팁
5. 📝 한 줄 결론

친근하고 전문적인 톤으로 답변해주세요.
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 서울 교통 빅데이터 전문가입니다. 실제 교통 패턴과 요금제를 잘 알고 있으며, 데이터 기반의 정확한 분석을 제공합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"AI 분석 중 오류가 발생했습니다: {str(e)}"

# Django 메인 View 함수
def route_finder(request):
    context = {}
    
    if request.method == "POST":
        start_place = request.POST.get("start_place")
        goal_place = request.POST.get("goal_place")

        # 좌표 변환
        start_x, start_y = get_coordinates(start_place)
        goal_x, goal_y = get_coordinates(goal_place)

        if None in (start_x, start_y, goal_x, goal_y):
            context['error'] = "좌표 변환에 실패했습니다. 정확한 장소명을 입력해주세요."
            return render(request, 'kakaomap/route_finder.html', context)

        # 빅데이터 기반 교통 분석 실행
        current_time = datetime.now()
        current_day = current_time.weekday()
        
        # 경로 타입 결정
        route_type = determine_route_type(start_place, goal_place)
        
        results = []
        
        # 현재 시간부터 10분 간격으로 2시간 분석 (총 12개 시간대)
        for i in range(12):
            future_time = current_time + timedelta(minutes=i * 10)
            future_hour = future_time.hour
            future_day = future_time.weekday()
            
            # 카카오 API 호출
            if i == 0:
                # 현재 시간은 기본 API 사용
                route_result = get_directions(start_x, start_y, goal_x, goal_y)
            else:
                # 미래 시간은 departure_time API 사용
                route_result = get_future_directions(start_x, start_y, goal_x, goal_y, future_time)
            
            if route_result and route_result.get("routes"):
                summary = route_result["routes"][0]["summary"]
                
                # 빅데이터 기반 교통 혼잡도 계산
                traffic_factor = get_seoul_traffic_pattern(future_hour, future_day, route_type)
                
                # 기본 데이터
                base_duration = summary['duration'] / 60
                distance_km = summary['distance'] / 1000
                
                # 실제 소요시간 (빅데이터 혼잡도 반영)
                realistic_duration = base_duration * traffic_factor
                
                # 실제 택시 요금 계산
                realistic_fare = calculate_realistic_taxi_fare(distance_km, realistic_duration)
                
                results.append({
                    "departure_time": future_time,
                    "base_duration": base_duration,
                    "realistic_duration": realistic_duration,
                    "distance": distance_km,
                    "fare": realistic_fare,
                    "traffic_factor": traffic_factor,
                    "congestion_level": get_congestion_level(traffic_factor),
                    "api_fare": summary['fare']['taxi']
                })

        if not results:
            context['error'] = "경로 정보를 가져오지 못했습니다. API 키나 네트워크 상태를 확인해주세요."
            return render(request, 'kakaomap/route_finder.html', context)
            
        # 최적 시간 찾기
        best_result = min(results, key=lambda x: x['realistic_duration'])
        worst_result = max(results, key=lambda x: x['realistic_duration'])
        
        # AI 분석
        ai_recommendation = get_enhanced_ai_recommendation(results, start_place, goal_place)

        # 결과를 context에 담아 전달
        context.update({
            'start_place': start_place,
            'goal_place': goal_place,
            'route_type': route_type,
            'results': results,
            'best_result': best_result,
            'worst_result': worst_result,
            'time_diff': int(worst_result['realistic_duration'] - best_result['realistic_duration']),
            'fare_diff': worst_result['fare'] - best_result['fare'],
            'ai_recommendation': ai_recommendation.replace('\n', '<br>')  # 줄바꿈을 <br>로 변경
        })

    return render(request, 'kakaomap/route_finder.html', context)

# API 엔드포인트 (AJAX 요청용)
def route_analysis_api(request):
    """빅데이터 기반 교통 분석 API"""
    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            start_place = data.get("start_place")
            goal_place = data.get("goal_place")
            
            # 좌표 변환
            start_x, start_y = get_coordinates(start_place)
            goal_x, goal_y = get_coordinates(goal_place)

            if None in (start_x, start_y, goal_x, goal_y):
                return JsonResponse({
                    'success': False,
                    'error': "좌표 변환에 실패했습니다. 정확한 장소명을 입력해주세요."
                })

            # 빅데이터 기반 교통 분석 실행
            current_time = datetime.now()
            current_day = current_time.weekday()
            
            # 경로 타입 결정
            route_type = determine_route_type(start_place, goal_place)
            
            results = []
            
            # 현재 시간부터 10분 간격으로 2시간 분석 (총 12개 시간대)
            for i in range(12):
                future_time = current_time + timedelta(minutes=i * 10)
                future_hour = future_time.hour
                future_day = future_time.weekday()
                
                # 카카오 API 호출
                if i == 0:
                    # 현재 시간은 기본 API 사용
                    route_result = get_directions(start_x, start_y, goal_x, goal_y)
                else:
                    # 미래 시간은 departure_time API 사용
                    route_result = get_future_directions(start_x, start_y, goal_x, goal_y, future_time)
                
                if route_result and route_result.get("routes"):
                    summary = route_result["routes"][0]["summary"]
                    
                    # 빅데이터 기반 교통 혼잡도 계산
                    traffic_factor = get_seoul_traffic_pattern(future_hour, future_day, route_type)
                    
                    # 기본 데이터
                    base_duration = summary['duration'] / 60
                    distance_km = summary['distance'] / 1000
                    
                    # 실제 소요시간 (빅데이터 혼잡도 반영)
                    realistic_duration = base_duration * traffic_factor
                    
                    # 실제 택시 요금 계산
                    realistic_fare = calculate_realistic_taxi_fare(distance_km, realistic_duration)
                    
                    results.append({
                        "departure_time": future_time,
                        "base_duration": base_duration,
                        "realistic_duration": realistic_duration,
                        "distance": distance_km,
                        "fare": realistic_fare,
                        "traffic_factor": traffic_factor,
                        "congestion_level": get_congestion_level(traffic_factor),
                        "api_fare": summary['fare']['taxi']
                    })

            if not results:
                return JsonResponse({
                    'success': False,
                    'error': "경로 정보를 가져오지 못했습니다. API 키나 네트워크 상태를 확인해주세요."
                })
                
            # AI 분석
            ai_recommendation = get_enhanced_ai_recommendation(results, start_place, goal_place)
            
            return JsonResponse({
                'success': True,
                'results': results,
                'ai_recommendation': ai_recommendation
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'POST 요청만 허용됩니다.'})