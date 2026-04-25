import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL E BANCO DE DADOS ---
conn = sqlite3.connect('oficina_master.db', check_same_thread=False)
cursor = conn.cursor()

# Criação de todas as tabelas necessárias
cursor.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nome TEXT, tel TEXT, cpf TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY, item TEXT, qtd INTEGER, min INTEGER, preco REAL)')
cursor.execute('''CREATE TABLE IF NOT EXISTS ordens (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, veiculo TEXT, km INTEGER, 
    problema TEXT, valor REAL, status TEXT, custo_pecas REAL, comissao REAL, lucro REAL, data TEXT)''')
conn.commit()

st.set_page_config(page_title="Oficina Pro Master", layout="wide")

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

def tela_login():
    st.title("🔐 Acesso ao Sistema")
    with st.container():
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Acessar Oficina"):
            if u == "admin" and s == "1234":
                st.session_state['logado'] = True
                st.rerun()
            else: st.error("Acesso negado.")

if not st.session_state['logado']:
    tela_login()
    st.stop()

# --- MENU LATERAL ---
st.sidebar.title("🛠️ Oficina Pro")
menu = st.sidebar.radio("Navegação", ["Painel Geral", "Clientes", "Estoque", "Nova OS", "Financeiro", "Sair"])

if menu == "Sair":
    st.session_state['logado'] = False
    st.rerun()

# --- MÓDULO 1: PAINEL GERAL (DASHBOARD) ---
elif menu == "Painel Geral":
    st.header("📊 Painel de Controle")
    df = pd.read_sql_query("SELECT * FROM ordens", conn)
    
    if not df.empty:
        df['data_dt'] = pd.to_datetime(df['data'], dayfirst=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Total", f"R$ {df['valor'].sum():.2f}")
        c2.metric("Lucro Líquido", f"R$ {df['lucro'].fillna(0).sum():.2f}")
        c3.metric("OS Ativas", len(df[df['status'] == "Em Aberto"]))
        
        fig = px.line(df.groupby('data').sum().reset_index(), x='data', y='valor', title="Evolução de Vendas")
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 Últimas Ordens de Serviço")
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
    else: st.info("Nenhuma OS registrada.")

# --- MÓDULO 2: CLIENTES ---
elif menu == "Clientes":
    st.header("👥 Gestão de Clientes")
    with st.expander("➕ Cadastrar Novo Cliente"):
        n = st.text_input("Nome Completo")
        t = st.text_input("WhatsApp")
        c = st.text_input("CPF/CNPJ")
        if st.button("Salvar Cliente"):
            cursor.execute("INSERT INTO clientes (nome, tel, cpf) VALUES (?,?,?)", (n, t, c))
            conn.commit()
            st.success("Cliente cadastrado!")
    
    st.subheader("Lista de Clientes")
    st.dataframe(pd.read_sql_query("SELECT * FROM clientes", conn), use_container_width=True)

# --- MÓDULO 3: ESTOQUE ---
elif menu == "Estoque":
    st.header("📦 Controle de Estoque")
    with st.expander("➕ Adicionar Peça"):
        item = st.text_input("Nome da Peça")
        qtd = st.number_input("Quantidade", min_value=0)
        min_q = st.number_input("Estoque Mínimo", min_value=0)
        p = st.number_input("Preço de Custo (R$)", min_value=0.0)
        if st.button("Cadastrar Peça"):
            cursor.execute("INSERT INTO estoque (item, qtd, min, preco) VALUES (?,?,?,?)", (item, qtd, min_q, p))
            conn.commit()
            st.success("Peça adicionada!")

    est = pd.read_sql_query("SELECT * FROM estoque", conn)
    st.dataframe(est, use_container_width=True)
    for index, row in est.iterrows():
        if row['qtd'] <= row['min']:
            st.warning(f"⚠️ Alerta: Estoque baixo de {row['item']}!")

# --- MÓDULO 4: NOVA OS ---
elif menu == "Nova OS":
    st.header("📝 Abertura de Ordem de Serviço")
    clientes_lista = pd.read_sql_query("SELECT nome FROM clientes", conn)['nome'].tolist()
    
    if not clientes_lista:
        st.warning("Cadastre um cliente antes de abrir uma OS.")
    else:
        with st.form("os_form"):
            cli = st.selectbox("Selecione o Cliente", clientes_lista)
            veic = st.text_input("Veículo e Placa")
            km = st.number_input("KM Atual", min_value=0)
            prob = st.text_area("Descrição do Serviço")
            val = st.number_input("Valor Estimado (R$)", min_value=0.0)
            if st.form_submit_button("Gerar Ordem"):
                dt = datetime.now().strftime("%d/%m/%Y")
                cursor.execute("INSERT INTO ordens (cliente, veiculo, km, problema, valor, status, data) VALUES (?,?,?,?,?,?,?)",
                               (cli, veic, km, prob, val, "Em Aberto", dt))
                conn.commit()
                st.success("OS criada com sucesso!")

# --- MÓDULO 5: FINANCEIRO & COBRANÇA ---
elif menu == "Financeiro":
    st.header("💰 Fechamento e Cobrança")
    os_abertas = pd.read_sql_query("SELECT * FROM ordens WHERE status='Em Aberto'", conn)
    
    if not os_abertas.empty:
        escolha = st.selectbox("Escolha a OS", [f"{r['id']} - {r['cliente']}" for _, r in os_abertas.iterrows()])
        id_sel = int(escolha.split(" - ")[0])
        row = os_abertas[os_abertas['id'] == id_sel].iloc[0]
        
        c1, c2 = st.columns(2)
        custo = c1.number_input("Custo de Peças (R$)", min_value=0.0)
        comis = c2.slider("% Comissão do Mecânico", 0, 50, 30)
        
        if st.button("Finalizar e Gerar Recibo"):
            v_comis = (row['valor'] - custo) * (comis/100)
            lucro = row['valor'] - custo - v_comis
            cursor.execute("UPDATE ordens SET status='Pago', custo_pecas=?, comissao=?, lucro=? WHERE id=?", (custo, v_comis, lucro, id_sel))
            conn.commit()
            st.success("OS Paga!")
            st.info(f"**RECIBO:** Cliente: {row['cliente']} | Valor: R$ {row['valor']:.2f} | PIX: [CHAVE AQUI]")
    else: st.success("Nenhuma OS pendente.")
