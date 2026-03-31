import streamlit as st
from groq import Groq
import sqlite3
import os

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="CoChef Pro", page_icon="🍕", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #052e16; color: #ecfdf5; }
    section[data-testid="stSidebar"] { background-color: #064e3b !important; }
    h1, h2, h3, p { color: #ecfdf5 !important; font-family: 'Arial'; }
    .stButton>button {
        background-color: #10b981 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: bold !important;
    }
    .stChatMessage { background-color: #065f46 !important; border-radius: 15px !important; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect("cochef_v3.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nome TEXT, username TEXT UNIQUE, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cardapio (id INTEGER PRIMARY KEY, user_id INTEGER, titulo TEXT, conteudo TEXT)")
    conn.commit()
    return conn

db = iniciar_db()

# --- ESTADO DO USUÁRIO ---
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "user_id": None, "username": "", "messages": [], "ultima_resposta": ""})

# --- TELAS ---
def tela_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; font-size: 60px;'>C🍕Chef</h1>", unsafe_allow_html=True)
        aba1, aba2 = st.tabs(["Acessar Cozinha", "Novo Chef"])
        
        with aba1:
            u = st.text_input("UserName")
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
        st.write(f"### Bem-vindo, Chef **{st.session_state.username}**")
        st.divider()
        menu = st.radio("Navegar:", ["👨‍🍳 Cozinha (Chat)", "📖 Meu Cardápio"])
        if st.button("Sair da Conta"):
            st.session_state.update({"logado": False, "messages": [], "ultima_resposta": ""})
            st.rerun()

    if menu == "👨‍🍳 Cozinha (Chat)":
        st.title(f"Olá Chef {st.session_state.username}")
        
        # Histórico
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])

        # Input
        if prompt := st.chat_input("O que vamos cozinhar hoje?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)

            try:
                GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
                client = Groq(api_key=GROQ_API_KEY)
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": "Você é o CoChef, um assistente culinário profissional."}] + st.session_state.messages
                )
                resposta = res.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": resposta})
                st.session_state.ultima_resposta = resposta
                st.rerun() # Rerun para atualizar a tela com o histórico
            except Exception as e:
                st.error(f"Erro na API: {e}")

        # Botão de salvar (só aparece se houver resposta)
        if st.session_state.ultima_resposta:
            if st.button("💾 Salvar última receita no Cardápio"):
                conteudo = st.session_state.ultima_resposta
                titulo = conteudo.split('\n')[0][:40].replace('#', '').strip()
                db.execute("INSERT INTO cardapio (user_id, titulo, conteudo) VALUES (?,?,?)", 
                          (st.session_state.user_id, titulo, conteudo))
                db.commit()
                st.success("Receita salva com sucesso!")
                st.session_state.ultima_resposta = "" # Limpa para evitar duplicatas

    elif menu == "📖 Meu Cardápio":
        st.title("📖 Receitas Salvas")
        receitas = db.execute("SELECT titulo, conteudo FROM cardapio WHERE user_id=?", (st.session_state.user_id,)).fetchall()
        if not receitas: 
            st.info("Seu cardápio está vazio.")
        for t, c in receitas:
            with st.expander(f"🍴 {t}"): 
                st.write(c)
                if st.button(f"Excluir {t}", key=f"del_{t}"):
                    db.execute("DELETE FROM cardapio WHERE user_id=? AND titulo=?", (st.session_state.user_id, t))
                    db.commit()
                    st.rerun()

# --- EXECUÇÃO ---
if st.session_state.logado:
    painel_chef()
else:
    tela_login()

