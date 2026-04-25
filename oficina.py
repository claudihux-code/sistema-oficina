import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SISTEMA OFICINA ELITE", layout="wide", page_icon="🏎️")

# --- BANCO DE DADOS INTEGRADO ---
conn = sqlite3.connect('oficina_master_v3.db', check_same_thread=False)
cursor = conn.cursor()

# Criação de tabelas com chaves estrangeiras (Relações Reais)
cursor.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, placa TEXT, carro TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY, nome TEXT, preco_venda REAL, estoque_atual INTEGER)')
cursor.execute('''CREATE TABLE IF NOT EXISTS ordens (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    cliente_id INTEGER, 
    problema TEXT, 
    valor_total REAL, 
    custo_total REAL,
    status TEXT, 
    data_abertura TEXT,
    FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
conn.commit()

# --- ESTILIZAÇÃO CUSTOMIZADA ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    div[data-testid="stMetricValue"] { color: #00FF00; }
    .stButton>button { background-color: #FF4B4B; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- MENU LATERAL ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1995/1995471.png", width=100)
st.sidebar.title("MENU DE GESTÃO")
aba = st.sidebar.radio("Escolha o Módulo", ["📊 Dashboard", "👥 Clientes", "📦 Estoque", "🛠️ Oficina (OS)", "💰 Caixa/Lucro"])

# --- MÓDULO 1: DASHBOARD ---
if aba == "📊 Dashboard":
    st.title("🚀 Painel de Resultados")
    df_os = pd.read_sql_query("SELECT * FROM ordens", conn)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OS Ativas", len(df_os[df_os['status'] != 'Paga']))
    c2.metric("Faturamento", f"R$ {df_os['valor_total'].sum():.2f}")
    c3.metric("Custo Total", f"R$ {df_os['custo_total'].sum():.2f}")
    c4.metric("Lucro Líquido", f"R$ {(df_os['valor_total'].sum() - df_os['custo_total'].sum()):.2f}")

    if not df_os.empty:
        fig = px.pie(df_os, names='status', title="Distribuição de Serviços", hole=0.5)
        st.plotly_chart(fig, use_container_width=True)

# --- MÓDULO 2: CLIENTES ---
elif aba == "👥 Clientes":
    st.header("Gestão de Clientes e Frotas")
    with st.form("cad_cli"):
        n = st.text_input("Nome Completo")
        t = st.text_input("WhatsApp")
        p = st.text_input("Placa do Veículo")
        c = st.text_input("Modelo/Ano")
        if st.form_submit_button("Cadastrar"):
            cursor.execute("INSERT INTO clientes (nome, tel, placa, carro) VALUES (?,?,?,?)", (n,t,p,c))
            conn.commit()
            st.success("Cliente salvo!")
    
    st.dataframe(pd.read_sql_query("SELECT * FROM clientes", conn), use_container_width=True)

# --- MÓDULO 3: ESTOQUE ---
elif aba == "📦 Estoque":
    st.header("Controle de Peças e Produtos")
    with st.form("cad_prod"):
        item = st.text_input("Nome da Peça")
        pv = st.number_input("Preço de Venda (R$)", min_value=0.0)
        qtd = st.number_input("Quantidade em Estoque", min_value=0)
        if st.form_submit_button("Adicionar Peça"):
            cursor.execute("INSERT INTO produtos (nome, preco_venda, estoque_atual) VALUES (?,?,?)", (item, pv, qtd))
            conn.commit()
    
    st.dataframe(pd.read_sql_query("SELECT * FROM produtos", conn), use_container_width=True)

# --- MÓDULO 4: OFICINA (OS INTEGRADA) ---
elif aba == "🛠️ Oficina (OS)":
    st.header("Gerenciamento de Ordens de Serviço")
    
    tab1, tab2 = st.tabs(["Nova OS", "Gerenciar Pátio"])
    
    with tab1:
        df_c = pd.read_sql_query("SELECT id, nome, placa FROM clientes", conn)
        df_p = pd.read_sql_query("SELECT id, nome, preco_venda FROM produtos", conn)
        
        if df_c.empty: st.warning("Cadastre um cliente primeiro!")
        else:
            with st.form("abrir_os"):
                cliente = st.selectbox("Cliente", options=df_c.apply(lambda r: f"{r['id']}-{r['nome']} ({r['placa']})", axis=1))
                servico = st.text_area("Diagnóstico/Serviço")
                peca_usada = st.multiselect("Peças Utilizadas", options=df_p['nome'].tolist())
                mao_de_obra = st.number_input("Valor Mão de Obra (R$)", min_value=0.0)
                
                if st.form_submit_button("Abrir Ordem de Serviço"):
                    c_id = cliente.split("-")[0]
                    # Calcula valor total (Mão de obra + soma das peças selecionadas)
                    valor_pecas = df_p[df_p['nome'].isin(peca_usada)]['preco_venda'].sum()
                    total = mao_de_obra + valor_pecas
                    dt = datetime.now().strftime("%d/%m/%Y")
                    
                    cursor.execute("INSERT INTO ordens (cliente_id, problema, valor_total, custo_total, status, data_abertura) VALUES (?,?,?,?,?,?)",
                                   (c_id, servico, total, valor_pecas*0.6, "Em Execução", dt))
                    conn.commit()
                    st.success(f"OS Aberta! Valor Total: R$ {total:.2f}")

    with tab2:
        os_ativas = pd.read_sql_query("""
            SELECT ordens.id, clientes.nome, clientes.carro, clientes.placa, ordens.valor_total, ordens.status 
            FROM ordens JOIN clientes ON ordens.cliente_id = clientes.id WHERE status != 'Paga'
        """, conn)
        
        for _, os in os_ativas.iterrows():
            with st.expander(f"OS #{os['id']} - {os['carro']} ({os['placa']})"):
                st.write(f"**Cliente:** {os['nome']} | **Total:** R$ {os['valor_total']:.2f}")
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button(f"Dar Baixa/Pagar #{os['id']}"):
                    cursor.execute("UPDATE ordens SET status='Paga' WHERE id=?", (os['id'],))
                    conn.commit()
                    st.rerun()

# --- MÓDULO 5: FINANCEIRO ---
elif aba == "💰 Caixa/Lucro":
    st.header("Movimentação Financeira")
    finalizadas = pd.read_sql_query("SELECT * FROM ordens WHERE status='Paga'", conn)
    st.table(finalizadas)
    st.download_button("Exportar para Excel (CSV)", finalizadas.to_csv(), "caixa.csv")
  
