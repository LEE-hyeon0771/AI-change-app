SHELL := /usr/bin/bash

.PHONY: backend flutter-web flutter-mobile

## FastAPI backend (uvicorn) - uses .venv Python
backend-server:
	@cd backend && ../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## Flutter web (Chrome) - runs lib/main.dart
flutter-chrome:
	@cd frontend_flutter && flutter pub get && flutter run -d chrome && flutter run -t lib/main.dart -d chrome --web-port 5000

## Flutter mobile (에뮬레이터/연결된 디바이스)
## 연결된 기기 중 기본 디바이스에 실행됩니다.
flutter-mobile:
	@cd frontend_flutter && flutter pub get && flutter run


