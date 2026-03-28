import streamlit as st
from groq import Groq
import sqlite3
import os
from PIL import Image

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CoChef Pro", page_icon="🍕", layout="wide")

# Estilização CSS para manter o visual "Pano de Picnic" e cores
st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    [data-testid="stSidebar"] {
        background-image: url("https://www.transparenttextures.com/patterns/pinstriped-suit.png");
        background-color: #10b981;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #10b981;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CHAVE API ---
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "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")
MODELO_ATUAL = "llama-3.3-70b-versatile"

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect("cochef_web.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nome TEXT, username TEXT UNIQUE, senha TEXT, restricoes TEXT, gostos TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cardapio (id INTEGER PRIMARY KEY, user_id INTEGER, titulo TEXT, conteudo TEXT)")
    conn.commit()
    return conn

conn = iniciar_db()

# --- LÓGICA DE SESSÃO ---
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user_id = None
    st.session_state.username = ""

# --- COMPONENTES DE TELA ---
def tela_login():
    st.title("C🍕Chef")
    
    # Logo
    if os.path.exists("Logo CoChef.png"):
        st.image("Logo CoChef.png", width=200)
    
    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])
    
    with tab1:
        user = st.text_input("UserName", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar na Cozinha"):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE username=? AND senha=?", (user, senha))
            res = cursor.fetchone()
            if res:
                st.session_state.logado = True
                st.session_state.user_id = res[0]
                st.session_state.username = res[2]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

    with tab2:
        novo_nome = st.text_input("Nome")
        novo_user = st.text_input("Escolha um UserName")
        nova_senha = st.text_input("Senha", type="password")
        if st.button("Finalizar Cadastro"):
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO usuarios (nome, username, senha) VALUES (?,?,?)", (novo_nome, novo_user, nova_senha))
                conn.commit()
                st.success("Cadastro realizado! Vá para a aba Entrar.")
            except:
                st.error("UserName já existe.")

def area_principal():
    # Sidebar igual ao app anterior
    with st.sidebar:
        st.markdown(f"<h1 style='color:white;'>C🍕Chef</h1>", unsafe_allow_html=True)
        if os.path.exists("Logo CoChef.png"):
            st.image("Logo CoChef.png")
        
        st.write(f"### Olá chef {st.session_state.username}")
        st.divider()
        
        menu = st.radio("Navegação", ["👨‍🍳 Cozinha", "📖 Cardápio", "Sair"])
        
        if menu == "Sair":
            st.session_state.logado = False
            st.rerun()

    if menu == "👨‍🍳 Cozinha":
        st.header(f"Olá chef {st.session_state.username}")
        
        # Histórico de Chat (Simulado no browser)
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("O que vamos preparar hoje?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    client = Groq(api_key=GROQ_API_KEY)
                    response = client.chat.completions.create(
                        model=MODELO_ATUAL,
                        messages=[{"role": "system", "content": "Você é o CoChef, assistente gourmet."}] + 
                                 [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    )
                    full_response = response.choices[0].message.content
                    st.markdown(full_response)
                    
                    # Botão para salvar a última receita
                    if st.button("💾 Salvar esta Receita no Cardápio"):
                        cursor = conn.cursor()
                        tit = full_response.split('\n')[0][:40]
                        cursor.execute("INSERT INTO cardapio (user_id, titulo, conteudo) VALUES (?,?,?)", 
                                       (st.session_state.user_id, tit, full_response))
                        conn.commit()
                        st.toast("Receita salva com sucesso!")
                except:
                    st.error("Erro ao conectar com a Groq.")
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})

    elif menu == "📖 Cardápio":
        st.header("📖 Suas Receitas Salvas")
        cursor = conn.cursor()
        cursor.execute("SELECT titulo, conteudo FROM cardapio WHERE user_id=?", (st.session_state.user_id,))
        receitas = cursor.fetchall()
        
        if not receitas:
            st.info("Você ainda não salvou nada.")
        else:
            for tit, cont in receitas:
                with st.expander(f"🍴 {tit}"):
                    st.markdown(cont)

# --- EXECUÇÃO ---
if st.session_state.logado:
    area_principal()
else:
    tela_login()