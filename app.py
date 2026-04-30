import streamlit as st

aantal_verplegers = st.selectbox("Aantal verpleegkundigen", [2, 3, 4, 5, 6])
kamers = list(range(3027, 3047))
verplegers = [f"V{i+1}" for i in range(aantal_verplegers)]
dagen = ["ma", "di", "wo", "do", "vr"]

st.title("🧑‍⚕️ Patiëntenverdeling")

dag = st.selectbox("Kies dag", dagen)

st.subheader("Gegevens per kamer")

patiënten = []

# score mapping
score_map = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5
}

for kamer in kamers:
    col1, col2, col3 = st.columns(3)

    with col1:
        actief = st.checkbox(f"Kamer {kamer} actief", value=True, key=f"actief_{kamer}")

    with col2:
        mobiliteit = st.selectbox(
            f"Kamer {kamer} mobiliteit",
            ["A", "B", "C", "D", "E"],
            key=f"mob_{kamer}"
        )

    with col3:
        douche = st.multiselect(
            f"Douche {kamer}",
            dagen,
            key=f"douche_{kamer}"
        )

    zorgscore = score_map[mobiliteit]

    # alleen toevoegen als kamer NIET leeg is
    if actief:
        patiënten.append({
            "kamer": kamer,
            "zorgzwaarte": zorgscore,
            "mobiliteit": mobiliteit,
            "douche_dagen": douche
        })


def verdeel(patiënten, dag):
    planning = {v: [] for v in verplegers}
    werkdruk = {v: 0 for v in verplegers}

    for p in patiënten:
        gewicht = p["zorgzwaarte"]
        if dag in p["douche_dagen"]:
            gewicht += 1
        p["gewicht"] = gewicht

    patiënten_sorted = sorted(patiënten, key=lambda x: x["gewicht"], reverse=True)

    for p in patiënten_sorted:
        v = min(werkdruk, key=werkdruk.get)
        planning[v].append(p)
        werkdruk[v] += p["gewicht"]

    return planning, werkdruk


if st.button("📊 Maak planning"):
    planning, werkdruk = verdeel(patiënten, dag)

    st.subheader(f"Planning voor {dag}")

    for v in planning:
        st.markdown(f"### {v} (werkdruk: {werkdruk[v]})")

        for p in sorted(planning[v], key=lambda x: x["kamer"]):
            douche = "🚿" if dag in p["douche_dagen"] else ""
            st.write(f"Kamer {p['kamer']} | {p['mobiliteit']} | zorg {p['zorgzwaarte']} {douche}")