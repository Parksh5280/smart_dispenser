from flask import Flask, render_template, request, jsonify
import serial
import pandas as pd
import time

app = Flask(__name__)

# 약품 CSV 파일 로드
data = pd.read_csv('/home/8team/smart_dispenser/drug_info.csv', skip_blank_lines=True)

# 가짜 시리얼 클래스 정의 (테스트용)
class FakeSerial:
    def write(self, command):
        print(f"[SIMULATION] Writing to Arduino: {command.decode().strip()}")
    
    def readline(self):
        print("[SIMULATION] Reading from Arduino...")
        return b"Simulated Arduino response\n"

# 아두이노 연결
try:
    arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    print("Connected to Arduino!")
except serial.SerialException:
    print("Arduino not connected. Using simulated serial communication.")
    arduino = FakeSerial()  # 가짜 시리얼 객체 사용

# 알람 데이터 관리 (모터별 알람 시간, 작동 횟수, 약 이름 저장)
alarms = {
    "M1": {"time": None, "count": 0, "drug_name": None},
    "M2": {"time": None, "count": 0, "drug_name": None},
    "M3": {"time": None, "count": 0, "drug_name": None}
}

# GUI 메시지 전송
def send_to_gui(message):
    """GUI에 메시지를 전달하기 위해 파일에 작성"""
    with open("/tmp/gui_message.txt", "w") as f:
        f.write(message)

# 알람 체크 함수
def check_alarms():
    while True:
        current_time = time.strftime("%H:%M")
        alarm_triggered = False  # 스피커 작동 플래그

        for motor, alarm_data in alarms.items():
            if alarm_data["time"] == current_time and alarm_data["count"] > 0:
                # 모터 작동 명령 전송
                command = f"{motor} {alarm_data['count']}\n"
                arduino.write(command.encode())
                print(f"Motor {motor} activated {alarm_data['count']} times at {current_time}")
                
                # GUI 업데이트
                send_to_gui(f"약품 배출: {alarm_data['drug_name']} ({alarm_data['count']} 개)")

                # 알람 초기화
                alarms[motor] = {"time": None, "count": 0, "drug_name": alarm_data["drug_name"]}
                alarm_triggered = True

                # 모터 명령 간 지연 추가
                time.sleep(1)

        if alarm_triggered:
            # 스피커 작동
            arduino.write(b"S1\n")
            print(f"Speaker alarm triggered at {current_time}")
        
        time.sleep(60)  # 1분마다 확인

# 백그라운드 알람 체크 스레드 시작
import threading
threading.Thread(target=check_alarms, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

# 알약 배출
@app.route('/dispense', methods=['POST'])
def dispense():
    try:
        motor = request.form.get('motor')  # M1, M2, M3
        steps = request.form.get('steps')  # 회전 스텝 수

        if motor not in ['M1', 'M2', 'M3']:
            return jsonify({"error": "Invalid motor identifier"}), 400

        command = f"{motor} {steps}\n"
        arduino.write(command.encode())

        # GUI 업데이트
        send_to_gui(f"약품 배출 명령: {motor} ({steps} 개)")

        return jsonify({"status": "success", "command_sent": command})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 알람 설정 (시간, 작동 횟수, 약 이름 저장)
@app.route('/set_alarm', methods=['POST'])
def set_alarm():
    try:
        motor = request.json.get('motor')  # M1, M2, M3
        alarm_time = request.json.get('alarm_time')  # HH:MM 형식
        count = int(request.json.get('count', 1))  # 작동 횟수 (기본값: 1)
        drug_name = request.json.get('drug_name')  # 약 이름

        if motor not in ['M1', 'M2', 'M3']:
            return jsonify({"error": "Invalid motor identifier"}), 400
        if count < 1:
            return jsonify({"error": "Count must be at least 1"}), 400

        # 알람 데이터 저장
        alarms[motor] = {"time": alarm_time, "count": count, "drug_name": drug_name}

        # GUI 업데이트
        send_to_gui(f"알람 설정: {drug_name} ({count} 개) - 시간: {alarm_time}")

        return jsonify({"status": "success", "motor": motor, "alarm_time": alarm_time, "count": count, "drug_name": drug_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 알람 상태 확인
@app.route('/get_alarms', methods=['GET'])
def get_alarms():
    try:
        return jsonify({"status": "success", "alarms": alarms})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 약품 검색 API
@app.route('/search', methods=['POST'])
def search_drug():
    try:
        drug_name = request.json.get('drug_name', '')  # 클라이언트에서 전달된 약품명
        matching_rows = data[data['약품명'].str.contains(drug_name, case=False, na=False)]
        
        if not matching_rows.empty:
            # 결과를 JSON으로 반환
            results = []
            display_message = f"검색 결과 - {drug_name}:\n"
            for _, row in matching_rows.iterrows():
                precautions = row['주의사항'].split('.')  # 마침표를 기준으로 나눔
                formatted_precautions = '.\n'.join([p.strip() for p in precautions if p.strip()])  # 빈 문장 제거 및 개행 추가
                results.append({
                    "약품명": row['약품명'],
                    "주의사항": formatted_precautions
                })
                display_message += f"\n약품명: {row['약품명']}\n주의사항:\n{formatted_precautions}\n"
            
            # GUI 업데이트
            send_to_gui(display_message.strip())

            return jsonify({"status": "success", "results": results})
        else:
            error_message = f"검색 결과 없음 - {drug_name}"
            # GUI 업데이트
            send_to_gui(error_message)

            return jsonify({"status": "error", "message": "해당 약품이 목록에 없습니다."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 스피커 테스트
@app.route('/play_melody', methods=['POST'])
def play_melody():
    try:
        arduino.write(b"S1\n")
        return jsonify({"status": "success", "message": "Melody command sent to Arduino"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
