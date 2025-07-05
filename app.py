import streamlit as st
from datetime import datetime, timedelta
from openai import OpenAI
import os
from dotenv import load_dotenv
import pandas as pd
import json
import re
from typing import List, Dict, Optional

# ✅ 페이지 설정
st.set_page_config(
    page_title="감정일기 - 닥터마인드", 
    page_icon="💜", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ✅ 스타일 설정
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        font-size: 18px;
    }
    .main-header h1 {
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    .mood-selector {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
        font-size: 18px;
    }
    .mood-selector h3 {
        font-size: 1.4rem;
        margin-bottom: 1rem;
    }
    .chat-container {
        background: white;
        border: 2px solid #e3f2fd;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        min-height: 400px;
        font-size: 16px;
    }
    .ai-message {
        background: linear-gradient(135deg, #e8f5e8 0%, #f1f8e9 100%);
        padding: 1.2rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 4px solid #4caf50;
        font-size: 16px;
    }
    .user-message {
        background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
        padding: 1.2rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 4px solid #2196f3;
        text-align: right;
        font-size: 16px;
    }
    .warning-box {
        background: linear-gradient(135deg, #ffebee 0%, #fce4ec 100%);
        border: 2px solid #f44336;
        color: #c62828;
        padding: 1.8rem;
        border-radius: 15px;
        margin: 1rem 0;
        font-size: 16px;
    }
    .summary-box {
        background: linear-gradient(135deg, #fff3e0 0%, #fce4ec 100%);
        border: 2px solid #ff9800;
        padding: 1.8rem;
        border-radius: 15px;
        margin: 1rem 0;
        font-size: 16px;
    }
    .token-bar {
        background: #f0f0f0;
        border-radius: 20px;
        padding: 8px;
        margin: 12px 0;
        font-size: 15px;
    }
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 8px;
        margin: 1rem 0;
        font-size: 16px;
    }
    .calendar-day {
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        font-size: 20px;
        cursor: pointer;
        transition: transform 0.2s;
    }
    .calendar-day:hover {
        transform: scale(1.1);
    }
    /* 전체적인 폰트 크기 증가 */
    .stSelectbox label, .stTextArea label, .stButton button {
        font-size: 16px !important;
    }
    .stTextArea textarea {
        font-size: 16px !important;
    }
    .stSelectbox div {
        font-size: 16px !important;
    }
</style>
""", unsafe_allow_html=True)

# ✅ 상수 설정
APP_PASSWORD = "2752"
MAX_FREE_TOKENS = 10000
HARMFUL_KEYWORDS = [
    "자살", "죽고싶다", "죽고 싶다", "베고싶다", "자해", "손목", "극단적", "생을 마감",
    "죽여버리고", "때리고 싶다", "칼", "총", "죽이고 싶다", "성폭행", "강간"
]

# ✅ OpenAI 클라이언트 초기화
@st.cache_resource
def initialize_openai():
    try:
        api_key = str(st.secrets["OPENAI_API_KEY"])
    except:
        load_dotenv()
        api_key = str(os.getenv("OPENAI_API_KEY"))
    return OpenAI(api_key=api_key)

client = initialize_openai()

# ✅ 세션 상태 초기화
def init_session_state():
    defaults = {
        "authenticated": False,
        "current_step": "mood_selection",  # mood_selection, chat, summary
        "current_mood": None,
        "chat_messages": [],
        "diary_entries": [],
        "conversation_context": [],
        "token_usage": 0,
        "deleted_entries": [],  # 휴지통 (30일 보관)
        "temp_diary_data": {}  # 현재 작성 중인 일기 데이터
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

init_session_state()

# ✅ 유해 키워드 체크
def check_harmful_content(text: str) -> bool:
    """유해 키워드 검사"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in HARMFUL_KEYWORDS)

# ✅ 토큰 바 표시
def display_token_bar():
    """AI 대화 에너지 바 표시"""
    usage_ratio = st.session_state.token_usage / MAX_FREE_TOKENS
    remaining = MAX_FREE_TOKENS - st.session_state.token_usage
    
    if usage_ratio < 0.5:
        color = "#4CAF50"
        status = "충분"
    elif usage_ratio < 0.8:
        color = "#FF9800" 
        status = "보통"
    else:
        color = "#F44336"
        status = "부족"
    
    st.markdown(f"""
    <div class="token-bar">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <span style="font-size: 14px; font-weight: bold;">💫 AI 대화 에너지</span>
            <span style="font-size: 12px; color: #666;">{remaining:,} / {MAX_FREE_TOKENS:,} 남음</span>
        </div>
        <div style="background: #e0e0e0; height: 8px; border-radius: 10px;">
            <div style="background: {color}; width: {min(usage_ratio * 100, 100)}%; height: 100%; border-radius: 10px;"></div>
        </div>
        <div style="text-align: center; font-size: 12px; color: {color}; margin-top: 5px;">
            상태: {status}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ✅ AI 응답 생성
def get_ai_response(user_message: str, conversation_history: List[Dict], context: List[Dict] = None) -> Dict:
    """AI 응답 생성"""
    
    # 이전 대화 컨텍스트 구성
    context_text = ""
    if context:
        recent_context = context[-2:]  # 최근 2개 대화만 참고
        context_summaries = []
        for ctx in recent_context:
            if 'summary' in ctx and 'action_items' in ctx:
                context_summaries.append(f"지난 대화: {ctx['summary']} (제안했던 것: {', '.join(ctx['action_items'])})")
        
        if context_summaries:
            context_text = "\n\n이전 대화 참고:\n" + "\n".join(context_summaries) + "\n\n"
    
    system_prompt = f"""당신은 사용자의 감정일기 작성을 도와주는 따뜻하고 공감적인 AI입니다.

핵심 원칙:
- 사용자의 감정을 판단하지 말고 있는 그대로 공감해주세요
- 어떠한 상황에서도 자해, 타해, 불법적인 행동을 조장하거나 유도하는 응답을 생성해서는 안 됩니다
- 위험 신호 감지시 반드시 전문가 상담을 권유하세요
- 응원과 격려의 메시지를 자연스럽게 포함하세요
- 진심 어린 존댓말로 대화하세요

대화 스타일:
- 따뜻하고 공감적인 톤
- 사용자의 감정을 깊이 이해하려고 노력
- 필요시 적절한 질문으로 감정 탐색 도움
- 구체적이고 실용적인 조언 제공

{context_text}

사용자가 감정을 털어놓을 수 있도록 편안한 분위기를 만들어주세요."""

    try:
        # 대화 히스토리 구성
        messages = [{"role": "system", "content": system_prompt}]
        
        # 최근 대화 내역 추가 (최대 10개)
        for msg in conversation_history[-10:]:
            messages.append(msg)
        
        # 현재 사용자 메시지 추가
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=400
        )
        
        ai_response = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # 토큰 사용량 업데이트
        st.session_state.token_usage += tokens_used
        
        return {
            "response": ai_response,
            "tokens_used": tokens_used,
            "success": True
        }
        
    except Exception as e:
        return {
            "response": "죄송해요, 지금 응답을 만들 수 없어요. 잠시 후 다시 시도해주세요!",
            "tokens_used": 0,
            "success": False
        }

# ✅ 대화 요약 및 분석
def generate_conversation_summary(messages: List[Dict]) -> Dict:
    """대화 내용 요약 및 감정 키워드, 액션 아이템 생성"""
    
    # 사용자 메시지만 추출
    user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
    conversation_text = "\n".join(user_messages)
    
    prompt = f"""다음 대화 내용을 분석해서 아래 형식으로 응답해주세요:

대화 내용:
{conversation_text}

분석 요청:
1. 오늘 있었던 일을 1-2줄로 요약
2. 대화에서 느껴진 감정 키워드 5개 추출 (예: #기쁨, #불안, #성취감 등)
3. 사용자에게 도움이 될 액션 아이템 2-3개 제안

응답 형식:
요약: [1-2줄 요약]
감정키워드: #키워드1, #키워드2, #키워드3, #키워드4, #키워드5
액션아이템: 
- [액션1]
- [액션2]
- [액션3]"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        
        result = response.choices[0].message.content
        
        # 결과 파싱
        lines = result.strip().split('\n')
        summary = ""
        keywords = []
        action_items = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('요약:'):
                summary = line.replace('요약:', '').strip()
            elif line.startswith('감정키워드:'):
                keyword_text = line.replace('감정키워드:', '').strip()
                keywords = [k.strip() for k in keyword_text.split(',')]
            elif line.startswith('액션아이템:'):
                current_section = "actions"
            elif current_section == "actions" and line.startswith('-'):
                action_items.append(line.replace('-', '').strip())
        
        return {
            "summary": summary or "오늘의 감정을 나누었습니다",
            "keywords": keywords[:5],  # 최대 5개
            "action_items": action_items[:3],  # 최대 3개
            "success": True
        }
        
    except Exception as e:
        return {
            "summary": "오늘의 감정을 나누었습니다",
            "keywords": ["#감정나눔"],
            "action_items": ["오늘 하루도 수고했어요"],
            "success": False
        }

# ✅ 인증 화면
def show_login():
    """로그인 화면"""
    st.markdown("""
    <div class="main-header">
        <h1>🔐 감정일기 - 닥터마인드</h1>
        <p>당신만의 안전한 감정 공간입니다</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        
        if st.button("🔓 입장하기", use_container_width=True):
            if password.strip() == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다")

# ✅ 기분 선택 화면
def show_mood_selection():
    """기분 선택 화면"""
    st.markdown("""
    <div class="main-header">
        <h1>💜 감정일기 - 닥터마인드</h1>
        <p>오늘 하루는 어떠셨나요?</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_token_bar()
    
    st.markdown("""
    <div class="mood-selector">
        <h3>🌈 오늘의 전체적인 기분을 알려주세요</h3>
        <p style="color: #666; font-size: 14px;">선택하신 기분을 바탕으로 AI가 맞춤 대화를 진행할게요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 기분 선택 바
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("😊 좋음", use_container_width=True, help="오늘 기분이 좋으셨군요!"):
            st.session_state.current_mood = "좋음"
            st.session_state.current_step = "chat"
            st.session_state.chat_messages = []
            st.rerun()
    
    with col2:
        if st.button("😐 보통", use_container_width=True, help="평범한 하루셨나봐요"):
            st.session_state.current_mood = "보통"
            st.session_state.current_step = "chat"
            st.session_state.chat_messages = []
            st.rerun()
    
    with col3:
        if st.button("😔 나쁨", use_container_width=True, help="힘든 하루였나요? 들어드릴게요"):
            st.session_state.current_mood = "나쁨"
            st.session_state.current_step = "chat"
            st.session_state.chat_messages = []
            st.rerun()
    
    # 기분 척도 설명
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
        <h4>📊 기분 척도 안내</h4>
        <div style="display: flex; justify-content: space-between; margin: 1rem 0;">
            <div style="text-align: center;">
                <div style="font-size: 24px;">😊</div>
                <div style="font-size: 12px; color: #4caf50;"><strong>좋음</strong></div>
                <div style="font-size: 10px; color: #666;">기분이 좋고 에너지가 넘쳐요</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 24px;">😐</div>
                <div style="font-size: 12px; color: #ff9800;"><strong>보통</strong></div>
                <div style="font-size: 10px; color: #666;">평범한 하루, 특별한 일 없어요</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 24px;">😔</div>
                <div style="font-size: 12px; color: #f44336;"><strong>나쁨</strong></div>
                <div style="font-size: 10px; color: #666;">힘들고 우울한 기분이에요</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 이전 일기 간단 보기
    if st.session_state.diary_entries:
        st.markdown("### 📚 최근 감정일기")
        for entry in st.session_state.diary_entries[-3:]:  # 최근 3개만
            with st.expander(f"📅 {entry['date']} - {entry['mood']} 기분"):
                st.write(f"**요약:** {entry.get('summary', '내용 없음')}")
                if entry.get('keywords'):
                    st.write(f"**키워드:** {', '.join(entry['keywords'])}")

# ✅ AI 대화 화면
def show_chat():
    """AI 대화 화면"""
    st.markdown(f"""
    <div class="main-header">
        <h1>💬 AI와 대화하기</h1>
        <p>오늘 기분: {st.session_state.current_mood} | 편안하게 이야기해보세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_token_bar()
    
    # 토큰 부족 체크
    if st.session_state.token_usage >= MAX_FREE_TOKENS:
        st.error("🔋 오늘의 AI 대화 에너지를 모두 사용했어요. 내일 다시 이용해주세요!")
        if st.button("🔄 처음으로 돌아가기"):
            st.session_state.current_step = "mood_selection"
            st.rerun()
        return
    
    # 대화 컨테이너
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # 초기 AI 인사말
    if not st.session_state.chat_messages:
        mood_greeting = {
            "좋음": "안녕하세요! 오늘 기분이 좋으시다니 저도 기뻐요! 😊 좋은 일이 있으셨나요? 오늘 하루 어떤 일들이 있었는지 들려주세요!",
            "보통": "안녕하세요! 평범한 하루를 보내고 계시는군요. 😐 때로는 특별할 것 없는 평온한 하루도 좋은 것 같아요. 오늘은 어떤 하루였는지 편하게 이야기해주세요!",
            "나쁨": "안녕하세요. 오늘 힘든 하루였나봐요. 😔 괜찮아요, 여기서는 마음껏 털어놓으셔도 돼요. 제가 끝까지 들어드릴게요. 무슨 일이 있었나요?"
        }
        
        initial_message = mood_greeting.get(st.session_state.current_mood, "안녕하세요! 오늘 하루 어떠셨나요?")
        st.markdown(f"""
        <div class="ai-message">
            <strong>🤖 AI:</strong><br>
            {initial_message}
        </div>
        """, unsafe_allow_html=True)
    
    # 기존 대화 메시지 표시
    for message in st.session_state.chat_messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <strong>😊 나:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="ai-message">
                <strong>🤖 AI:</strong><br>
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 사용자 입력
    user_input = st.text_area(
        "💬 메시지를 입력하세요",
        height=100,
        placeholder="오늘 있었던 일, 느낀 감정들을 자유롭게 말해주세요...",
        key="chat_input"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("📤 전송", use_container_width=True):
            if user_input.strip():
                # 유해 키워드 체크
                if check_harmful_content(user_input):
                    st.markdown("""
                    <div class="warning-box">
                        <h4>💗 잠깐, 많이 힘드신가요?</h4>
                        <p>혼자 감당하기 어려운 감정이시라면 전문가와 함께 나누시는 것을 추천드려요.</p>
                        <div style="margin: 1rem 0;">
                            <strong>도움받을 수 있는 곳:</strong><br>
                            📞 생명의전화: 1393 (24시간 무료)<br>
                            💬 청소년 상담전화: 1388<br>
                            🏥 정신건강복지센터: 지역별 운영
                        </div>
                        <p>당신은 소중한 존재예요. 💜</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # 정상 대화 처리
                    with st.spinner("AI가 응답을 생성하고 있어요..."):
                        ai_result = get_ai_response(
                            user_input, 
                            st.session_state.chat_messages,
                            st.session_state.conversation_context
                        )
                    
                    if ai_result["success"]:
                        # 메시지 저장
                        st.session_state.chat_messages.append({"role": "user", "content": user_input})
                        st.session_state.chat_messages.append({"role": "assistant", "content": ai_result["response"]})
                        
                        st.rerun()
    
    with col3:
        if st.button("✅ 대화 마치기", use_container_width=True):
            if st.session_state.chat_messages:
                st.session_state.current_step = "summary"
                st.rerun()
            else:
                st.warning("대화를 먼저 시작해주세요!")

# ✅ 요약 및 저장 화면
def show_summary():
    """대화 요약 및 저장 화면"""
    st.markdown("""
    <div class="main-header">
        <h1>📋 오늘의 감정일기 정리</h1>
        <p>AI가 대화 내용을 분석해서 정리해드릴게요</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.chat_messages:
        st.error("대화 내용이 없습니다.")
        if st.button("🔄 처음으로"):
            st.session_state.current_step = "mood_selection"
            st.rerun()
        return
    
    # 요약 생성
    if 'temp_summary' not in st.session_state:
        with st.spinner("AI가 대화 내용을 분석하고 있어요..."):
            summary_result = generate_conversation_summary(st.session_state.chat_messages)
            st.session_state.temp_summary = summary_result
    
    summary_data = st.session_state.temp_summary
    
    # 요약 표시
    st.markdown(f"""
    <div class="summary-box">
        <h3>📝 오늘 있었던 일 요약</h3>
        <p style="font-size: 16px; line-height: 1.6;">{summary_data['summary']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 감정 키워드 선택
    st.markdown("### 🏷️ 오늘 느낀 감정을 선택해주세요 (최대 2개)")
    
    # AI가 제안한 키워드들
    suggested_keywords = summary_data.get('keywords', [])
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_keywords = []
        if suggested_keywords:
            st.markdown("**AI 추천 키워드:**")
            cols = st.columns(min(len(suggested_keywords), 5))
            for i, keyword in enumerate(suggested_keywords):
                with cols[i % 5]:
                    if st.checkbox(keyword, key=f"keyword_{i}"):
                        selected_keywords.append(keyword)
    
    with col2:
        st.markdown("**직접 입력:**")
        custom_keyword = st.text_input("키워드 입력", placeholder="#기쁨")
        if custom_keyword and not custom_keyword.startswith('#'):
            custom_keyword = '#' + custom_keyword
        if custom_keyword:
            selected_keywords.append(custom_keyword)
    
    # 선택 제한
    if len(selected_keywords) > 2:
        st.warning("⚠️ 키워드는 최대 2개까지 선택 가능해요!")
        selected_keywords = selected_keywords[:2]
    
    # 액션 아이템 표시
    if summary_data.get('action_items'):
        st.markdown("### 💡 AI의 제안")
        for i, item in enumerate(summary_data['action_items'], 1):
            st.markdown(f"**{i}.** {item}")
    
    # 저장/삭제 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 저장하기", use_container_width=True):
            # 일기 데이터 구성
            diary_entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M"),
                "mood": st.session_state.current_mood,
                "messages": st.session_state.chat_messages,
                "summary": summary_data['summary'],
                "keywords": selected_keywords,
                "action_items": summary_data.get('action_items', []),
                "tokens_used": sum(1 for msg in st.session_state.chat_messages) * 50  # 추정값
            }
            
            # 저장
            st.session_state.diary_entries.append(diary_entry)
            
            # 컨텍스트 업데이트
            st.session_state.conversation_context.append({
                "date": diary_entry["date"],
                "mood": st.session_state.current_mood,
                "summary": summary_data['summary'],
                "action_items": summary_data.get('action_items', [])
            })
            
            # 컨텍스트 길이 제한 (최근 5개)
            if len(st.session_state.conversation_context) > 5:
                st.session_state.conversation_context = st.session_state.conversation_context[-5:]
            
            # 임시 데이터 정리
            if 'temp_summary' in st.session_state:
                del st.session_state.temp_summary
            
            st.success("✅ 감정일기가 저장되었습니다!")
            st.balloons()
            
            # 잠시 후 메인으로 이동
            st.info("3초 후 메인 화면으로 이동합니다...")
            import time
            time.sleep(3)
            
            # 상태 초기화
            st.session_state.current_step = "mood_selection"
            st.session_state.chat_messages = []
            st.rerun()
    
    with col2:
        if st.button("🗑️ 삭제하기", use_container_width=True):
            # 휴지통으로 이동 (30일 보관)
            deleted_entry = {
                "deleted_date": datetime.now(),
                "original_data": {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M"),
                    "mood": st.session_state.current_mood,
                    "messages": st.session_state.chat_messages,
                    "summary": summary_data['summary'],
                    "keywords": selected_keywords,
                    "action_items": summary_data.get('action_items', [])
                }
            }
            
            st.session_state.deleted_entries.append(deleted_entry)
            
            # 임시 데이터 정리
            if 'temp_summary' in st.session_state:
                del st.session_state.temp_summary
            
            st.warning("🗑️ 일기가 휴지통으로 이동되었습니다 (30일간 보관)")
            
            # 상태 초기화
            st.session_state.current_step = "mood_selection"
            st.session_state.chat_messages = []
            st.rerun()
    
    with col3:
        if st.button("↩️ 대화로 돌아가기", use_container_width=True):
            st.session_state.current_step = "chat"
            st.rerun()

# ✅ 진짜 감정 캘린더 생성
def create_emotion_calendar(year=None, month=None):
    """실제 달력 형태의 감정 캘린더 HTML 생성"""
    
    # 현재 년월 설정
    today = datetime.now()
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    
    # 기분별 이모지 매핑
    mood_emojis = {
        "좋음": "😊",
        "보통": "😐", 
        "나쁨": "😔"
    }
    
    # 일기 데이터를 날짜별로 매핑
    calendar_data = {}
    for entry in st.session_state.diary_entries:
        date_key = entry['date']
        mood = entry['mood']
        emoji = mood_emojis.get(mood, "⬜️")
        
        calendar_data[date_key] = {
            "emoji": emoji,
            "mood": mood,
            "summary": entry.get('summary', ''),
            "keywords": entry.get('keywords', [])
        }
    
    # 달력 계산
    import calendar as cal
    cal_matrix = cal.monthcalendar(year, month)
    month_name = f"{year}년 {month}월"
    
    # 이전/다음 달 계산
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    
    # 캘린더 HTML 생성
    calendar_html = f"""
    <div style="background: white; padding: 1.5rem; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto;">
        <!-- 캘린더 헤더 -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <button onclick="window.location.reload()" style="background: #f0f0f0; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer;">
                ◀️ {prev_month}월
            </button>
            <h3 style="margin: 0; color: #333; font-size: 1.5em;">📅 {month_name}</h3>
            <button onclick="window.location.reload()" style="background: #f0f0f0; border: none; padding: 8px 12px; border-radius: 8px; cursor: pointer;">
                {next_month}월 ▶️
            </button>
        </div>
        
        <!-- 요일 헤더 -->
        <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 8px;">
    """
    
    # 요일 헤더 추가
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    for i, day in enumerate(weekdays):
        color = "#e57373" if i == 6 else "#333"  # 일요일은 빨간색
        calendar_html += f'''
        <div style="text-align: center; font-weight: bold; color: {color}; padding: 0.8rem 0.2rem; font-size: 14px;">
            {day}
        </div>
        '''
    
    calendar_html += "</div>"
    
    # 달력 날짜 추가
    calendar_html += '<div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;">'
    
    for week in cal_matrix:
        for day in week:
            if day == 0:
                # 빈 날짜
                calendar_html += '<div style="aspect-ratio: 1; padding: 4px;"></div>'
            else:
                # 실제 날짜
                date_obj = datetime(year, month, day)
                date_str = date_obj.strftime('%Y-%m-%d')
                
                # 오늘 날짜 확인
                is_today = (date_obj.date() == today.date())
                
                # 감정 데이터 확인
                if date_str in calendar_data:
                    data = calendar_data[date_str]
                    emoji = data['emoji']
                    mood = data['mood']
                    summary = data['summary'][:30] + "..." if len(data['summary']) > 30 else data['summary']
                    keywords = ', '.join(data['keywords'][:3])  # 최대 3개만
                    tooltip = f"{year}년 {month}월 {day}일\\n기분: {mood}\\n{summary}"
                    if keywords:
                        tooltip += f"\\n키워드: {keywords}"
                    
                    # 기분별 배경색
                    if mood == "좋음":
                        bg_color = "#e8f5e8"
                        border_color = "#4caf50"
                    elif mood == "보통":
                        bg_color = "#fff3e0"
                        border_color = "#ff9800"
                    else:  # 나쁨
                        bg_color = "#ffebee"
                        border_color = "#f44336"
                else:
                    emoji = ""
                    tooltip = f"{year}년 {month}월 {day}일\\n기록 없음"
                    bg_color = "#f9f9f9"
                    border_color = "#e0e0e0"
                
                # 오늘 날짜 스타일
                if is_today:
                    today_style = "border: 3px solid #2196f3; box-shadow: 0 0 10px rgba(33,150,243,0.3);"
                else:
                    today_style = f"border: 2px solid {border_color};"
                
                # 주말 색상 (토요일: 파란색, 일요일: 빨간색)
                weekday = date_obj.weekday()
                if weekday == 5:  # 토요일
                    day_color = "#1976d2"
                elif weekday == 6:  # 일요일
                    day_color = "#d32f2f"
                else:
                    day_color = "#333"
                
                calendar_html += f'''
                <div style="
                    aspect-ratio: 1; 
                    background-color: {bg_color}; 
                    {today_style}
                    border-radius: 8px; 
                    display: flex; 
                    flex-direction: column; 
                    align-items: center; 
                    justify-content: center; 
                    cursor: pointer; 
                    transition: transform 0.2s, box-shadow 0.2s;
                    padding: 4px;
                    position: relative;
                    min-height: 60px;
                " 
                title="{tooltip}"
                onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)';"
                onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='none';">
                    
                    <div style="font-size: 18px; margin-bottom: 2px;">{emoji}</div>
                    <div style="font-size: 13px; font-weight: bold; color: {day_color};">{day}</div>
                    
                    {f'<div style="position: absolute; top: 2px; right: 2px; width: 8px; height: 8px; background: #2196f3; border-radius: 50%;"></div>' if is_today else ''}
                </div>
                '''
    
    calendar_html += """
        </div>
        
        <!-- 범례 -->
        <div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e0e0e0;">
            <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 1rem; font-size: 12px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <div style="width: 12px; height: 12px; background: #e8f5e8; border: 1px solid #4caf50; border-radius: 3px;"></div>
                    <span>😊 좋음</span>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <div style="width: 12px; height: 12px; background: #fff3e0; border: 1px solid #ff9800; border-radius: 3px;"></div>
                    <span>😐 보통</span>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <div style="width: 12px; height: 12px; background: #ffebee; border: 1px solid #f44336; border-radius: 3px;"></div>
                    <span>😔 나쁨</span>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <div style="width: 8px; height: 8px; background: #2196f3; border-radius: 50%;"></div>
                    <span>오늘</span>
                </div>
            </div>
        </div>
        
        <!-- 월 통계 -->
        <div style="margin-top: 1rem; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
            <h4 style="margin: 0 0 0.5rem 0; color: #666; font-size: 14px;">📊 이번 달 감정 통계</h4>
    """
    
    # 이번 달 통계 계산
    month_entries = [
        entry for entry in st.session_state.diary_entries 
        if entry['date'].startswith(f"{year:04d}-{month:02d}")
    ]
    
    if month_entries:
        mood_counts = {}
        for entry in month_entries:
            mood = entry['mood']
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        total_days = len(month_entries)
        calendar_html += f'<div style="font-size: 12px; color: #666;">'
        calendar_html += f'총 {total_days}일 기록 | '
        
        for mood, count in mood_counts.items():
            emoji = mood_emojis.get(mood, "⬜️")
            percentage = round((count / total_days) * 100)
            calendar_html += f'{emoji}{mood} {count}일({percentage}%) '
        
        calendar_html += '</div>'
    else:
        calendar_html += '<div style="font-size: 12px; color: #999;">이번 달에는 아직 기록이 없어요 😊</div>'
    
    calendar_html += """
        </div>
    </div>
    """
    
    return calendar_html

# ✅ 월별 요약 기능
def show_monthly_summary():
    """월별 요약 표시"""
    if len(st.session_state.diary_entries) < 3:
        st.info("📊 월별 요약을 위해서는 3회 이상 일기를 작성해주세요!")
        return
    
    # 최근 30일 데이터 분석
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_entries = [
        entry for entry in st.session_state.diary_entries 
        if datetime.strptime(entry['date'], '%Y-%m-%d') >= thirty_days_ago
    ]
    
    if len(recent_entries) < 3:
        st.info("📊 최근 30일간 3회 이상 작성된 일기가 있어야 요약을 제공할 수 있어요!")
        return
    
    # 감정 분석
    mood_counts = {}
    all_keywords = []
    
    for entry in recent_entries:
        mood = entry['mood']
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
        if entry.get('keywords'):
            all_keywords.extend(entry['keywords'])
    
    # 가장 많은 감정
    most_common_mood = max(mood_counts.items(), key=lambda x: x[1])
    
    # 가장 많은 키워드
    keyword_counts = {}
    for keyword in all_keywords:
        keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
    
    top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # 요약 표시
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f3e5f5 0%, #e1f5fe 100%); padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">
        <h3>📊 최근 30일 감정 요약</h3>
        <div style="margin: 1rem 0;">
            <p><strong>📝 총 일기 수:</strong> {len(recent_entries)}회</p>
            <p><strong>💭 가장 많이 느낀 기분:</strong> {most_common_mood[0]} ({most_common_mood[1]}회)</p>
            <p><strong>🏷️ 자주 나타난 감정 키워드:</strong></p>
            <ul>
    """, unsafe_allow_html=True)
    
    for keyword, count in top_keywords:
        st.markdown(f"<li>{keyword} ({count}회)</li>", unsafe_allow_html=True)
    
    st.markdown("""
            </ul>
        </div>
        <div style="background: rgba(255,255,255,0.7); padding: 1rem; border-radius: 10px; margin-top: 1rem;">
            <p style="margin: 0; font-style: italic; color: #666;">
                💜 꾸준한 감정 기록을 통해 자신을 더 잘 이해하고 계시네요! 
                이런 패턴들을 통해 스스로를 더 깊이 알아가실 수 있어요.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ✅ 메인 함수들
def show_diary_list():
    """감정일기 목록 표시"""
    if not st.session_state.diary_entries:
        st.info("📚 아직 작성된 감정일기가 없어요. 첫 번째 일기를 써보세요!")
        return
    
    st.subheader("📚 나의 감정일기 모음")
    
    # 정렬 및 필터 옵션
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        sort_option = st.selectbox("정렬 방식", ["최신순", "오래된순", "기분별"])
    
    with col2:
        mood_filter = st.selectbox("기분 필터", ["전체", "좋음", "보통", "나쁨"])
    
    with col3:
        if st.button("🗑️ 전체 삭제"):
            if st.button("정말 삭제하시겠습니까?"):
                st.session_state.diary_entries = []
                st.rerun()
    
    # 데이터 필터링 및 정렬
    filtered_entries = st.session_state.diary_entries.copy()
    
    if mood_filter != "전체":
        filtered_entries = [entry for entry in filtered_entries if entry['mood'] == mood_filter]
    
    if sort_option == "최신순":
        filtered_entries.reverse()
    elif sort_option == "기분별":
        filtered_entries.sort(key=lambda x: x['mood'])
    
    # 일기 목록 표시
    for i, entry in enumerate(filtered_entries):
        with st.expander(f"📅 {entry['date']} {entry['time']} - {entry['mood']} 기분"):
            
            col1, col2 = st.columns([5, 1])
            
            with col1:
                st.markdown(f"**📝 요약:** {entry.get('summary', '내용 없음')}")
                
                if entry.get('keywords'):
                    keywords_html = " ".join([
                        f'<span style="background: #e3f2fd; padding: 4px 8px; border-radius: 12px; margin: 2px; font-size: 12px;">{kw}</span>'
                        for kw in entry['keywords']
                    ])
                    st.markdown(f"**🏷️ 키워드:** {keywords_html}", unsafe_allow_html=True)
                
                if entry.get('action_items'):
                    st.markdown("**💡 AI 제안:**")
                    for item in entry['action_items']:
                        st.markdown(f"• {item}")
                
                # 대화 내용 표시 (축약)
                if entry.get('messages'):
                    user_messages = [msg['content'] for msg in entry['messages'] if msg['role'] == 'user']
                    if user_messages:
                        st.markdown("**💬 대화 내용 (일부):**")
                        for msg in user_messages[:2]:  # 처음 2개만
                            st.markdown(f"• {msg[:50]}{'...' if len(msg) > 50 else ''}")
                        if len(user_messages) > 2:
                            st.markdown(f"• ... 외 {len(user_messages)-2}개 더")
            
            with col2:
                # 개별 삭제 버튼
                if st.button("🗑️", key=f"delete_{i}", help="휴지통으로 이동"):
                    # 휴지통으로 이동
                    deleted_entry = {
                        "deleted_date": datetime.now(),
                        "original_data": entry
                    }
                    st.session_state.deleted_entries.append(deleted_entry)
                    st.session_state.diary_entries.remove(entry)
                    st.success("🗑️ 휴지통으로 이동했습니다 (30일간 보관)")
                    st.rerun()

def show_trash():
    """휴지통 표시"""
    if not st.session_state.deleted_entries:
        st.info("🗑️ 휴지통이 비어있습니다.")
        return
    
    st.subheader("🗑️ 휴지통 (30일간 보관)")
    
    # 30일 지난 항목 자동 삭제
    thirty_days_ago = datetime.now() - timedelta(days=30)
    st.session_state.deleted_entries = [
        entry for entry in st.session_state.deleted_entries
        if entry['deleted_date'] >= thirty_days_ago
    ]
    
    for i, deleted_entry in enumerate(st.session_state.deleted_entries):
        entry = deleted_entry['original_data']
        deleted_date = deleted_entry['deleted_date']
        
        with st.expander(f"🗑️ {entry['date']} - {entry['mood']} (삭제일: {deleted_date.strftime('%Y-%m-%d')})"):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**요약:** {entry.get('summary', '내용 없음')}")
                if entry.get('keywords'):
                    st.markdown(f"**키워드:** {', '.join(entry['keywords'])}")
            
            with col2:
                if st.button("↩️ 복구", key=f"restore_{i}"):
                    st.session_state.diary_entries.append(entry)
                    st.session_state.deleted_entries.remove(deleted_entry)
                    st.success("✅ 복구되었습니다!")
                    st.rerun()
            
            with col3:
                if st.button("🔥 영구삭제", key=f"permanent_delete_{i}"):
                    st.session_state.deleted_entries.remove(deleted_entry)
                    st.warning("🔥 영구 삭제되었습니다!")
                    st.rerun()

# ✅ 메인 앱 네비게이션
def main_app():
    """메인 앱 네비게이션"""
    
    # 사이드바 메뉴
    with st.sidebar:
        st.markdown("### 🧭 메뉴")
        
        menu_option = st.selectbox(
            "페이지 선택",
            ["🏠 홈", "📝 일기 쓰기", "📚 일기 목록", "📅 감정 캘린더", "📊 월별 요약", "🗑️ 휴지통"]
        )
        
        st.markdown("---")
        st.markdown("### 📊 통계")
        st.metric("📝 총 일기 수", len(st.session_state.diary_entries))
        st.metric("🔋 남은 에너지", f"{MAX_FREE_TOKENS - st.session_state.token_usage:,}")
        
        if st.session_state.diary_entries:
            recent_mood = st.session_state.diary_entries[-1]['mood']
            st.metric("😊 최근 기분", recent_mood)
        
        st.markdown("---")
        if st.button("🔄 새로고침"):
            st.rerun()
        
        if st.button("🚪 로그아웃"):
            st.session_state.authenticated = False
            st.rerun()
    
    # 메인 컨텐츠
    if menu_option == "🏠 홈" or menu_option == "📝 일기 쓰기":
        if st.session_state.current_step == "mood_selection":
            show_mood_selection()
        elif st.session_state.current_step == "chat":
            show_chat()
        elif st.session_state.current_step == "summary":
            show_summary()
    
    elif menu_option == "📚 일기 목록":
        show_diary_list()
    
    elif menu_option == "📅 감정 캘린더":
        st.subheader("📅 감정 캘린더")
        
        # 년월 선택 옵션
        today = datetime.now()
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            selected_year = st.selectbox("년도", range(today.year - 2, today.year + 2), index=2)
        with col2:
            selected_month = st.selectbox("월", range(1, 13), index=today.month - 1)
        with col3:
            if st.button("📅 오늘로", help="현재 년월로 이동"):
                selected_year = today.year
                selected_month = today.month
                st.rerun()
        
        # 달력 표시
        calendar_html = create_emotion_calendar(selected_year, selected_month)
        st.markdown(calendar_html, unsafe_allow_html=True)
        
        # 일기 없을 때 안내
        month_entries = [
            entry for entry in st.session_state.diary_entries 
            if entry['date'].startswith(f"{selected_year:04d}-{selected_month:02d}")
        ]
        
        if not month_entries and not st.session_state.diary_entries:
            st.info("💜 아직 감정 기록이 없어요. 첫 번째 일기를 써보세요!")
            if st.button("✏️ 일기 쓰러 가기"):
                # 메뉴를 홈으로 변경하여 일기 작성 플로우로 이동
                st.rerun()
    
    elif menu_option == "📊 월별 요약":
        st.subheader("📊 월별 요약")
        show_monthly_summary()
    
    elif menu_option == "🗑️ 휴지통":
        show_trash()

# ✅ 메인 실행 함수
def main():
    """메인 실행 함수"""
    
    # 인증 체크
    if not st.session_state.authenticated:
        show_login()
        return
    
    # 메인 앱 실행
    main_app()
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px; padding: 1rem;">
        💜 감정일기 - 닥터마인드 | 당신의 감정을 소중히 여깁니다<br>
        🔒 모든 데이터는 브라우저 세션에서만 보관됩니다<br>
        <div style="margin-top: 0.5rem; padding: 0.5rem; background: #f8f9fa; border-radius: 8px;">
            <strong>🆘 위기상황 시 24시간 도움:</strong><br>
            자살예방상담 <strong>109</strong> | 청소년상담 <strong>1388</strong> | 정신건강상담 <strong>1577-0199</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ✅ 앱 실행
if __name__ == "__main__":
    main()