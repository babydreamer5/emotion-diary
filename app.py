import streamlit as st
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import re

# 환경변수 로드
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="감정일기", layout="wide")

if "is_premium_user" not in st.session_state:
    st.session_state["is_premium_user"] = False

st.markdown("""
    <style>
    body {
        background: linear-gradient(to bottom right, #fce4ec, #e1bee7);
    }
    .emotion-card {
        background-color: rgba(255, 255, 255, 0.6);
        padding: 1rem;
        border-radius: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    .emotion-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #6a1b9a;
    }
    .emotion-text {
        font-size: 1.1rem;
        color: #7e57c2;
        font-weight: 500;
        margin-top: 0.5rem;
    }
    .calendar-box {
        font-family: monospace;
        background-color: rgba(255,255,255,0.5);
        padding: 1rem;
        border-radius: 1rem;
        white-space: pre-wrap;
        line-height: 2.2;
        font-size: 1.2rem;
        color: #4a148c;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌷 감정일기")
st.caption("💬 당신의 감정을 들어주는 작은 공간")

emotion_options = {
    "😊 기쁨": "기분이 좋아요 😊",
    "😢 슬픔": "마음이 울적해요 😢",
    "😠 분노": "짜증나고 화가 나요 😠",
    "😟 불안": "좀 불안하고 초조해요 😟",
    "😳 당황": "당황스럽고 혼란스러워요 😳",
    "😔 외로움": "혼자인 기분이에요 😔",
    "😌 편안함": "마음이 편안해요 😌",
    "😩 지침": "너무 지치고 힘들어요 😩"
}

st.markdown("### 오늘 어떤 기분이셨나요?")
selected_emotion = st.radio(
    label="",
    options=["선택 안 함"] + list(emotion_options.keys()),
    horizontal=True,
    index=0
)

diary_text = st.text_area(
    "📝 오늘 하루 어땠나요?",
    height=200,
    max_chars=500,
    placeholder="ex.) 오늘은 너무 힘든 날이었다..."
)

if "diary_log" not in st.session_state:
    st.session_state.diary_log = []

def system_prompt():
    return "공감하는 AI 상담사처럼 짧고 다정하게 답해주세요."

def build_prompt(diary_text):
    return f"다음은 사용자의 감정일기입니다:\n\n{diary_text}"

def get_ai_response(diary_text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": build_prompt(diary_text)}
        ],
        temperature=0.5,
        max_tokens=500
    )
    return response.choices[0].message.content

def extract_emotion_tag(text):
    match = re.search(r"(기분이 좋아요|마음이 울적해요|짜증나고 화가 나요|좀 불안하고 초조해요|당황스럽고 혼란스러워요|혼자인 기분이에요|마음이 편안해요|너무 지치고 힘들어요)", text)
    return match.group(0) if match else "감정 미분류"

st.caption("🔍 당신의 감정을 AI가 따뜻하게 분석해드릴게요.")
if st.button("🔮 감정일기 분석 시작 (클릭)") and diary_text.strip():
    with st.spinner("AI가 당신의 이야기를 듣고 있어요..."):
        response = get_ai_response(diary_text)
        emotion_tag = emotion_options[selected_emotion] if selected_emotion != "선택 안 함" else extract_emotion_tag(response)
        st.session_state.diary_log.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "emotion": emotion_tag,
            "text": diary_text,
            "response": response
        })
        st.success("감정 분석이 완료되었어요!")

if st.session_state.diary_log:
    st.markdown("## 📒 최근 감정일기")
    for idx, entry in enumerate(reversed(st.session_state.diary_log[-5:])):
        entry_index = len(st.session_state.diary_log) - 1 - idx
        st.markdown(f"""
            <div class="emotion-card">
                <div class="emotion-title">🗓️ {entry['date']} | {entry['emotion']}</div>
                <div class="emotion-text"><b>내가 쓴 일기:</b><br>{entry['text']}</div>
                <div class="emotion-text"><b>AI 분석:</b><br>{entry['response']}</div>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("🤖 AI와 더 대화하기 (프리미엄 기능)", expanded=False):
            if st.session_state["is_premium_user"]:
                followup = st.text_area(f"AI에게 더 이야기해볼까요? ({entry['date']})", max_chars=300, key=f"followup_{entry_index}")
                if st.button("AI에게 보내기", key=f"send_followup_{entry_index}") and followup.strip():
                    with st.spinner("AI가 당신의 이야기를 듣고 있어요..."):
                        followup_response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": system_prompt()},
                                {"role": "user", "content": followup}
                            ],
                            temperature=0.5,
                            max_tokens=200
                        )
                        reply = followup_response.choices[0].message.content
                        st.markdown(f"**AI의 응답:**\n\n{reply}")
            else:
                st.info("이 기능은 프리미엄 사용자에게 제공됩니다. 곧 오픈 예정이에요! 💎")

        if st.button("❌ 삭제", key=f"delete_{entry_index}"):
            del st.session_state.diary_log[entry_index]
            st.experimental_rerun()

# 감정 캘린더
st.markdown("## 📅 감정 캘린더")

if st.session_state.diary_log:
    df = pd.DataFrame(st.session_state.diary_log)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        calendar_map = {}
        for _, row in df.iterrows():
            emoji_icon = ''.join([ch for ch in row["emotion"] if ch in "😀😢😠😟😳😔😌😩😊❤️"])
            date_key = row["date"].strftime("%Y-%m-%d")
            if date_key in calendar_map:
                calendar_map[date_key] += f" {emoji_icon}"
            else:
                calendar_map[date_key] = emoji_icon

        today = datetime.today()
        start_day = today - timedelta(days=29)
        dates = [start_day + timedelta(days=i) for i in range(30)]

        calendar_html = '<div class="calendar-box">'
        for i, date in enumerate(dates):
            date_str = date.strftime("%Y-%m-%d")
            emoji_icons = calendar_map.get(date_str, "⬜️")
            calendar_html += f"{emoji_icons}  "
            if (i + 1) % 7 == 0:
                calendar_html += "<br>"
        calendar_html += "</div>"

        st.markdown(calendar_html, unsafe_allow_html=True)
        st.caption("⬜️ 감정 기록이 없는 날이에요. 감정을 남겨보세요!")
    else:
        st.warning("⚠️ 감정일기 데이터에 날짜 정보가 없어요.")
else:
    st.info("아직 감정일기가 작성되지 않았어요. 오늘의 감정을 남겨보세요!")