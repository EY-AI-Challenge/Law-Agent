import streamlit as st
import streamlit.components.v1 as components

# Set Page Config
st.set_page_config(page_title="EY Law Agent", page_icon="⚖️", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for EY styling
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #1a1a24;
        color: #ffffff;
    }
    
    /* Top Navigation bar simulation */
    .top-nav {
        display: flex;
        align-items: center;
        background-color: #252533;
        padding: 10px 20px;
        margin-top: -50px;
        margin-bottom: 20px;
        border-bottom: 1px solid #333344;
    }
    .ey-logo {
        color: #ffe600;
        font-weight: bold;
        font-size: 20px;
        margin-right: 30px;
        display: flex;
        align-items: center;
    }
    .nav-links {
        display: flex;
        gap: 20px;
        color: #aaaaaa;
        font-size: 14px;
        flex-grow: 1;
    }
    .nav-links span.active {
        color: #ffe600;
        border-bottom: 2px solid #ffe600;
        padding-bottom: 5px;
    }
    
    /* Sub Nav */
    .sub-nav {
        display: flex;
        gap: 30px;
        padding: 0 20px;
        margin-bottom: 20px;
        color: #aaaaaa;
        font-size: 14px;
        border-bottom: 1px solid #333344;
    }
    .sub-nav span.active {
        color: #ffe600;
        border-bottom: 2px solid #ffe600;
        padding-bottom: 10px;
    }

    /* Override Streamlit UI Elements */
    div.stButton > button {
        background-color: #1a1a24;
        color: #aaaaaa;
        border: 1px solid #555566;
        border-radius: 4px;
    }
    div.stButton > button:hover {
        background-color: #252533;
        color: #ffe600;
        border-color: #ffe600;
    }
    
    .metric-pill {
        display: inline-block;
        background-color: #252533;
        padding: 5px 15px;
        border-radius: 15px;
        margin-right: 10px;
        font-size: 12px;
        color: #aaaaaa;
    }
    .metric-value {
        color: #ffe600;
        font-weight: bold;
        margin-right: 5px;
    }

    /* Chat styling */
    .chat-bubble-sys {
        background-color: #252533;
        border-left: 3px solid #ffe600;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        font-size: 14px;
    }
    .chat-bubble-user {
        border: 1px solid #555566;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        font-size: 14px;
        color: #ffe600;
    }
</style>
""", unsafe_allow_html=True)

# Top Bar HTML
st.markdown("""
<div class="top-nav">
    <div class="ey-logo">
        <span style="font-size: 24px; margin-right: 8px;">🔶</span> 
        <div style="line-height: 1;">Law Agent<br><span style="font-size: 10px; font-weight: normal; color: #aaaaaa;">Shape the future with confidence</span></div>
    </div>
    <div class="nav-links">
        <span class="active">Insights</span>
        <span>Serviços</span>
        <span>Indústrias</span>
        <span>Carreiras</span>
        <span>Sobre nós</span>
    </div>
    <div style="color: #aaaaaa; font-size: 12px;">Portugal</div>
</div>
<div class="sub-nav">
    <span class="active">Código do Trabalho</span>
    <span>Código Civil</span>
    <span>AI Assistant</span>
    <div style="margin-left: auto;">Law Statistics <span style="color:#ffe600;">●</span></div>
</div>
""", unsafe_allow_html=True)

# Main layout
col_main, col_chat = st.columns([3, 1], gap="large")

with col_main:
    # Controls row
    c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 1, 1, 1])
    with c1:
        st.text_input("Search", placeholder="Pesquisar artigo ou lei...", label_visibility="collapsed")
    with c2:
        st.button("Cód. Trabalho", use_container_width=True)
    with c3:
        st.button("Código Civil", use_container_width=True)
    with c4:
        st.button("Decretos-Lei", use_container_width=True)
    with c5:
        st.button("Exportar", use_container_width=True)
    with c6:
        st.button("Expandir", use_container_width=True)
        
    st.markdown("""
        <div style="margin: 15px 0;">
            <div class="metric-pill"><span class="metric-value">247</span> documentos legais</div>
            <div class="metric-pill"><span class="metric-value">1,842</span> referências</div>
            <div class="metric-pill"><span class="metric-value">34</span> clusters</div>
        </div>
    """, unsafe_allow_html=True)

    # Graph
    try:
        with open("legal_network.html", "r", encoding="utf-8") as f:
            html_data = f.read()
        components.html(html_data, height=600, scrolling=True)
    except FileNotFoundError:
        st.warning("Graph file not found. Ensure `legal_network.html` is generated.")
        
    # Legend
    st.markdown("""
    <div style="background-color: #252533; padding: 10px; border-radius: 5px; width: fit-content; font-size: 12px; color: #aaaaaa; border: 1px solid #333344">
        <div><span style="color: #ffe600;">●</span> Código do Trabalho</div>
        <div><span style="color: #4da6ff;">●</span> Código Civil</div>
        <div><span style="color: #888888;">●</span> Decreto-Lei</div>
        <div><span style="color: #ff4d4d;">●</span> Nó central (hub)</div>
    </div>
    """, unsafe_allow_html=True)

with col_chat:
    st.markdown("""
    <div style='display:flex; justify-content:space-between; margin-bottom:20px; font-size: 14px;'>
        <span><b>AI assistant</b></span>
        <span style='background:#ffe600; color:#000; padding:2px 8px; border-radius:10px; font-size:12px; font-weight:bold;'>GPT-4o</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Mocking the chat history using custom bubbles to mimic design
    st.markdown("""
    <div class="chat-bubble-sys">
        Olá! Sou o assistente legal da EY. Posso ajudar-te a explorar as relações entre o <b style="color:#ffe600;">Código do Trabalho</b> e o <b style="color:#4da6ff;">Código Civil</b>.<br><br>
        <span style="color:#80e060; font-size:12px; border: 1px solid #80e060; padding: 5px; display: inline-block; border-radius: 4px;">Clica num nó do grafo para ver detalhes e analisar com IA.</span>
    </div>
    
    <div class="chat-bubble-user">
        Quais os artigos do Código Civil mais referenciados pelo Código do Trabalho?
    </div>
    
    <div class="chat-bubble-sys">
        Os artigos com maior índice de citação cruzada são:<br><br>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #555566; padding:8px 0;"><span>Art. 217.º CC</span><span style="color:#ffe600;">89×</span></div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #555566; padding:8px 0;"><span>Art. 334.º CC</span><span style="color:#aaaaaa;">45×</span></div>
        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #555566; padding:8px 0;"><span>Art. 762.º CC</span><span style="color:#aaaaaa;">38×</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat input at bottom
    st.text_input("Ask", placeholder="Pergunta sobre a rede legal...", label_visibility="collapsed")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("Conflitos CT/CC")
    with c2:
        st.button("Clusters")
    with c3:
        st.button("Influência")
    st.button("Inconsistências")