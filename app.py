import streamlit as st
from groq import Groq
import sqlite3
import os

# --- CONFIGURAÇÃO VISUAL (ESTILO PROFISSIONAL) ---
st.set_page_config(page_title="CoChef Pro", page_icon="🍕", layout="wide")

st.markdown("""
    <style>
    /* Fundo Principal e Sidebar */
    .stApp { background-color: #052e16; color: #ecfdf5; }
    section[data-testid="stSidebar"] { background-color: #064e3b !important; }
    
    /* Títulos e Textos */
    h1, h2, h3, p { color: #ecfdf5 !important; font-family: 'Arial'; }
    
    /* Botões Gourmet */
    .stButton>button {
        background-color: #10b981 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        height: 3em !important;
        font-weight: bold !important;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #059669 !important; transform: scale(1.02); }

    /* Estilo das Mensagens de Chat */
    .stChatMessage { background-color: #065f46 !important; border-radius: 15px !important; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÃO DA API ---
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect("cochef_v2.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nome TEXT, username TEXT UNIQUE, senha TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS cardapio (id INTEGER PRIMARY KEY, user_id INTEGER, titulo TEXT, conteudo TEXT)")
    return conn

db = iniciar_db()

# --- ESTADO DO USUÁRIO ---
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "user_id": None, "username": "", "messages": []})

# --- TELAS ---
def tela_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; font-size: 60px;'>C🍕Chef</h1>", unsafe_allow_html=True)
        if os.path.exists("Logo CoChef.png"):
            st.image("Logo CoChef.png", use_container_width=True)
        
        aba1, aba2 = st.tabs(["Acessar Cozinha", "Novo Chef"])
        with aba1:
            u = st.text_input("UserName (Ex: s)")
            s = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                res = db.execute("SELECT id, username FROM usuarios WHERE username=? AND senha=?", (u, s)).fetchone()
                if res:
                    st.session_state.update({"logado": True, "user_id": res[0], "username": res[1]})
                    st.rerun()
                else: st.error("Chef não encontrado.")
        with aba2:
            n = st.text_input("Seu Nome")
            un = st.text_input("Escolha um UserName")
            ps = st.text_input("Crie uma Senha", type="password")
            if st.button("Finalizar Cadastro"):
                try:
                    db.execute("INSERT INTO usuarios (nome, username, senha) VALUES (?,?,?)", (n, un, ps))
                    db.commit()
                    st.success("Cadastro realizado! Use a aba Entrar.")
                except: st.error("Esse UserName já está em uso.")

def painel_chef():
    with st.sidebar:
        st.markdown("<h1 style='text-align: center;'>C🍕Chef</h1>", unsafe_allow_html=True)
        if os.path.exists("Logo CoChef.png"): st.image("Logo CoChef.png")
        st.write(f"### Bem-vindo, Chef **{st.session_state.username}**")
        st.divider()
        menu = st.radio("Navegar:", ["👨‍🍳 Cozinha (Chat)", "📖 Meu Cardápio"])
        if st.button("Sair da Conta"):
            st.session_state.logado = False
            st.rerun()

    if menu == "👨‍🍳 Cozinha (Chat)":
        st.title(f"Olá Chef {st.session_state.username}")
        
        # Exibição do Chat
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])

        if prompt := st.chat_input("O que vamos cozinhar hoje?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)

            try:
                client = Groq(api_key=GROQ_API_KEY)
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": f"Você é o CoChef. O usuário é o Chef {st.session_state.username}. Dê receitas incríveis."}] + st.session_state.messages
                )
                resposta = res.choices[0].message.content
                with st.chat_message("assistant"): st.write(resposta)
                st.session_state.messages.append({"role": "assistant", "content": resposta})
                
                # Opção de salvar
                if st.button("💾 Salvar esta Receita"):
                    tit = resposta.split('\n')[0][:40]
                    db.execute("INSERT INTO cardapio (user_id, titulo, conteudo) VALUES (?,?,?)", (st.session_state.user_id, tit, resposta))
                    db.commit()
                    st.toast("Receita enviada para o Cardápio!")
            except: st.error("Erro: Verifique sua chave API nos Secrets.")

    elif menu == "📖 Meu Cardápio":
        st.title("📖 Receitas Salvas")
        receitas = db.execute("SELECT titulo, conteudo FROM cardapio WHERE user_id=?", (st.session_state.user_id,)).fetchall()
        if not receitas: st.info("Seu cardápio está vazio. Peça uma receita na Cozinha!")
        for t, c in receitas:
            with st.expander(f"🍴 {t}"): st.write(c)

# --- EXECUÇÃO ---
if st.session_state.logado: painel_chef()
else: tela_login()
