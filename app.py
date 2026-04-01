import streamlit as st
from groq import Groq
import sqlite3
import os

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="CoChef Pro", page_icon="🍕", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #052e16; color: #ecfdf5; }
    section[data-testid="sidebar"] { background-color: #064e3b !important; }
    h1, h2, h3, p { color: #ecfdf5 !important; font-family: 'Arial'; }
    .stButton>button {
        background-color: #10b981 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        width: 100%;
    }
    .stChatMessage { background-color: #065f46 !important; border-radius: 15px !important; margin-bottom: 10px; }
    .recipe-card { background-color: #064e3b; padding: 20px; border-radius: 15px; border-left: 5px solid #10b981; }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect("cochef_v3.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nome TEXT, username TEXT UNIQUE, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cardapio (id INTEGER PRIMARY KEY, user_id INTEGER, titulo TEXT, conteudo TEXT)")
    conn.commit()
    return conn, cursor

db_conn, db_cursor = iniciar_db()

# --- ESTADO DO USUÁRIO ---
if "logado" not in st.session_state:
    st.session_state.update({
        "logado": False, 
        "user_id": None, 
        "username": "", 
        "messages": [], 
        "ultima_resposta": ""
    })

# --- TELAS ---
def tela_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; font-size: 60px;'>C🍕Chef</h1>", unsafe_allow_html=True)
        aba1, aba2 = st.tabs(["Acessar Cozinha", "Novo Chef"])
        
        with aba1:
            u = st.text_input("UserName", key="login_u")
            s = st.text_input("Senha", type="password", key="login_s")
            if st.button("Entrar"):
                db_cursor.execute("SELECT id, username FROM usuarios WHERE username=? AND senha=?", (u, s))
                res = db_cursor.fetchone()
                if res:
                    st.session_state.update({"logado": True, "user_id": res[0], "username": res[1]})
                    st.rerun()
                else:
                    st.error("Chef não encontrado ou senha incorreta.")

        with aba2:
            n = st.text_input("Seu Nome")
            un = st.text_input("Escolha um UserName")
            ps = st.text_input("Crie uma Senha", type="password")
            if st.button("Finalizar Cadastro"):
                try:
                    db_cursor.execute("INSERT INTO usuarios (nome, username, senha) VALUES (?,?,?)", (n, un, ps))
                    db_conn.commit()
                    st.success("Cadastro realizado! Use a aba Entrar.")
                except:
                    st.error("Esse UserName já está em uso.")

def painel_chef():
    # Sidebar
    with st.sidebar:
        st.markdown("<h1 style='text-align: center;'>C🍕Chef</h1>", unsafe_allow_html=True)
        st.write(f"### 👨‍🍳 Chef: **{st.session_state.username}**")
        st.divider()
        menu = st.radio("Navegar:", ["Cozinha (Chat)", "Meu Cardápio"])
        st.divider()
        if st.button("Sair da Conta"):
            st.session_state.update({"logado": False, "messages": [], "ultima_resposta": ""})
            st.rerun()

    # Conteúdo Principal
    if menu == "Cozinha (Chat)":
        st.title(f"O que vamos criar hoje, Chef?")
        
        # Histórico de Chat
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        # Chat Input
        if prompt := st.chat_input("Ex: Uma receita de massa com o que sobrou do churrasco..."):
            # Adiciona user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Resposta da IA
            with st.chat_message("assistant"):
                try:
                    # Tenta pegar a chave do st.secrets ou do ambiente
                    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
                    if not api_key:
                        st.error("Erro: GROQ_API_KEY não configurada nos Secrets.")
                        st.stop()

                    client = Groq(api_key=api_key)
                    
                    # Chamada Stream (melhor UX)
                    full_response = ""
                    placeholder = st.empty()
                    
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Você é o CoChef, um assistente culinário de alto nível. Forneça receitas detalhadas, tempos de preparo e dicas de Chef."}
                        ] + st.session_state.messages,
                        stream=True
                    )

                    for chunk in completion:
                        content = chunk.choices[0].delta.content
                        if content:
                            full_response += content
                            placeholder.markdown(full_response + "▌")
                    
                    placeholder.markdown(full_response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.session_state.ultima_resposta = full_response
                    
                except Exception as e:
                    st.error(f"Erro na conexão: {e}")

        # Ações Adicionais
        if st.session_state.ultima_resposta:
            st.divider()
            if st.button("💾 Salvar esta receita no meu Cardápio"):
                conteudo = st.session_state.ultima_resposta
                # Tenta pegar a primeira linha como título
                titulo = conteudo.split('\n')[0].replace('#', '').strip()[:50] or "Receita Nova"
                
                db_cursor.execute("INSERT INTO cardapio (user_id, titulo, conteudo) VALUES (?,?,?)",
                           (st.session_state.user_id, titulo, conteudo))
                db_conn.commit()
                st.success(f"Receita '{titulo}' guardada a sete chaves!")
                st.session_state.ultima_resposta = ""

    elif menu == "Meu Cardápio":
        st.title("📖 Suas Criações Guardadas")
        db_cursor.execute("SELECT id, titulo, conteudo FROM cardapio WHERE user_id=?", (st.session_state.user_id,))
        receitas = db_cursor.fetchall()
        
        if not receitas:
            st.info("Seu cardápio ainda está em branco. Vamos cozinhar?")
        
        for id_rec, t, c in receitas:
            with st.expander(f"🍴 {t}"):
                st.markdown(c)
                if st.button(f"Remover {t}", key=f"del_{id_rec}"):
                    db_cursor.execute("DELETE FROM cardapio WHERE id=?", (id_rec,))
                    db_conn.commit()
                    st.rerun()

# --- EXECUÇÃO ---
if st.session_state.logado:
    painel_chef()
else:
    tela_login()


