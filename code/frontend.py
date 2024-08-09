import streamlit as st
import backend as rgb

st.set_page_config(page_title="Q&A sobre las leyes de tráfico vial")

# App title
title_html = '''
<p style="font-family:sans-serif; color:#8B0000; font-size: 42px; text-align:center;">
     <strong>Q&A sobre las leyes de tráfico vial</strong> 
</p>
<p style="font-family:sans-serif; color:#FFD700; font-size: 18px; text-align:center;">
    Conoce las respuestas a tus preguntas sobre las normas de tráfico
</p>
'''
st.markdown(title_html, unsafe_allow_html=True)

# Starting vector indexer
if 'vector_index' not in st.session_state:
    with st.spinner("📀 Espera un momento, estamos trabajando..."):
        st.session_state.vector_index = rgb.document_indexing()

# Here the user will ask the question
input_text = st.text_area("Introduce tu consulta:", label_visibility="collapsed")

# Buttom to send the question
if st.button("Enviar", type="primary"):
    if input_text.strip():
        # Giving my llm consciousness
        with st.spinner("Pensando..."):
            response_content = rgb.create_qa_chain().invoke({"input": input_text, "chat_history": []})
            st.write(response_content["answer"])
    else:
        st.warning("Por favor, introduce un texto antes de enviar.")
