import streamlit as st
from data import load_data

def pagina_rankings():
    """Pagina de rankings completos - 5 abas, 50 ativos, cards estilizados."""
    st.markdown('<h1 class="main-header">🏆 Rankings</h1>', unsafe_allow_html=True)
    
    df = load_data()
    if df.empty:
        st.warning("Dados nao disponiveis.")
        return
    
    df = df[df['Nome'] != '#N/A']
    df = df[df['Nome'].notna()]
    df = df[df['Nome'].str.strip() != '']
    df = df[df['Nome'].str.strip() != 'nan']
    
    if df.empty:
        st.warning("Nenhum ativo valido encontrado apos filtro de Nome.")
        return
    
    st.markdown("""
    <style>
    .ranking-card {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 14px 10px;
        margin-bottom: 0.75rem;
        transition: all 0.3s ease;
        text-align: center;
        height: 100%;
    }
    .ranking-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        border-color: #3b82f6;
    }
    .ticker-link button {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        color: #38bdf8 !important;
        text-decoration: underline !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        cursor: pointer !important;
        width: auto !important;
        box-shadow: none !important;
    }
    .ticker-link button:hover {
        color: #60a5fa !important;
        text-decoration: none !important;
    }
    .ranking-nome {
        font-size: 0.72rem;
        color: #94a3b8;
        margin: 4px 0 8px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    .ranking-valor {
        font-size: 1.35rem;
        font-weight: 800;
        color: #38bdf8;
        margin: 6px 0;
        line-height: 1.1;
    }
    .ranking-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.68rem;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #334155;
    }
    .ranking-score { font-weight: 700; }
    .ranking-setor { color: #64748b; font-weight: 500; }
    .ranking-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    </style>
    """, unsafe_allow_html=True)

    setores = ["Todos"] + sorted([str(x) for x in df['Setor'].dropna().unique().tolist() if str(x) not in ['nan', 'N/A', '#N/A', '']])
    subsetores = ["Todos"] + sorted([str(x) for x in df['SubSetor'].dropna().unique().tolist() if str(x) not in ['nan', 'N/A', '#N/A', '']])

    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1: setor_sel = st.selectbox("📂 Setor", setores, key="rank_setor")
    with col_f2: subsetor_sel = st.selectbox("📁 SubSetor", subsetores, key="rank_subsetor")
    with col_f3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        st.markdown(f'<p style="color:#94a3b8; font-size:0.85rem; margin:0;">📊 {len(df)} ativos carregados</p>', unsafe_allow_html=True)

    df_filt = df.copy()
    if setor_sel != "Todos": df_filt = df_filt[df_filt['Setor'] == setor_sel]
    if subsetor_sel != "Todos": df_filt = df_filt[df_filt['SubSetor'] == subsetor_sel]
    if df_filt.empty:
        st.warning("Nenhum ativo encontrado com os filtros selecionados.")
        return

    def render_ranking(df_rank, col_indicador, titulo, fmt_func, is_ascending=False, cor_valor="#38bdf8"):
        df_work = df_rank.copy()
        if col_indicador in ['PL', 'PVP', 'EV_EBITDA', 'DivLiquida_EBITDA']:
            df_work = df_work[df_work[col_indicador] > 0]
        if col_indicador in ['DY', 'ROE', 'ROIC', 'MargemLiquida', 'CAGR_Lucros_5a', 'CAGR_Receitas_5a', 'Score_CS']:
            df_work = df_work[df_work[col_indicador].notna()]
        if df_work.empty:
            st.info(f"Dados insuficientes para {titulo}.")
            return

        top = df_work.nsmallest(50, col_indicador) if is_ascending else df_work.nlargest(50, col_indicador)
        st.markdown(f'<div class="section-title-v2">{titulo}</div>', unsafe_allow_html=True)

        items = []
        for _, row in top.iterrows():
            ticker = row['Ticker']
            nome = str(row.get('Nome', ticker))
            valor = fmt_func(row.get(col_indicador, 0))
            score = int(row.get('Score_CS', 0))
            setor = str(row.get('Setor', 'N/A'))
            
            # Badge do score - if-elif-else limpo
            if score >= 9:
                badge_bg, badge_text, badge_label = "#065f46", "#10b981", "Excelente"
            elif score >= 7:
                badge_bg, badge_text, badge_label = "#3f6212", "#84cc16", "Bom"
            elif score >= 5:
                badge_bg, badge_text, badge_label = "#92400e", "#f59e0b", "Regular"
            elif score >= 3:
                badge_bg, badge_text, badge_label = "#7c2d12", "#f97316", "Fraco"
            else:
                badge_bg, badge_text, badge_label = "#7f1d1d", "#dc2626", "Pessimo"
            
            # Cor do score
            if score >= 9:
                sc_color = "#10b981"
            elif score >= 7:
                sc_color = "#84cc16"
            elif score >= 5:
                sc_color = "#f59e0b"
            elif score >= 3:
                sc_color = "#f97316"
            else:
                sc_color = "#dc2626"
            
            items.append((ticker, nome, valor, score, sc_color, setor, badge_bg, badge_text, badge_label))

        for row_idx in range(10):
            cols = st.columns(5)
            for col_idx in range(5):
                idx = row_idx * 5 + col_idx
                if idx < len(items):
                    ticker, nome, valor, score, sc_color, setor, badge_bg, badge_text, badge_label = items[idx]
                    nome_curto = nome[:22] + "..." if len(nome) > 22 else nome
                    setor_curto = setor[:15] + "..." if len(setor) > 15 else setor
                    with cols[col_idx]:
                        st.markdown('<div class="ticker-link">', unsafe_allow_html=True)
                        if st.button(f"{ticker} 🔍", key=f"nav_{ticker}_{col_indicador}", use_container_width=False):
                            st.query_params["page"] = "Analise"
                            st.query_params["ticker"] = ticker
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class="ranking-card">
                            <div class="ranking-nome">{nome_curto}</div>
                            <div class="ranking-valor" style="color: {cor_valor};">{valor}</div>
                            <div style="margin-top:6px;">
                                <span class="ranking-badge" style="background:{badge_bg}40; color:{badge_text};">{badge_label}</span>
                            </div>
                            <div class="ranking-footer">
                                <span class="ranking-score" style="color:{sc_color};">● CS {score}</span>
                                <span class="ranking-setor">{setor_curto}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Destaque", "💰 Valuation", "📈 Crescimento", "🏛️ Tamanho", "🎖️ Score CS"])

    with tab1:
        render_ranking(df_filt, 'DY', '💰 Maiores Dividend Yield', lambda x: f"{x:.2f}%", cor_valor="#f59e0b")
        render_ranking(df_filt, 'PL', '📉 Menores P/L', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#38bdf8")
        render_ranking(df_filt, 'ROE', '📈 Maiores ROE', lambda x: f"{x:.2f}%", cor_valor="#10b981")
        render_ranking(df_filt, 'Upside_AGF_Medio', '🎯 Maior Upside Medio', lambda x: f"{x:+.1f}%", cor_valor="#a78bfa")

    with tab2:
        render_ranking(df_filt, 'Upside_Graham', '📊 Mais Baratas — Graham', lambda x: f"{x:+.1f}%", cor_valor="#34d399")
        render_ranking(df_filt, 'Upside_Bazin', '💵 Mais Baratas — Bazin', lambda x: f"{x:+.1f}%", cor_valor="#fbbf24")
        render_ranking(df_filt, 'PVP', '📉 Menores P/VP', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#38bdf8")
        render_ranking(df_filt, 'EV_EBITDA', '⚡ Menor EV/EBITDA', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#60a5fa")

    with tab3:
        render_ranking(df_filt, 'CAGR_Lucros_5a', '🚀 Maior CAGR Lucros 5a', lambda x: f"{x:.2f}%", cor_valor="#10b981")
        render_ranking(df_filt, 'CAGR_Receitas_5a', '📊 Maior CAGR Receitas 5a', lambda x: f"{x:.2f}%", cor_valor="#34d399")
        render_ranking(df_filt, 'MargemLiquida', '💎 Maior Margem Liquida', lambda x: f"{x:.2f}%", cor_valor="#a78bfa")
        render_ranking(df_filt, 'DivLiquida_EBITDA', '🛡️ Menor Divida Liq/EBITDA', lambda x: f"{x:.2f}x", is_ascending=True, cor_valor="#f87171")

    with tab4:
        render_ranking(df_filt, 'Market_Cap', '🏢 Maior Valor de Mercado', lambda x: f"R$ {x/1e9:.2f}B" if x >= 1e9 else f"R$ {x/1e6:.2f}M", cor_valor="#fbbf24")
        render_ranking(df_filt, 'Lucro_Liquido', '💰 Maiores Lucros', lambda x: f"R$ {x/1e9:.2f}B" if abs(x) >= 1e9 else f"R$ {x/1e6:.2f}M", cor_valor="#10b981")
        render_ranking(df_filt, 'Receita_Liquida', '📈 Maiores Receitas', lambda x: f"R$ {x/1e9:.2f}B" if x >= 1e9 else f"R$ {x/1e6:.2f}M", cor_valor="#38bdf8")

    with tab5:
        df_score = df_filt[df_filt['Score_CS'].notna()]
        if not df_score.empty:
            top_score = df_score.nlargest(50, 'Score_CS')
            st.markdown('<div class="section-title-v2">🎖️ Top Score CS</div>', unsafe_allow_html=True)

            items = []
            for _, row in top_score.iterrows():
                ticker = row['Ticker']
                nome = str(row.get('Nome', ticker))
                score = int(row.get('Score_CS', 0))
                setor = str(row.get('Setor', 'N/A'))
                
                # Score CS - if-elif-else limpo
                if score >= 9:
                    card_border, score_color, score_label = "#10b981", "#10b981", "Excelente"
                elif score >= 7:
                    card_border, score_color, score_label = "#84cc16", "#84cc16", "Bom"
                elif score >= 5:
                    card_border, score_color, score_label = "#f59e0b", "#f59e0b", "Regular"
                elif score >= 3:
                    card_border, score_color, score_label = "#f97316", "#f97316", "Fraco"
                else:
                    card_border, score_color, score_label = "#dc2626", "#dc2626", "Pessimo"
                
                nome_curto = nome[:22] + "..." if len(nome) > 22 else nome
                setor_curto = setor[:15] + "..." if len(setor) > 15 else setor
                items.append((ticker, nome_curto, score, score_color, score_label, setor_curto, card_border))

            for row_idx in range(10):
                cols = st.columns(5)
                for col_idx in range(5):
                    idx = row_idx * 5 + col_idx
                    if idx < len(items):
                        ticker, nome_curto, score, score_color, score_label, setor_curto, card_border = items[idx]
                        with cols[col_idx]:
                            st.markdown('<div class="ticker-link">', unsafe_allow_html=True)
                            if st.button(f"{ticker} ", key=f"nav_score_{ticker}", use_container_width=False):
                                st.query_params["page"] = "Analise"
                                st.query_params["ticker"] = ticker
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                            st.markdown(f"""
                            <div class="ranking-card" style="border: 2px solid {card_border};">
                                <div class="ranking-nome">{nome_curto}</div>
                                <div style="margin: 10px 0;">
                                    <div style="font-size: 2.2rem; font-weight: 800; color: {score_color}; line-height: 1;">{score}</div>
                                    <div style="font-size: 0.75rem; font-weight: 700; color: {score_color}; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;">{score_label}</div>
                                </div>
                                <div class="ranking-footer">
                                    <span style="color:#64748b; font-size:0.7rem; font-weight:600;">de 10</span>
                                    <span class="ranking-setor">{setor_curto}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        else:
            st.info("Dados de Score CS nao disponiveis.")
