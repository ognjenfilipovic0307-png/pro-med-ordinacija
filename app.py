import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF

# --- KONFIGURACIJA I DIZAJN ---
st.set_page_config(page_title="PRO Med-Sistem", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stExpander { background-color: white; border-radius: 10px; box-shadow: 0px 2px 10px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA PODATAKA (SQLITE) ---
conn = sqlite3.connect('med_pro_v1.db', check_same_thread=False)
c = conn.cursor()

def inicijalizuj_bazu():
    # Proširena tabela pacijenata sa "tonom podataka"
    c.execute('''CREATE TABLE IF NOT EXISTS pacijenti
                 (id INTEGER PRIMARY KEY, ime TEXT, prezime TEXT, jmbg TEXT, lbo TEXT,
                  broj_kartona TEXT, datum_rodjenja TEXT, pol TEXT, adresa TEXT,
                  telefon TEXT, email TEXT, krvna_grupa TEXT, alergije TEXT, hronicne_bolesti TEXT)''')
   
    # Tabela za posete (sveobuhvatna)
    c.execute('''CREATE TABLE IF NOT EXISTS posete
                 (id INTEGER PRIMARY KEY, pac_id INTEGER, datum TEXT, tip_posete TEXT,
                  nacin_placanja TEXT, dokument_tip TEXT, dijagnoza_kod TEXT, dijagnoza_opis TEXT,
                  terapija TEXT, anamneza TEXT, status_organa TEXT, lab_nalaz TEXT,
                  bolovanje_start TEXT, bolovanje_end TEXT, cena REAL)''')
    conn.commit()

inicijalizuj_bazu()

# --- NAVIGACIJA ---
st.sidebar.title("🏥 PRO MEDIC")
opcija = st.sidebar.radio("Navigacija", ["Pretraga i Izbor Pacijenta", "Registracija Novog Pacijenta", "Arhiva Pregleda", "Finansijski Izveštaj"])

# --- MODUL 1: REGISTRACIJA (SA SVIM PODACIMA) ---
if opcija == "Registracija Novog Pacijenta":
    st.header("📋 Registracija pacijenta u sistem")
    with st.form("registracija"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ime = st.text_input("Ime *")
            prezime = st.text_input("Prezime *")
            jmbg = st.text_input("JMBG (13 cifara) *")
        with col2:
            lbo = st.text_input("LBO (11 cifara)")
            br_kartona = st.text_input("Broj zdravstvenog kartona")
            dat_rodj = st.date_input("Datum rođenja")
        with col3:
            pol = st.selectbox("Pol", ["M", "Ž"])
            krvna_grupa = st.selectbox("Krvna grupa", ["A+", "A-", "B+", "B-", "AB+", "AB-", "0+", "0-", "Nepoznato"])
            telefon = st.text_input("Kontakt telefon")
       
        st.divider()
        col4, col5 = st.columns(2)
        with col4:
            adresa = st.text_input("Adresa stanovanja")
            email = st.text_input("E-mail adresa")
        with col5:
            alergije = st.text_area("Alergije (Lekovi, hrana...)", placeholder="Napišite 'Nema' ako ne postoje")
            hronika = st.text_area("Hronične bolesti / Prethodne operacije")

        if st.form_submit_button("SAČUVAJ PACIJENTA U BAZU"):
            if ime and prezime and jmbg:
                c.execute('''INSERT INTO pacijenti (ime, prezime, jmbg, lbo, broj_kartona, datum_rodjenja, pol, adresa, telefon, email, krvna_grupa, alergije, hronicne_bolesti)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (ime, prezime, jmbg, lbo, br_kartona, str(dat_rodj), pol, adresa, telefon, email, krvna_grupa, alergije, hronika))
                conn.commit()
                st.success(f"Pacijent {ime} {prezime} je uspešno registrovan!")
            else:
                st.error("Polja sa zvezdicom (*) su obavezna!")

# --- MODUL 2: PRETRAGA I IZBOR (ZA NOVU POSETU) ---
elif opcija == "Pretraga i Izbor Pacijenta":
    st.header("🔍 Pronađi pacijenta za pregled")
    search_query = st.text_input("Pretraži po prezimenu ili JMBG-u")
   
    if search_query:
        query = f"SELECT id, ime, prezime, jmbg, broj_kartona, alergije FROM pacijenti WHERE prezime LIKE '%{search_query}%' OR jmbg LIKE '%{search_query}%'"
        rezultati = pd.read_sql(query, conn)
       
        if not rezultati.empty:
            st.write("Pronađeni pacijenti:")
            for index, row in rezultati.iterrows():
                with st.expander(f"👤 {row['ime']} {row['prezime']} | JMBG: {row['jmbg']} | Karton: {row['broj_kartona']}"):
                    st.warning(f"⚠️ Alergije: {row['alergije']}")
                    if st.button(f"Započni novu posetu za {row['ime']}", key=row['id']):
                        st.session_state['trenutni_pacijent'] = row.to_dict()
                        st.info("Pacijent izabran. Pređite na popunjavanje nalaza ispod.")

    # --- SEKCIJA: UNOS POSRETE (OTVARA SE KADA JE PACIJENT IZABRAN) ---
    if 'trenutni_pacijent' in st.session_state:
        tp = st.session_state['trenutni_pacijent']
        st.divider()
        st.subheader(f"📝 Obrada posete: {tp['ime']} {tp['prezime']}")
       
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1:
                dat_posete = st.date_input("Datum", datetime.now())
                tip_p = st.selectbox("Tip posete", ["Redovni pregled", "Sistematski", "Kontrola", "Bolovanje", "Hitno"])
            with c2:
                placanje = st.selectbox("Plaćanje", ["Keš", "Kartica", "Virman", "Osiguranje"])
                iznos = st.number_input("Cena (RSD)", min_value=0.0)
            with c3:
                dok_tip = st.selectbox("Vrsta dokumenta", ["Lekarski izveštaj", "Uputnica", "Recept", "Potvrda o bolovanju"])

            st.divider()
           
            # Klinički deo
            tab_med, tab_lab, tab_bol = st.tabs(["🩺 Pregled i Dijagnoza", "🧪 Laboratorija", "📅 Bolovanje & Sistematski"])
           
            with tab_med:
                anamneza = st.text_area("Anamneza (Tegobe pacijenta)")
                col_d1, col_d2 = st.columns([1,3])
                with col_d1:
                    dij_kod = st.text_input("MKB-10 Šifra")
                with col_d2:
                    dij_opis = st.text_input("Opis dijagnoze")
                terapija = st.text_area("Propisana terapija i savet")

            with tab_lab:
                lab_nalaz = st.text_area("Unos laboratorijskih parametara (Le, Er, Hb, Glu...)")
           
            with tab_bol:
                if tip_p == "Bolovanje":
                    b_od = st.date_input("Početak bolovanja")
                    b_do = st.date_input("Kraj bolovanja")
                else: b_od, b_do = None, None
               
                if tip_p == "Sistematski":
                    status_org = st.text_area("Detaljan status po sistemima (KVS, RS, GIT, CNS...)")
                else: status_org = ""

            if st.button("FINALIZUJ, SAČUVAJ I ŠTAMPAJ"):
                c.execute('''INSERT INTO posete (pac_id, datum, tip_posete, nacin_placanja, dokument_tip, dijagnoza_kod, dijagnoza_opis, terapija, anamneza, status_organa, lab_nalaz, bolovanje_start, bolovanje_end, cena)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (tp['id'], str(dat_posete), tip_p, placanje, dok_tip, dij_kod, dij_opis, terapija, anamneza, status_org, lab_nalaz, str(b_od), str(b_do), iznos))
                conn.commit()
                st.success("Poseta je trajno sačuvana u elektronski karton!")
                # Ovde bi išla funkcija za PDF...

# --- MODUL 3: ARHIVA ---
elif opcija == "Arhiva Pregleda":
    st.header("📂 Elektronska arhiva kartona")
    arhiva = pd.read_sql('''SELECT p.ime, p.prezime, v.datum, v.tip_posete, v.dijagnoza_kod, v.dijagnoza_opis
                            FROM posete v JOIN pacijenti p ON v.pac_id = p.id ORDER BY v.id DESC''', conn)
    st.table(arhiva)

# --- MODUL 4: FINANSIJE ---
elif opcija == "Finansijski Izveštaj":
    st.header("💰 Pregled prometa")
    fin = pd.read_sql("SELECT datum, nacin_placanja, cena FROM posete", conn)
    if not fin.empty:
        st.metric("Ukupna zarada (RSD)", f"{fin['cena'].sum():,.2f}")
        st.bar_chart(fin.groupby('nacin_placanja')['cena'].sum())
