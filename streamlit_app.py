from supabase import create_client
import csv
import os
archivo = "clientes.csv"
if not os.path.exists(archivo):
    with open(archivo, "w", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["nombre", "telefono", "email", "notas"])
import pandas as pd
import streamlit as st
supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
st.title("JF Clientes")
st.header("Clientes")
nombre = st.text_input("Nombre del cliente")
telefono = st.text_input("Teléfono")
email = st.text_input("Email")
notas = st.text_area("Notas")
if st.button("Guardar cliente"):
    supabase.table("clientes").insert({"nombre": nombre}).execute()

st.subheader("Clientes guardados")
st.subheader("Personas de contacto")
contacto = st.text_input("Nombre del contacto")
cargo = st.text_input("Cargo del contacto")
telefono_contacto = st.text_input("Teléfono del contacto")
email_contacto = st.text_input("Email del contacto")
cliente_contacto = st.selectbox("Cliente al que pertenece", pd.read_csv("clientes.csv")["nombre"].dropna().unique())
if st.button("Guardar contacto"):
      with open("contactos.csv", "a", newline="") as f:
                csv.writer(f).writerow([cliente_contacto, contacto, cargo, telefono_contacto, email_contacto])
                st.success("Contacto guardado correctamente")
if os.path.exists(archivo):
         st.dataframe(pd.read_csv(archivo))
         st.subheader("Contactos guardados")
         if os.path.exists("contactos.csv"):
               st.dataframe(pd.read_csv("contactos.csv", header=None))

               st.subheader("Consultar cliente")
               clientes = pd.read_csv("clientes.csv")
               cliente_elegido = st.selectbox("Selecciona un cliente", clientes["nombre"])
               st.subheader("Contactos de " + cliente_elegido)
               contactos = pd.read_csv("contactos.csv", header=None)
               contactos_cliente = contactos[contactos[0].astype(str).str.strip().str.upper() == cliente_elegido.strip().upper()]
               st.dataframe(contactos_cliente)
    



