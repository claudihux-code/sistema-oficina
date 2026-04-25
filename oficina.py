import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO DE AMBIENTE ---
st.set_page_config(page_title="SISTEMA MECÂNICA PRO", layout="wide")

# --- CONEXÃO BANCO DE DADOS ---
conn = sqlite3.connect('sistema_oficina_v4.db', check_same_thread=False)
cursor = conn.cursor()

def iniciar_db():
    cursor.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, placa TEXT, carro TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY, item TEXT, preco REAL, qtd INTEGER)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, descricao TEXT, 
        pecas_id TEXT, valor_total REAL, status TEXT, data TEXT,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
    conn.commit()

iniciar_db()

# --- AUTENTICAÇÃO ---
if 'auth' not in st.session_state: st.session_state.auth = False

def login():
    st.title("🛡️ Acesso Restrito")
    col1, col2 = st.columns([1,1])
    with col1:
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema"):
            if user == "admin" and pw == "admin":
                st.session_state.auth = True
                st.rerun()
            else: st.error("Incorreto")

if not st.session_state.auth:
    login()
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.title("MECÂNICA PRO v4.0")
aba = st.sidebar.radio("Navegação", ["Dashboard", "Clientes", "Estoque", "Ordens de Serviço", "Caixa"])

# --- DASHBOARD ---
if aba == "Dashboard":
    st.title("📊 Indicadores de Performance")
    df_os = pd.read_sql_query("SELECT * FROM ordens", conn)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Serviços", len(df_os))
    c2.metric("Receita Acumulada", f"R$ {df_os['valor_total'].sum():.2f}")
    c3.metric("Ticket Médio", f"R$ {(df_os['valor_total'].mean() if not df_os.empty else 0):.2f}")
    
    if not df_os.empty:
        fig = px.bar(df_os, x='data', y='valor_total', title="Faturamento por Data")
        st.plotly_chart(fig, use_container_width=True)

# --- CLIENTES ---
elif aba == "Clientes":
    st.title("👥 Gestão de Clientes")
    with st.form("cad"):
        n, t = st.columns(2)
        nome = n.text_input("Nome")
        tel = t.text_input("WhatsApp")
        p, c = st.columns(2)
        placa = p.text_input("Placa")
        carro = c.text_input("Carro")
        if st.form_submit_button("Salvar Cliente"):
            cursor.execute("INSERT INTO clientes (nome, tel, placa, carro) VALUES (?,?,?,?)", (nome, tel, placa, carro))
            conn.commit()
            st.success("Cadastrado!")
    
    st.dataframe(pd.read_sql_query("SELECT * FROM clientes", conn), use_container_width=True)

# --- ESTOQUE ---
elif aba == "Estoque":
    st.title("📦 Controle de Peças")
    with st.form("est"):
        i, p, q = st.columns(3)
        item = i.text_input("Peça")
        preco = p.number_input("Preço Venda", min_value=0.0)
        qtd = q.number_input("Quantidade", min_value=0)
        if st.form_submit_button("Adicionar"):
            cursor.execute("INSERT INTO estoque (item, preco, qtd) VALUES (?,?,?)", (item, preco, qtd))
            conn.commit()
    
    st.table(pd.read_sql_query("SELECT * FROM estoque", conn))

# --- ORDENS DE SERVIÇO ---
elif aba == "Ordens de Serviço":
    st.title("🛠️ Gerenciamento de OS")
    df_c = pd.read_sql_query("SELECT id, nome, placa FROM clientes", conn)
    
    with st.expander("➕ Abrir Nova Ordem"):
        if df_c.empty: st.warning("Cadastre um cliente primeiro")
        else:
            cli = st.selectbox("Selecione o Cliente", options=df_c.apply(lambda r: f"{r['id']}-{r['nome']}", axis=1))
            desc = st.text_area("Descrição do Serviço")
            valor = st.number_input("Valor do Serviço (R$)", min_value=0.0)
            if st.button("Gerar OS"):
                c_id = cli.split("-")[0]
                dt = datetime.now().strftime("%d/%m/%Y")
                cursor.execute("INSERT INTO ordens (cliente_id, descricao, valor_total, status, data) VALUES (?,?,?,?,?)",
                               (c_id, desc, valor, "Pendente", dt))
                conn.commit()
                st.rerun()

    st.subheader("Serviços em Aberto")
    query = """SELECT ordens.id, clientes.nome, clientes.carro, ordens.descricao, ordens.valor_total, ordens.status 
               FROM ordens JOIN clientes ON ordens.cliente_id = clientes.id WHERE status='Pendente'"""
    st.dataframe(pd.read_sql_query(query, conn), use_container_width=True)

# --- CAIXA ---
elif aba == "Caixa":
    st.title("💰 Fechamento de Caixa")
    df_paga = pd.read_sql_query("SELECT * FROM ordens", conn)
    st.write("Histórico de Entradas")
    st.dataframe(df_paga, use_container_width=True)
