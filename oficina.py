import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÕES E ESTILIZAÇÃO ---
st.set_page_config(page_title="OFICINA PREMIER", layout="wide", page_icon="⚙️")

# CSS para deixar o sistema com cara de Software Moderno
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
conn = sqlite3.connect('oficina_master_v2.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, veiculo TEXT, placa TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY, item TEXT, qtd INTEGER, preco REAL)')
cursor.execute('''CREATE TABLE IF NOT EXISTS ordens (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, status TEXT, 
    descricao TEXT, valor_total REAL, data_entrada TEXT, data_saida TEXT, lucro REAL)''')
conn.commit()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("⚙️ OFICINA PREMIER - LOGIN")
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("ENTRAR NO SISTEMA"):
            if u == "admin" and s == "admin": 
                st.session_state.logado = True
                st.rerun()
            else: st.error("Acesso Negado")
    st.stop()

# --- MENU ---
menu = st.sidebar.radio("MENU PRINCIPAL", ["Dashboard", "Clientes & Veículos", "Nova Ordem (OS)", "Oficina (Pátio)", "Estoque", "Financeiro"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.title("🚀 Painel de Resultados")
    df_os = pd.read_sql_query("SELECT * FROM ordens", conn)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OS Abertas", len(df_os[df_os['status'] == 'Aberta']))
    c2.metric("OS Concluídas", len(df_os[df_os['status'] == 'Finalizada']))
    c3.metric("Receita Bruta", f"R$ {df_os['valor_total'].sum():.2f}")
    c4.metric("Lucro Real", f"R$ {df_os['lucro'].sum():.2f}")

    if not df_os.empty:
        st.subheader("📈 Desempenho Mensal")
        fig = px.bar(df_os, x='data_entrada', y='valor_total', color='status', title="Vendas por Dia")
        st.plotly_chart(fig, use_container_width=True)

# --- 2. CLIENTES ---
elif menu == "Clientes & Veículos":
    st.title("👥 Gestão de Clientes")
    with st.form("cad_cliente"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome do Cliente")
        tel = col1.text_input("WhatsApp")
        veiculo = col2.text_input("Modelo do Carro")
        placa = col2.text_input("Placa")
        if st.form_submit_button("CADASTRAR CLIENTE"):
            cursor.execute("INSERT INTO clientes (nome, tel, veiculo, placa) VALUES (?,?,?,?)", (nome, tel, veiculo, placa))
            conn.commit()
            st.success("Cliente e Veículo cadastrados!")
    
    st.subheader("Base de Clientes")
    st.dataframe(pd.read_sql_query("SELECT * FROM clientes", conn), use_container_width=True)

# --- 3. NOVA OS ---
elif menu == "Nova Ordem (OS)":
    st.title("📝 Abrir Nova Ordem de Serviço")
    df_cli = pd.read_sql_query("SELECT id, nome, veiculo, placa FROM clientes", conn)
    
    if df_cli.empty:
        st.warning("Cadastre um cliente primeiro!")
    else:
        with st.form("os"):
            cliente_sel = st.selectbox("Selecione o Cliente/Veículo", 
                                     options=df_cli.apply(lambda r: f"{r['id']} - {r['nome']} ({r['placa']})", axis=1))
            cli_id = cliente_sel.split(" - ")[0]
            desc = st.text_area("O que precisa ser feito?")
            val = st.number_input("Valor do Orçamento (R$)", min_value=0.0)
            if st.form_submit_button("GERAR ORDEM DE SERVIÇO"):
                data = datetime.now().strftime("%d/%m/%Y")
                cursor.execute("INSERT INTO ordens (cliente_id, status, descricao, valor_total, data_entrada, lucro) VALUES (?,?,?,?,?,?)",
                             (cli_id, 'Aberta', desc, val, data, 0))
                conn.commit()
                st.success("OS enviada para o Pátio!")

# --- 4. PÁTIO (GESTÃO VISUAL) ---
elif menu == "Oficina (Pátio)":
    st.title("🔧 Veículos na Oficina")
    # Join para pegar dados do cliente e da OS
    query = """
    SELECT ordens.id, clientes.nome, clientes.veiculo, clientes.placa, ordens.descricao, ordens.valor_total, ordens.status
    FROM ordens INNER JOIN clientes ON ordens.cliente_id = clientes.id
    WHERE ordens.status != 'Finalizada'
    """
    df_patio = pd.read_sql_query(query, conn)
    
    for i, row in df_patio.iterrows():
        with st.expander(f"🚗 {row['veiculo']} - Placa: {row['placa']} (OS #{row['id']})"):
            st.write(f"**Cliente:** {row['nome']}")
            st.write(f"**Problema:** {row['descricao']}")
            st.write(f"**Valor Orçado:** R$ {row['valor_total']:.2f}")
            if st.button(f"Finalizar Serviço #{row['id']}"):
                cursor.execute("UPDATE ordens SET status='Finalizada', data_saida=?, lucro=? WHERE id=?", 
                             (datetime.now().strftime("%d/%m/%Y"), row['valor_total']*0.4, row['id']))
                conn.commit()
                st.rerun()

# --- 5. FINANCEIRO ---
elif menu == "Financeiro":
    st.title("💰 Financeiro Detalhado")
    df_fin = pd.read_sql_query("SELECT * FROM ordens WHERE status='Finalizada'", conn)
    st.dataframe(df_fin, use_container_width=True)
    st.download_button("Baixar Relatório (CSV)", df_fin.to_csv(), "financeiro.csv")
