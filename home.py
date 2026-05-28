import streamlit as st

def pagina_home():
    st.markdown("""
    <style>
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px;
        margin: 12px 0;
        transition: all 0.3s ease;
    }
    .feature-card:hover {
        border-color: #3b82f6;
        transform: translateY(-4px);
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 12px;
    }
    .feature-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 8px;
    }
    .feature-desc {
        color: #94a3b8;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="hero-title">Bem-vindo ao Sobral Invest</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Sua plataforma completa de análise de investimentos</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🏆</div>
            <div class="feature-title">Rankings</div>
            <div class="feature-desc">
                Descubra as melhores ações através de rankings personalizados por valuation, 
                dividendos, crescimento e muito mais.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <div class="feature-title">Análise Detalhada</div>
            <div class="feature-desc">
                Análise completa de cada ativo com indicadores fundamentais, 
                valuation, Score CS e gráficos interativos.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Comparativo</div>
            <div class="feature-desc">
                Compare múltiplos ativos lado a lado para tomar 
                decisões de investimento mais assertivas.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🚀 Comece agora")
    st.info("Selecione uma opção no menu lateral para explorar todas as funcionalidades!")
