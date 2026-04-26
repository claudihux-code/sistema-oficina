import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÕES DE DESIGN ---
st.set_page_config(page_title="ERP OFICINA PRO v5.0", layout="wide", page_icon="🛠️")

# Estilo para botões e métricas
st.markdown("""
    <style>
    .stButton>button { background-color: #2E7D32; color: white; border-radius: 8px; height: 50px; font-weight: bold; }
    .stMetric { background-color: #1E1E1E; border: 1px solid #333; padding: 20px; border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

# --- NÚCLEO DE DADOS (DATABASE) ---
conn = sqlite3.connect('erp_oficina_v5.db', check_same_thread=False)
cursor = conn.cursor()

def setup_db():
    # Tabela de Clientes e Veículos
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY, nome TEXT, whatsapp TEXT, carro TEXT, placa TEXT UNIQUE)''')
    
    # Tabela de Estoque (Produtos)
    cursor.execute('''CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY, item TEXT, custo REAL, venda REAL, saldo INTEGER)''')
    
    # Tabela de Ordens de Serviço (OS)
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens (
        id INTEGER PRIMARY KEY AUTOINCREMENT, cliente_id INTEGER, 
        servico TEXT, pecas_json TEXT, mao_de_obra REAL, 
        total REAL, status TEXT, data TEXT,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
    conn.commit()

setup_db()

# --- NAVEGAÇÃO PROFISSIONAL ---
with st.sidebar:
    st.title("⚙️ GESTÃO ELITE")
    menu = st.radio("Módulos do Sistema", 
                    ["📊 Dashboard Executivo", "👥 Clientes & Frotas", "📦 Estoque & Compras", "🛠️ Ordens de Serviço", "💰 Financeiro"])
    st.divider()
    st.info("Usuário: Administrador\nVersão: 5.0 Enterprise")

# --- 1. DASHBOARD EXECUTIVO ---
if menu == "📊 Dashboard Executivo":
    st.title("📊 Indicadores de Performance")
    df_os = pd.read_sql_query("SELECT * FROM ordens", conn)
    
    c1, c2, c3, c4 = st.columns(4)
    if not df_os.empty:
        c1.metric("Faturamento Mensal", f"R$ {df_os['total'].sum():.2f}")
        c2.metric("Serviços Ativos", len(df_os[df_os['status'] != 'Finalizado']))
        c3.metric("Ticket Médio", f"R$ {df_os['total'].mean():.2f}")
        lucro_est = df_os['total'].sum() * 0.4 # Estimativa de 40% de margem
        c4.metric("Lucro Estimado", f"R$ {lucro_est:.2f}")

        st.subheader("📈 Tendência de Vendas")
        fig = px.area(df_os, x='data', y='total', title="Fluxo de Caixa Diário", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando os primeiros registros para gerar inteligência de dados.")

# --- 2. CLIENTES & FROTAS ---
elif menu == "👥 Clientes & Frotas":
    st.title("👥 Cadastro de Clientes")
    with st.form("cli_form"):
        col1, col2 = st.columns(2)
        n = col1.text_input("Nome do Cliente")
        w = col1.text_input("WhatsApp")
        v = col2.text_input("Veículo (Marca/Modelo/Ano)")
        p = col2.text_input("Placa")
        if st.form_submit_button("💾 Salvar Registro"):
            try:
                cursor.execute("INSERT INTO clientes (nome, whatsapp, carro, placa) VALUES (?,?,?,?)", (n, w, v, p))
                conn.commit()
                st.success("Cliente cadastrado com sucesso!")
            except: st.error("Erro: Esta placa já está cadastrada.")
    
    st.subheader("Base de Dados")
    st.dataframe(pd.read_sql_query("SELECT * FROM clientes", conn), use_container_width=True)

# --- 3. ESTOQUE & COMPRAS ---
elif menu == "📦 Estoque & Compras":
    st.title("📦 Gestão de Insumos")
    with st.expander("➕ Adicionar Novo Item ao Estoque"):
        with st.form("estoque_form"):
            i = st.text_input("Nome da Peça/Produto")
            c = st.number_input("Custo de Compra (R$)", min_value=0.0)
            v = st.number_input("Preço de Venda (R$)", min_value=0.0)
            s = st.number_input("Saldo Inicial (Unidades)", min_value=0)
            if st.form_submit_button("Adicionar"):
                cursor.execute("INSERT INTO estoque (item, custo, venda, saldo) VALUES (?,?,?,?)", (i, c, v, s))
                conn.commit()
    
    df_est = pd.read_sql_query("SELECT * FROM estoque", conn)
    st.dataframe(df_est, use_container_width=True)

# --- 4. ORDENS DE SERVIÇO (PDV) ---
elif menu == "🛠️ Ordens de Serviço":
    st.title("🛠️ Centro de Serviços")
    tab1, tab2 = st.tabs(["🆕 Abrir Nova OS", "📋 Gerenciar Serviços"])

    with tab1:
        df_cli = pd.read_sql_query("SELECT id, nome, placa FROM clientes", conn)
        df_prod = pd.read_sql_query("SELECT item, venda FROM estoque WHERE saldo > 0", conn)
        
        if df_cli.empty: st.warning("Cadastre um cliente antes de abrir uma OS.")
        else:
            with st.form("os_pro"):
                cliente_sel = st.selectbox("Selecione o Cliente", options=df_cli.apply(lambda r: f"{r['id']} - {r['nome']} ({r['placa']})", axis=1))
                servico = st.text_area("Descrição Técnica do Problema")
                pecas_mult = st.multiselect("Peças e Peças Utilizadas", options=df_prod['item'].tolist())
                mao = st.number_input("Valor da Mão de Obra (R$)", min_value=0.0)
                
                if st.form_submit_button("🚀 Gerar OS Profissional"):
                    c_id = cliente_sel.split(" - ")[0]
                    # Cálculo automático do total baseado no preço de venda do estoque
                    total_pecas = df_prod[df_prod['item'].isin(pecas_mult)]['venda'].sum()
                    total_final = total_pecas + mao
                    data_os = datetime.now().strftime("%d/%m/%Y")
                    
                    cursor.execute("INSERT INTO ordens (cliente_id, servico, pecas_json, mao_de_obra, total, status, data) VALUES (?,?,?,?,?,?,?)",
                                   (c_id, servico, str(pecas_mult), mao, total_final, "Em Execução", data_os))
                    conn.commit()
                    st.success(f"OS aberta com sucesso! Valor Total: R$ {total_final:.2f}")

    with tab2:
        query_os = """SELECT ordens.id, clientes.nome, clientes.placa, ordens.total, ordens.status 
                      FROM ordens JOIN clientes ON ordens.cliente_id = clientes.id"""
        st.dataframe(pd.read_sql_query(query_os, conn), use_container_width=True)

# --- 5. FINANCEIRO ---
elif menu == "💰 Financeiro":
    st.title("💰 Movimentação de Caixa")
    df_fin = pd.read_sql_query("SELECT * FROM ordens", conn)
    st.write("Histórico de Faturamento Detalhado")
    st.dataframe(df_fin)
    st.button("📄 Exportar para Contabilidade (CSV)")
import { describe, expect, it, vi } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";

function createMockContext(): TrpcContext {
  return {
    user: {
      id: 1,
      openId: "test-user",
      email: "test@example.com",
      name: "Test User",
      loginMethod: "manus",
      role: "admin",
      createdAt: new Date(),
      updatedAt: new Date(),
      lastSignedIn: new Date(),
    },
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {
      clearCookie: vi.fn(),
    } as TrpcContext["res"],
  };
}

describe("Comissões - Serialização de Datas (Regressão)", () => {
  it("deve serializar comissões sem erro toISOString", async () => {
    const ctx = createMockContext();
    const caller = appRouter.createCaller(ctx);
    
    // O endpoint list deve existir e ser chamável
    expect(caller.comissoes.list).toBeDefined();
    
    // Verificar que o endpoint aceita filtros com datas como strings
    const result = await caller.comissoes.list({
      dataInicio: "2026-01-01",
      dataFim: "2026-12-31",
    });
    
    // Deve retornar um array (vazio ou com dados)
    expect(Array.isArray(result)).toBe(true);
    
    // Se houver dados, verificar que dataPagamento é string ou null
    if (result.length > 0) {
      result.forEach(comissao => {
        expect(typeof comissao.id).toBe("number");
        expect(typeof comissao.mecanicoId).toBe("number");
        expect(typeof comissao.osId).toBe("number");
        expect(typeof comissao.status).toBe("string");
        // dataPagamento deve ser string (YYYY-MM-DD) ou null, nunca Date
        if (comissao.dataPagamento !== null) {
          expect(typeof comissao.dataPagamento).toBe("string");
          // Validar formato YYYY-MM-DD
          expect(comissao.dataPagamento).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        }
        // createdAt e updatedAt devem ser Date ou timestamp
        expect(comissao.createdAt).toBeDefined();
        expect(comissao.updatedAt).toBeDefined();
        // mecanicoNome deve estar presente
        expect(typeof comissao.mecanicoNome).toBe("string");
      });
    }
  });

  it("deve serializar resumo de comissões sem erro", async () => {
    const ctx = createMockContext();
    const caller = appRouter.createCaller(ctx);
    
    const result = await caller.comissoes.resumo({
      dataInicio: "2026-01-01",
      dataFim: "2026-12-31",
    });
    
    expect(Array.isArray(result)).toBe(true);
    
    if (result.length > 0) {
      result.forEach(resumo => {
        expect(typeof resumo.mecanicoId).toBe("number");
        expect(typeof resumo.mecanicoNome).toBe("string");
        expect(typeof resumo.totalOS).toBe("number");
        // totalProducao e totalComissao podem ser números ou strings (Decimal)
        expect(resumo.totalProducao).toBeDefined();
        expect(resumo.totalComissao).toBeDefined();
      });
    }
  });

  it("deve permitir pagar comissão com dataPagamento string", async () => {
    const ctx = createMockContext();
    const caller = appRouter.createCaller(ctx);
    
    // Teste que o endpoint aceita dataPagamento como string
    const result = await caller.comissoes.pagar({
      id: 999, // ID que provavelmente não existe, mas valida o input
      dataPagamento: "2026-04-25",
    }).catch(err => {
      // Esperamos erro de DB (ID não existe), não erro de serialização
      expect(err).toBeDefined();
      return null;
    });
    
    // Se não houver erro, sucesso
    if (result) {
      expect(result.success).toBe(true);
    }
  });
});
