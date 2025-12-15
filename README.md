<div align="center">
  <img src="backend/assets/logo.png" alt="MojiTranslateAI Logo" width="200" />

  # MojiTranslateAI 🎌🤖
</div>

**MojiTranslateAI** é um pipeline automatizado avançado projetado para traduzir mangás e quadrinhos. Ele utiliza um sistema de IA multi-agente para lidar com cada etapa do processo de localização: desde a detecção de balões de texto até OCR, tradução, limpeza e diagramação (typesetting).

O projeto apresenta um **Editor Web Interativo** moderno que permite aos usuários refinar traduções, estilos e posicionamento em tempo real antes de exportar a página final.

---

## 🚀 Principais Funcionalidades

### 1. **Pipeline de IA Completo**
*   **Detecção de Regiões:** Identifica automaticamente balões de texto e painéis.
*   **OCR (Reconhecimento Óptico de Caracteres):** Extrai texto em japonês (ou outros idiomas de origem) usando modelos especializados (ex: MangaOCR).
*   **Tradução Ciente de Contexto:** Usa LLMs (GPT-4o) para traduzir o texto preservando o contexto, tom do falante e nuances.
*   **Limpeza e Redesenho Inteligente (Smart Cleaning & Redraw):** Remove automaticamente o texto original e preenche o fundo (inpainting) para preparar para o novo texto.

### 2. **Editor Interativo HTML-First**
*   **Diagramação WYSIWYG:** Edite o texto diretamente na página com uma experiência semelhante ao Microsoft Word.
*   **Estilização de Texto Rica:** Controle Família da Fonte, Tamanho, Cor, Espessura da Borda (Stroke), Altura da Linha e Alinhamento.
*   **Arrastar e Soltar:** Mova, redimensione e rotacione blocos de texto facilmente.
*   **Pré-visualização em Tempo Real:** Veja as alterações instantaneamente sem precisar renderizar a imagem inteira novamente.

### 3. **Gerenciamento de Fluxo de Trabalho**
*   **Visualizador Passo a Passo:** Verifique cada etapa do pipeline (Regiões -> OCR -> Tradução -> Limpeza e Redesenho -> Final).
*   **Ajustes Manuais:** Corrija erros de OCR, ajuste traduções ou conserte regiões manualmente se a IA deixar passar algo.

---

## 🛠️ Tecnologias Utilizadas

### Backend
*   **Linguagem:** Python 3.10+
*   **Framework:** FastAPI
*   **Integração de IA:** OpenAI API (GPT-4o Vision), PyTorch (para modelos de visão locais).
*   **Processamento de Imagem:** OpenCV, Pillow, Lama (Inpainting).

### Frontend (v2)
*   **Biblioteca:** React 18
*   **Ferramenta de Build:** Vite
*   **Linguagem:** TypeScript
*   **Estilização:** TailwindCSS
*   **Ícones:** Lucide React

---

## 📦 Instalação

### Pré-requisitos
*   Python 3.10+
*   Node.js 18+
*   GPU compatível com CUDA (Recomendado para OCR/Inpainting local)

### Configuração do Backend
1.  Navegue até o diretório do backend:
    ```bash
    cd backend
    ```
2.  Crie um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # ou venv\Scripts\activate no Windows
    ```
3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
4.  Rode o servidor:
    ```bash
    uvicorn app.main:app --reload
    ```

### Configuração do Frontend
1.  Navegue até o diretório do frontend:
    ```bash
    cd backend/frontend_v2
    ```
2.  Instale as dependências:
    ```bash
    npm install
    ```
3.  Inicie o servidor de desenvolvimento:
    ```bash
    npm run dev
    ```

---

## 📖 Como Usar

1.  **Enviar um Capítulo:** Use o painel para criar um novo trabalho (job) e fazer upload das páginas do mangá.
2.  **Rodar o Pipeline:** O sistema processará as páginas através do fluxo de trabalho definido.
3.  **Revisar e Editar:** Abra o **Visualizador do Pipeline** (Pipeline Viewer) para inspecionar os resultados.
    *   *Tradução:* Verifique o texto traduzido.
    *   *Limpeza e Redesenho:* Verifique o preenchimento do fundo (inpainting).
    *   *Final:* Use o **Editor Interativo** para estilizar o texto (Fontes, Cores, Rotação) e posicioná-lo perfeitamente.
4.  **Exportar:** Salve o resultado final.

### 🎥 Tutorial em Vídeo
Confira o tutorial detalhado de uso: [Assistir no YouTube](https://www.youtube.com/watch?v=qHnFcLuT_fA)

---

## 📝 Licença
[MIT](LICENSE)
