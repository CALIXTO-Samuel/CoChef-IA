import streamlit as st
from groq import Groq

# Configuração da Página
st.set_page_config(page_title="CoChef Pro", page_icon="🍳", layout="wide")

# --- ESTILIZAÇÃO DA MARCA D'ÁGUA ONC ---
st.markdown(
    """
    <style>
    .watermark {
        position: fixed;
        bottom: 10px;
        right: 20px;
        width: auto;
        text-align: right;
        color: rgba(128, 128, 128, 0.4); /* Cor cinza semi-transparente */
        font-size: 16px;
        font-weight: bold;
        font-style: italic;
        z-index: 1000;
        pointer-events: none;
        user-select: none;
    }
    </style>
    <div class="watermark">ONC - Mateus, Mirella e S. Calixto</div>
    """,
    unsafe_allow_html=True
)

st.title("C🍕Chef Pro")

# Sidebar com a marca d'água também no menu
with st.sidebar:
    st.header("Menu CoChef")
    st.info("Desenvolvido por: ONC")
    st.write("---")
    # Se tiver o ficheiro da logo, ele aparece aqui
    try:
        st.image("Logo CoChef.jpeg", width=150)
    except:
        pass

# --- LÓGICA DO CHAT (GROQ) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibir histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input do utilizador
if prompt := st.chat_input("O que vamos cozinhar, Chef?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # Substitua pela sua chave real ou use st.secrets para segurança
        client = Groq(api_key="SUA_CHAVE_GROQ_AQUI")
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        )
        
        full_response = response.choices[0].message.content
        with st.chat_message("assistant"):
            st.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
    except Exception as e:
        st.error("Erro: Verifique a sua chave da API Groq.")
