import streamlit as st
from datetime import datetime, timedelta
from openai import OpenAI
import os
from dotenv import load_dotenv
import pandas as pd

# ✅ 페이지 설정
st.set_page_config(page_title="감정일기", page_icon="💜", layout="wide")

# ✅ 비밀번호 설정
app_password = "2752"

# ✅ API 키 불러오기
try:
    api_key = str(st.secrets["OPENAI_API_KEY"])
except Exception:
    load_dotenv()
    api_key = str(os.getenv("OPENAI_API_KEY"))

client = OpenAI(api_key=api_key)

# ✅ 인증 상태 초기화
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# ✅ 인증 흐름
if not st.session_state["authenticated"]:
    st.title("🔐 감정일기 잠금 해제")
    pw = st.text_input("비밀번호를 입력하세요", type="password", placeholder="비밀번호를 입력해주세요")
    if pw.strip() == app_password:
        st.session_state["authenticated"] = True
        st.rerun()
    elif pw:
        st.error("비밀번호가 틀렸어요.")
    st.stop()

# ✅ 앱 시작
st.title("💜 감정일기")
st.markdown('<p style="color:#B388EB;">AI가 당신의 감정을 공감하고, 필요할 땐 다정하게 제안도 드려요.</p>', unsafe_allow_html=True)
st.markdown('<p style="color:#B388EB;">💡 상단에서 감정을 선택하면 캘린더에 이모티콘이 나타난답니다.</p>', unsafe_allow_html=True)

# ✅ 세션 상태 초기화
if "diary_log" not in st.session_state:
    st.session_state.diary_log = []
if "show_example" not in st.session_state:
    st.session_state.show_example = True

# ✅ 샘플 일기 자동 추가
if not st.session_state.diary_log:
    st.session_state.diary_log.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "emotion": "😟 불안",
        "text": "오늘은 별일 없었는데도 마음이 계속 불안했어요.",
        "response": "불안한 하루였군요. 그런 날도 있어요. 지금은 잠시 쉬어가도 괜찮아요."
    })

# ✅ 감정 선택 + 일기 입력
emotion_options = [
    "😊 기쁨", "😢 슬픔", "😠 분노", "😟 불안",
    "😌 편안함", "😩 지침", "😔 외로움", "😳 당황", "선택 안 함"
]

with st.form("diary_form"):
    selected_emotion = st.radio("오늘의 감정은?", options=emotion_options, horizontal=True, index=len(emotion_options)-1)
    diary_text = st.text_area("오늘 하루 어땠나요?", height=200, placeholder="ex) 오늘은 조금 힘든 하루였어요...")
    submitted = st.form_submit_button("🔍 감정 분석하기")

# ✅ 감정 프롬프트 생성
def build_prompt(emotion):
    return f"""
당신은 사용자의 감정일기를 읽고, 감정의 맥락에 맞는 따뜻하고 현실적인 위로를 건네는 역할입니다.

- 사용자의 감정을 판단하지 말고, 있는 그대로 공감해주세요.
- “{emotion}”이라는 감정에 어울리는 말투와 공감 표현을 사용해주세요.
- 조언이 필요한 상황(예: 친구와의 갈등)에서는 사용자의 편에서 다정하게 말해주세요.
- 너무 길지 않게, 진심 어린 존댓말로 1~2문장 이내로 응답해주세요.
"""

# ✅ AI 응답 생성
def get_ai_response(text, emotion):
    prompt = build_prompt(emotion)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"오늘의 감정: {emotion}\n\n감정일기:\n{text}"}
        ],
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message.content

# ✅ 감정 분석 실행
if submitted and diary_text.strip():
    with st.spinner("AI가 당신의 이야기를 듣고 있어요..."):
        emotion = selected_emotion if selected_emotion != "선택 안 함" else "⬜️ 감정 미선택"
        response = get_ai_response(diary_text, emotion)
        st.session_state.diary_log.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "emotion": emotion,
            "text": diary_text,
            "response": response
        })
        st.success("감정 분석이 완료되었어요!")
        st.markdown(f"**내가 쓴 일기:** {diary_text}")
        st.markdown(f"**AI의 응답:** {response}")
        st.session_state.show_example = False

# ✅ 감정일기 예시 (최초 1회만)
if st.session_state.show_example:
    st.markdown(
        '<p style="color:#B388EB; font-size:0.9rem;">💜 감정일기 예시 (이런 식으로 짧게 써보셔도 좋아요!)</p>',
        unsafe_allow_html=True
    )
    st.markdown("**😢 슬픔 감정일기**")
    st.markdown("**내가 쓴 일기:** 괜히 눈물이 나는 하루였어요.")
    st.markdown("**AI의 응답:** 그 감정, 소중해요. 오늘도 잘 견뎌주셔서 고마워요.")

# ✅ 감정일기 목록
if st.session_state.diary_log:
    st.markdown("## 📒 내가 쓴 감정일기")
    for idx, entry in enumerate(reversed(st.session_state.diary_log)):
        real_index = len(st.session_state.diary_log) - 1 - idx
        with st.container():
            col1, col2 = st.columns([0.95, 0.05])
            with col1:
                st.markdown(f"**🗓️ {entry['date']} | {entry['emotion']}**")
                st.markdown(f"**내가 쓴 일기:** {entry['text']}")
                st.markdown(f"**AI의 응답:** {entry['response']}")
            with col2:
                if st.button("🗑️", key=f"delete_{real_index}"):
                    del st.session_state.diary_log[real_index]
                    st.rerun()

# ✅ 감정 캘린더
st.markdown("## 📅 감정 캘린더")

if st.session_state.diary_log:
    df = pd.DataFrame(st.session_state.diary_log)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    calendar_map = {}
    for _, row in df.iterrows():
        emoji = ''.join([c for c in row["emotion"] if c in "😀😢😠😟😳😔😌😩😊❤️"])
        emoji = emoji if emoji else "⬜️"
        date_key = row["date"].strftime("%Y-%m-%d")
        calendar_map[date_key] = {
            "emoji": emoji,
            "tooltip": f"{date_key} - {row['emotion']}"
        }

    today = datetime.today()
    start_day = today - timedelta(days=29)
    dates = [start_day + timedelta(days=i) for i in range(30)]

    calendar_html = '<div style="font-family:monospace; background-color:#f9f9f9; padding:1rem; border-radius:1rem; line-height:2.2; font-size:1.1rem;">'
    for i, date in enumerate(dates):
        date_str = date.strftime("%Y-%m-%d")
        if date_str in calendar_map:
            emoji = calendar_map[date_str]["emoji"]
            tooltip = calendar_map[date_str]["tooltip"]
        else:
            emoji = "⬜️"
            tooltip = f"{date_str} - 기록 없음"
        calendar_html += f'<span title="{tooltip}">{emoji}</span>  '
        if (i + 1) % 7 == 0:
            calendar_html += "<br>"
    calendar_html += "</div>"

    st.markdown(calendar_html, unsafe_allow_html=True)
    st.caption("⬜️ 감정을 선택하지 않으셨군요. 감정을 선택하면 이모티콘이 나타난답니다.")
else:
    st.info("아직 감정일기가 작성되지 않았어요. 오늘의 감정을 남겨보세요!")

# ✅ AI와 더 대화하기 버튼
st.markdown("## 💬 AI와 더 대화해보기")

if st.button("💖 AI와 더 대화해볼래요", key="chat_button"):
    st.markdown(
        '<p style="color:#FFB6C1; font-size:1rem;">💬 AI와의 대화 기능은 준비 중이에요. 곧 만나요!</p>',
        unsafe_allow_html=True
    )