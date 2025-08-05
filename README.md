# AI 교통 경로 추천 시스템

Django와 카카오맵 API, OpenAI를 활용한 AI 기반 교통 경로 추천 서비스입니다.

## 주요 기능

- 카카오맵 API를 통한 실시간 교통 정보 분석
- OpenAI를 활용한 AI 기반 경로 추천
- 빅데이터 기반 교통 패턴 분석
- 택시 요금 계산 및 최적 경로 제안

## 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/hyunhan-cho/ai-traffic-recommendation.git
cd ai-traffic-recommendation
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv myvenv
myvenv\Scripts\activate  # Windows
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정
```bash
copy .env.example .env  # Windows
```

`.env` 파일을 열어서 실제 API 키들로 수정하세요:
```properties
KAKAO_API_KEY=your_kakao_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_django_secret_key_here
DEBUG=True
```

### 5. 서버 실행
```bash
python manage.py runserver
```

## 필요한 API 키

### KAKAO_API_KEY
1. [카카오 개발자 센터](https://developers.kakao.com/)에 접속
2. 애플리케이션 생성
3. 플랫폼 설정에서 Web 플랫폼 추가
4. REST API 키 사용

### OPENAI_API_KEY
1. [OpenAI 플랫폼](https://platform.openai.com/)에 접속
2. API Keys 섹션에서 새 키 생성
3. 생성된 키를 환경변수에 설정

## 기술 스택

- **Backend**: Django 5.2.4
- **API**: 카카오맵 API, OpenAI API
- **Database**: SQLite (실제로는 사용하지 않음)
- **Frontend**: HTML, CSS, JavaScript

## Cloudtype 배포

### 1. Cloudtype 환경변수 설정
다음 환경변수를 설정하세요:
- `SECRET_KEY`: Django 시크릿 키
- `DEBUG`: False
- `KAKAO_API_KEY`: 카카오 REST API 키
- `OPENAI_API_KEY`: OpenAI API 키

### 2. 애플리케이션 설정
- **Python 버전**: v3.12
- **Port**: 8000
- **Start command**: gunicorn config.wsgi:application --bind 0.0.0.0:8000
- **Install command**: pip install -r requirements.txt
- **Pre start Command**: python manage.py collectstatic --noinput

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
