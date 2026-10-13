
import json
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="Reva 5 – Patiëntenplanning",
    page_icon="🏥",
    layout="wide",
)

SAVE_FILE = Path("planning.json")

TEAM = {
    "Ryan": "VPK",
    "Stephanie": "VPK",
    "Nadine": "VPK",
    "Tina": "VPK",
    "Vince": "VPK",
    "Wendy": "VPK",
    "Chantal": "VPK",
    "Fleur": "VPK",
    "Britt": "VPK",
    "Cat": "ZK",
    "Katrien": "ZK",
    "Kim": "ZK",
    "Lutgard": "ZK",
    "Mieke": "ZK",
}

ROOMS = list(range(3027, 3047))
DAYS = ["ma", "di", "wo", "do", "vr"]

DOUBLE_ROOMS = [(3034, 3035), (3036, 3037)]

MOBILITY_SCORE = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
}

DEFAULT_PATIENT = {
    "active": True,
    "mobility": "A",
    "shower": [],
    "wound": False,
}


def default_state():
    return {
        "day": "ma",
        "patients": {
            str(room): {
                "active": True,
                "mobility": "A",
                "shower": [],
                "wound": False,
            }
            for room in ROOMS
        },
        "working_team": list(TEAM.keys()),
        "medicatie_vpk": None,
    }


def load_data():
    if not SAVE_FILE.exists():
        return default_state()

    try:
        data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        state = default_state()

        state["day"] = data.get("day", "ma")
        state["working_team"] = [
            n for n in data.get("working_team", list(TEAM.keys()))
            if n in TEAM
        ]
        state["medicatie_vpk"] = data.get("medicatie_vpk")

        for room in ROOMS:
            saved = data.get("patients", {}).get(str(room), {})
            state["patients"][str(room)] = {
                "active": saved.get("active", True),
                "mobility": saved.get("mobility", "A"),
                "shower": saved.get("shower", []),
                "wound": saved.get("wound", False),
            }

        return state
    except Exception:
        return default_state()


def save_current_state():
    data = {
        "day": st.session_state.day,
        "patients": st.session_state.patients,
        "working_team": st.session_state.working_team,
        "medicatie_vpk": st.session_state.medicatie_vpk,
    }
    SAVE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def init_session():
    if "initialized" not in st.session_state:
        state = load_data()
        st.session_state.day = state["day"]
        st.session_state.patients = state["patients"]
        st.session_state.working_team = state["working_team"]
        st.session_state.medicatie_vpk = state["medicatie_vpk"]
        st.session_state.initialized = True


def patient_weight(patient, day):
    if not patient["active"]:
        return 0

    weight = MOBILITY_SCORE.get(patient["mobility"], 1)

    if day in patient["shower"]:
        weight += 1

    if patient["wound"]:
        weight += 2

    return weight


def is_double_start(room):
    return any(room == a for a, b in DOUBLE_ROOMS)


def get_double_partner(room):
    for a, b in DOUBLE_ROOMS:
        if room == a:
            return b
        if room == b:
            return a
    return None


def build_groups(day):
    """Build patient groups. Double rooms stay together."""
    groups = []
    used = set()

    for room in ROOMS:
        if room in used:
            continue

        patient = st.session_state.patients[str(room)]

        partner = get_double_partner(room)

        if partner is not None:
            used.add(room)
            used.add(partner)

            p2 = st.session_state.patients[str(partner)]

            active = patient["active"] or p2["active"]
            if not active:
                continue

            rooms = [room, partner]
            weight = patient_weight(patient, day) + patient_weight(p2, day)
            vpk_needed = patient["wound"] or p2["wound"]

            groups.append({
                "rooms": rooms,
                "weight": weight,
                "vpk_needed": vpk_needed,
            })
        else:
            used.add(room)

            if not patient["active"]:
                continue

            groups.append({
                "rooms": [room],
                "weight": patient_weight(patient, day),
                "vpk_needed": patient["wound"],
            })

    groups.sort(key=lambda x: x["weight"], reverse=True)
    return groups


def make_planning(day):
    selected = [
        n for n in st.session_state.working_team
        if n in TEAM
    ]

    # The medication VPK is not part of the gang distribution.
    gang = [
        n for n in selected
        if n != st.session_state.medicatie_vpk
    ]

    assignments = {
        n: {"role": TEAM[n], "weight": 0, "groups": []}
        for n in gang
    }

    if not gang:
        return assignments

    vpk_people = [n for n in gang if TEAM[n] == "VPK"]
    zk_people = [n for n in gang if TEAM[n] == "ZK"]

    for group in build_groups(day):
        candidates = vpk_people if group["vpk_needed"] and vpk_people else gang

        # Keep workload balanced. For ties, preserve the current team order.
        person = min(
            candidates,
            key=lambda n: assignments[n]["weight"]
        )

        assignments[person]["groups"].append(group)
        assignments[person]["weight"] += group["weight"]

    return assignments


def room_icons(room, day):
    p = st.session_state.patients[str(room)]
    icons = []

    if day in p["shower"]:
        icons.append("🚿")

    if p["wound"]:
        icons.append("🩹")

    return " ".join(icons)


def workload_label(weight):
    if weight <= 8:
        return "🟢 Licht"
    if weight <= 13:
        return "🟡 Normaal"
    return "🔴 Hoog"


def apply_loaded_state():
    state = load_data()
    st.session_state.day = state["day"]
    st.session_state.patients = state["patients"]
    st.session_state.working_team = state["working_team"]
    st.session_state.medicatie_vpk = state["medicatie_vpk"]


init_session()

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2rem;
        font-weight: 750;
        margin-bottom: 0;
    }
    .subtitle {
        color: #6b7280;
        margin-top: -4px;
        margin-bottom: 18px;
    }
    .card {
        padding: 16px;
        border: 1px solid rgba(128,128,128,.20);
        border-radius: 14px;
        margin-bottom: 10px;
    }
    .small-muted {
        color: #6b7280;
        font-size: .9rem;
    }
    .room-title {
        font-size: 1.05rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header ----------
c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

with c1:
    st.markdown('<div class="main-title">🏥 Reva 5 – Patiëntenplanning</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Overzicht, patiëntgegevens en evenwichtige gangverdeling</div>',
        unsafe_allow_html=True,
    )

with c2:
    st.session_state.day = st.selectbox(
        "Dag",
        DAYS,
        index=DAYS.index(st.session_state.day),
    )

with c3:
    if st.button("💾 Opslaan", use_container_width=True):
        save_current_state()
        st.success("Opgeslagen")

with c4:
    if st.button("↩️ Laden", use_container_width=True):
        apply_loaded_state()
        st.rerun()

st.divider()

# ---------- Tabs ----------
tab_overview, tab_patients, tab_team, tab_planning = st.tabs(
    ["🏠 Overzicht", "🛏️ Patiënten", "👥 Team", "📊 Planning"]
)

# ---------- Overview ----------
with tab_overview:
    active_rooms = sum(
        1 for room in ROOMS
        if st.session_state.patients[str(room)]["active"]
    )
    wound_rooms = sum(
        1 for room in ROOMS
        if st.session_state.patients[str(room)]["active"]
        and st.session_state.patients[str(room)]["wound"]
    )
    shower_rooms = sum(
        1 for room in ROOMS
        if st.session_state.patients[str(room)]["active"]
        and st.session_state.day in st.session_state.patients[str(room)]["shower"]
    )

    team_today = [
        n for n in st.session_state.working_team if n in TEAM
    ]
    gang_today = [
        n for n in team_today
        if n != st.session_state.medicatie_vpk
    ]

    a, b, c, d = st.columns(4)
    a.metric("Actieve kamers", active_rooms)
    b.metric("Wondzorg", wound_rooms)
    c.metric("Douche vandaag", shower_rooms)
    d.metric("Gangmedewerkers", len(gang_today))

    st.markdown("### Vandaag")
    left, right = st.columns(2)

    with left:
        st.info(
            f"**{st.session_state.day.upper()}** · "
            f"{len(gang_today)} medewerkers op de gang"
        )

        if st.session_state.medicatie_vpk:
            st.caption(
                f"💊 Medicatie-VPK: **{st.session_state.medicatie_vpk}** "
                f"(niet meegenomen in de gangverdeling)"
            )
        else:
            st.caption("💊 Nog geen medicatie-VPK aangeduid.")

    with right:
        st.caption("Dubbele kamers blijven altijd samen:")
        st.write("• 3034 + 3035")
        st.write("• 3036 + 3037")

    st.markdown("### Snelle acties")
    x, y = st.columns(2)
    with x:
        if st.button("📊 Planning maken", type="primary", use_container_width=True):
            st.session_state.show_planning = True
            st.rerun()
    with y:
        if st.button("🔄 Terug naar standaard", use_container_width=True):
            state = default_state()
            st.session_state.day = state["day"]
            st.session_state.patients = state["patients"]
            st.session_state.working_team = state["working_team"]
            st.session_state.medicatie_vpk = state["medicatie_vpk"]
            st.rerun()

# ---------- Patients ----------
with tab_patients:
    st.markdown("### 🛏️ Patiënten")

    st.caption(
        "Pas per kamer de mobiliteit, douche en wondzorg aan. "
        "Wondzorg maakt de patiënt VPK-gebonden en verhoogt de werkdruk."
    )

    for room in ROOMS:
        p = st.session_state.patients[str(room)]
        partner = get_double_partner(room)

        title = f"Kamer {room}"
        if partner:
            title += f"  ·  🔗 samen met {partner}"

        with st.container(border=True):
            top = st.columns([1.2, 1, 1, 1, 1.3])

            with top[0]:
                st.markdown(f"**{title}**")
                p["active"] = st.checkbox(
                    "Actief",
                    value=p["active"],
                    key=f"active_{room}",
                )

            with top[1]:
                p["mobility"] = st.selectbox(
                    "Mobiliteit",
                    list(MOBILITY_SCORE.keys()),
                    index=list(MOBILITY_SCORE.keys()).index(p["mobility"]),
                    key=f"mobility_{room}",
                )

            with top[2]:
                p["wound"] = st.checkbox(
                    "🩹 Wondzorg",
                    value=p["wound"],
                    key=f"wound_{room}",
                )

            with top[3]:
                p["shower"] = st.multiselect(
                    "🚿 Douche",
                    DAYS,
                    default=p["shower"],
                    key=f"shower_{room}",
                )

            with top[4]:
                weight = patient_weight(p, st.session_state.day)
                st.metric("Werkdruk", weight)
                flags = room_icons(room, st.session_state.day)
                if flags:
                    st.caption(flags)

# ---------- Team ----------
with tab_team:
    st.markdown("### 👥 Team")

    selected = st.multiselect(
        "Wie werkt vandaag?",
        list(TEAM.keys()),
        default=st.session_state.working_team,
    )
    st.session_state.working_team = selected

    vpk = [n for n in selected if TEAM[n] == "VPK"]
    zk = [n for n in selected if TEAM[n] == "ZK"]

    st.markdown("#### 💊 Medicatie")
    medication_options = ["Geen medicatie-VPK"] + vpk

    current_med = st.session_state.medicatie_vpk
    current_index = (
        medication_options.index(current_med)
        if current_med in medication_options
        else 0
    )

    medication_choice = st.selectbox(
        "Wie doet vandaag de medicatie?",
        medication_options,
        index=current_index,
    )

    st.session_state.medicatie_vpk = (
        None if medication_choice == "Geen medicatie-VPK"
        else medication_choice
    )

    st.markdown("#### Aanwezig team")
    tc1, tc2 = st.columns(2)

    with tc1:
        st.markdown("**VPK**")
        if vpk:
            for name in vpk:
                badge = "💊" if name == st.session_state.medicatie_vpk else "👤"
                st.write(f"{badge} **{name}**")
        else:
            st.caption("Geen VPK geselecteerd.")

    with tc2:
        st.markdown("**ZK**")
        if zk:
            for name in zk:
                st.write(f"👤 **{name}**")
        else:
            st.caption("Geen ZK geselecteerd.")

# ---------- Planning ----------
with tab_planning:
    st.markdown("### 📊 Planning")
    st.caption(
        f"Verdeling voor **{st.session_state.day.upper()}**. "
        "Dubbele kamers worden samen toegewezen; wondzorg gaat naar een VPK."
    )

    assignments = make_planning(st.session_state.day)

    if not assignments:
        st.warning("Selecteer eerst medewerkers voor de gang.")
    else:
        weights = [info["weight"] for info in assignments.values()]
        min_w = min(weights) if weights else 0
        max_w = max(weights) if weights else 0

        if max_w - min_w <= 3:
            st.success("🟢 De werkdruk is mooi verdeeld.")
        elif max_w - min_w <= 6:
            st.warning("🟡 De werkdruk is redelijk verdeeld.")
        else:
            st.error("🔴 De werkdruk is sterk verschillend verdeeld.")

        cols = st.columns(min(3, max(1, len(assignments))))

        for idx, (name, info) in enumerate(assignments.items()):
            with cols[idx % len(cols)]:
                st.markdown('<div class="card">', unsafe_allow_html=True)

                role = info["role"]
                st.markdown(
                    f"### {'🩺' if role == 'VPK' else '👤'} {name}"
                )
                st.caption(role)

                st.metric(
                    "Werkdruk",
                    info["weight"],
                    delta=workload_label(info["weight"]),
                )

                if not info["groups"]:
                    st.caption("Geen patiënten toegewezen.")
                else:
                    for group in info["groups"]:
                        room_text = " + ".join(map(str, group["rooms"]))
                        icons = " ".join(
                            room_icons(r, st.session_state.day)
                            for r in group["rooms"]
                        ).strip()

                        suffix = f"  {icons}" if icons else ""
                        vpk_flag = " 🩹 VPK" if group["vpk_needed"] else ""

                        st.write(
                            f"**{room_text}** · {group['weight']} pt"
                            f"{suffix}{vpk_flag}"
                        )

                st.markdown("</div>", unsafe_allow_html=True)

        st.divider()
        st.caption(
            "Werkdrukscore: mobiliteit A=1 t/m E=5 · douche=+1 · wondzorg=+2. "
            "De medicatie-VPK wordt niet meegenomen in deze verdeling."
        )

# Keep data synchronized so a normal Streamlit rerun doesn't lose edits.
if st.session_state.get("auto_save", False):
    save_current_state()
