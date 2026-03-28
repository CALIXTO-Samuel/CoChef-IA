import streamlit as st
from groq import Groq
import sqlite3
import os

# --- 1. CONFIGURAÇÃO VISUAL GOURMET ---
st.set_page_config(page_title="CoChef Pro", page_icon="🍕", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #052e16; color: #ecfdf5; }
    section[data-testid="stSidebar"] { background-color: #064e3b !important; }
    h1, h2, h3, span, p { color: #ecfdf5 !important; font-family: 'Arial'; }
    .stButton>button {
        background-color: #10b981 !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        height: 3em !important;
        width: 100%;
    }
    .stChatInputContainer { padding-bottom: 20px; }
    /* Estilo para as receitas no cardápio */
    .stExpander { background-color: #065f46 !important; border: 1px solid #10b981 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO COM BANCO DE DADOS ---
def conectar_db():
    conn = sqlite3.connect("cochef_v3.db", check_same_thread=False)
    return conn

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT, username TEXT UNIQUE, senha TEXT
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardapio (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, titulo TEXT, conteudo TEXT
        )""")
    conn.commit()
    conn.close()

inicializar_db()

# --- 3. GESTÃO DE SESSÃO (MEMÓRIA DO SITE) ---
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. FUNÇÕES DE TELA ---
def tela_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; font-size: 50px;'>C🍕Chef</h1>", unsafe_allow_html=True)
        if os.path.exists("Logo CoChef.png"):
            st.image("Logo CoChef.png", use_container_width=True)
        
        tab1, tab2 = st.tabs(["Acessar Cozinha", "Novo Chef"])
        
        with tab1:
            u = st.text_input("UserName", placeholder="Seu usuário")
            s = st.text_input("Senha", type="password", placeholder="Sua senha")
            if st.button("Entrar"):
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute("SELECT id, username FROM usuarios WHERE username=? AND senha=?", (u, s))
                user = cursor.fetchone()
                conn.close()
                if user:
                    st.session_state.logado = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

        with tab2:
            n = st.text_input("Nome Completo")
            un = st.text_input("Escolha seu UserName (Ex: s)")
            ps = st.text_input("Crie uma Senha", type="password")
            if st.button("Finalizar Cadastro"):
                if n and un and ps:
                    try:
                        conn = conectar_db()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (nome, username, senha) VALUES (?,?,?)", (n, un, ps))
                        conn.commit()
                        conn.close()
                        st.success("Chef cadastrado com sucesso! Use a aba 'Entrar'.")
                    except:
                        st.error("Este UserName já existe. Escolha outro.")
                else:
                    st.warning("Preencha todos os campos.")

def painel_chef():
    with st.sidebar:
        st.markdown("<h1 style='text-align: center;'>C🍕Chef</h1>", unsafe_allow_html=True)
        if os.path.exists("Logo CoChef.png"):
            st.image("Logo CoChef.png")
        st.write(f"### Chef: **{st.session_state.username}**")
        st.divider()
        menu = st.radio("Navegação:", ["👨‍🍳 Cozinha", "📖 Cardápio"])
        st.divider()
        if st.button("Sair"):
            st.session_state.logado = False
            st.session_state.messages = []
            st.rerun()

    if menu == "👨‍🍳 Cozinha":
        st.title(f"Bem-vindo, Chef {st.session_state.username}!")
        
        # Mostrar histórico de chat
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        # Input do Chat
        if prompt := st.chat_input("O que vamos preparar hoje?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    # Pega a chave dos secrets do Streamlit
                    api_key = st.secrets.get("GROQ_API_KEY", "")
                    client = Groq(api_key=api_key)
                    
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": f"Você é o CoChef, um assistente gourmet profissional. O usuário é o Chef {st.session_state.username}."}] + st.session_state.messages
                    )
                    full_response = response.choices[0].message.content
                    st.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.rerun() # Atualiza para fixar a resposta na tela
                except Exception as e:
                    st.error(f"Erro ao conectar com a IA. Verifique os Secrets. {e}")

        # BOTÃO SALVAR (Sempre aparece abaixo da última resposta da IA)
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            if st.button("💾 Salvar esta Receita no meu Cardápio"):
                conteudo = st.session_state.messages[-1]["content"]
                titulo = conteudo.split('\n')[0].replace('#', '').strip()[:40]
                if not titulo: titulo = "Receita Especial"
                
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cardapio (user_id, titulo, conteudo) VALUES (?,?,?)", 
                               (st.session_state.user_id, titulo, conteudo))
                conn.commit()
                conn.close()
                st.success(f"Receita '{titulo}' salva com sucesso!")

    elif menu == "📖 Cardápio":
        st.title("📖 Suas Receitas Salvas")
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT titulo, conteudo FROM cardapio WHERE user_id=? ORDER BY id DESC", (st.session_state.user_id,))
        receitas = cursor.fetchall()
        conn.close()

        if not receitas:
            st.info("Seu cardápio ainda está vazio. Gere uma receita na Cozinha e clique em salvar!")
        else:
            for tit, cont in receitas:
                with st.expander(f"🍴 {tit}"):
                    st.markdown(cont)

# --- 5. EXECUÇÃO ---
if st.session_state.logado:
    painel_chef()
else:
    tela_login()
