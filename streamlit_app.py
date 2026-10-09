import streamlit as st
st.title("JF Clientes")
st.header("Clientes")
nombre = st.text_input("Nombre del cliente")
telefono = st.text_input("Teléfono")
email = st.text_input("Email")
notas = st.text_area("Notas")
if st.button("Guardar cliente"):
    st.success("Cliente guardado")
    
