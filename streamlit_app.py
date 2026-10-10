import csv
import os
archivo = "clientes.csv"
if not os.path.exists(archivo):
    with open(archivo, "w", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["nombre", "telefono", "email", "notas"])
import pandas as pd
import streamlit as st
st.title("JF Clientes")
st.header("Clientes")
nombre = st.text_input("Nombre del cliente")
telefono = st.text_input("Teléfono")
email = st.text_input("Email")
notas = st.text_area("Notas")
if st.button("Guardar cliente"):
    with open(archivo, "a",newline="") as f:
            f.write("\n")
            csv.writer(f).writerow([nombre, telefono, email, notas])

    st.success("Cliente guardado")

st.subheader("Clientes guardados")
if os.path.exists(archivo):
         st.dataframe(pd.read_csv(archivo))
    



