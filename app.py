import streamlit as st
import pandas as pd
import random
import requests
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="BM Hospital ER Command Center", layout="wide")

# ---------------- UI ----------------
st.markdown("""
<style>
.stApp {
    background:
        linear-gradient(rgba(12,12,12,0.90), rgba(12,12,12,0.95)),
        url("https://images.unsplash.com/photo-1587351021759-3e566b6af7cc");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    background-blend-mode: multiply;
}
.block-container {
    background: rgba(20,20,20,0.75);
    padding: 20px;
    border-radius: 12px;
}
* { color: #f5f5f5 !important; }
section[data-testid="stSidebar"] {
    background: rgba(0,0,0,0.95);
}
.alert-red {
    background: rgba(255,77,77,0.25);
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 8px;
}
.alert-yellow {
    background: rgba(255,193,7,0.25);
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 8px;
}
.alert-green {
    background: rgba(76,175,80,0.25);
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.title("🚑 ER Command Panel")

mode = st.sidebar.radio(
    "Simulation Mode",
    ["Demo (1 min)", "Real (15 min)", "Real (30 min)"]
)

interval = {
    "Demo (1 min)": timedelta(minutes=1),
    "Real (15 min)": timedelta(minutes=15),
    "Real (30 min)": timedelta(minutes=30)
}[mode]

TOTAL_BEDS = 50
TOTAL_DOCS = 10

# ---------------- SESSION ----------------
if "patients" not in st.session_state:
    st.session_state.patients = pd.DataFrame(columns=[
        "PatientID","Triage","WaitTime","Department","ArrivalTime"
    ])

if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Time","Admissions"])

if "weather_history" not in st.session_state:
    st.session_state.weather_history = pd.DataFrame(columns=["Time","WeatherScore"])

if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now()

# ---------------- SIMULATION ----------------
now = datetime.now()

if now - st.session_state.last_update >= interval:

    hour = now.hour

    # -------- BASE ARRIVAL --------
    if 8 <= hour <= 11:
        arrivals = random.randint(3,6)
    elif 18 <= hour <= 22:
        arrivals = random.randint(4,7)
    else:
        arrivals = random.randint(1,3)

    # -------- WEATHER MULTIPLIER --------
    weather_multiplier = 1

    if "weather_history" in st.session_state and not st.session_state.weather_history.empty:
        latest_weather = st.session_state.weather_history["WeatherScore"].iloc[-1]

        if latest_weather >= 2:
            weather_multiplier = 2
        elif latest_weather == 1:
            weather_multiplier = 1.5

    arrivals = int(arrivals * weather_multiplier)

    # -------- PATIENT GENERATION WITH WEATHER TRIAGE --------
    for _ in range(arrivals):

        triage = random.randint(1,5)

        if not st.session_state.weather_history.empty:
            latest_weather = st.session_state.weather_history["WeatherScore"].iloc[-1]

            if latest_weather >= 2:
                triage = random.choices([1,2,3,4,5], weights=[30,25,20,15,10])[0]
            elif latest_weather == 1:
                triage = random.choices([1,2,3,4,5], weights=[10,30,30,20,10])[0]

        st.session_state.patients = pd.concat([
            st.session_state.patients,
            pd.DataFrame([{
                "PatientID": f"P{random.randint(1000,9999)}",
                "Triage": triage,
                "WaitTime": 0,
                "Department": random.choice(["ER","Cardiology","Orthopedics","Neurology"]),
                "ArrivalTime": now.strftime("%H:%M:%S")
            }])
        ], ignore_index=True)


    # -------- DISCHARGE LOGIC (TRACKING) 🔥 --------
# -------- DISCHARGE LOGIC (WAIT-TIME BASED) 🔥 --------
discharged_now = 0

if not st.session_state.patients.empty:

    discharge_rate = 0.1  # 10% leave per cycle
    discharge_count = int(len(st.session_state.patients) * discharge_rate)

    if discharge_count > 0:
        discharged_now = discharge_count

        # Initialize discharged storage
        if "discharged" not in st.session_state:
            st.session_state.discharged = pd.DataFrame(
                columns=st.session_state.patients.columns
            )

        # Select patients with highest wait time
        discharged_patients = (
            st.session_state.patients
            .sort_values(by="WaitTime", ascending=False)
            .iloc[:discharge_count]
        )

        # Add to discharged list
        st.session_state.discharged = pd.concat(
            [st.session_state.discharged, discharged_patients],
            ignore_index=True
        )

        # Remove from active patients
        remaining_patients = st.session_state.patients.drop(discharged_patients.index)
        st.session_state.patients = remaining_patients.reset_index(drop=True)

# Store last cycle discharge count
    st.session_state.last_discharged = discharged_now

    # -------- STORE HISTORY --------
    st.session_state.history = pd.concat([
        st.session_state.history,
        pd.DataFrame({"Time":[now],"Admissions":[arrivals]})
    ], ignore_index=True)

    st.session_state.last_update = now

# -------- WAIT TIME UPDATE --------
if not st.session_state.patients.empty:
    st.session_state.patients["WaitTime"] += 1

# ---------------- HEADER ----------------
st.title("🏥 BM Hospital – ER Command Center")
st.caption("⚡ Real-Time Emergency Operation Dashboard")

# ---------------- KPIs ----------------
col1, col2, col3 = st.columns(3)

occupancy = len(st.session_state.patients)
avg_wait = st.session_state.patients["WaitTime"].mean() if occupancy else 0
critical = len(st.session_state.patients[st.session_state.patients["Triage"] == 1])

col1.metric("🏥 ER Occupancy", occupancy)
col2.metric("⏳ Avg Wait Time (mins)", f"{avg_wait:.1f}")
col3.metric("🚨 Critical Patients", critical)

# ---------------- SIDEBAR TRIAGE INSIGHTS ----------------
st.sidebar.markdown("### 🚑 Triage Insights")

if not st.session_state.patients.empty:

    critical_count = len(st.session_state.patients[
        st.session_state.patients["Triage"] == 1
    ])

    moderate_count = len(st.session_state.patients[
        st.session_state.patients["Triage"].isin([2,3])
    ])

    stable_count = len(st.session_state.patients[
        st.session_state.patients["Triage"] >= 4
    ])

    st.sidebar.markdown(f"""
    <div class="alert-red">
    🔴 <b>Critical (Triage 1)</b><br>
    Immediate attention required<br>
    Patients: {critical_count}
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(f"""
    <div class="alert-yellow">
    🟠 <b>Moderate (Triage 2–3)</b><br>
    Urgent but stable<br>
    Patients: {moderate_count}
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(f"""
    <div class="alert-green">
    🟢 <b>Stable (Triage 4–5)</b><br>
    Non-critical<br>
    Patients: {stable_count}
    </div>
    """, unsafe_allow_html=True)

# ---------------- CAPACITY ----------------
bed_util = (occupancy / TOTAL_BEDS) * 100
doc_ratio = occupancy / TOTAL_DOCS if TOTAL_DOCS else 0

st.sidebar.markdown("### 📊 Capacity Insights")
st.sidebar.write(f"🛏️ Bed Utilization: {bed_util:.1f}%")
st.sidebar.write(f"👨‍⚕️ Patient/Doctor Ratio: {doc_ratio:.1f}")

# ---------------- PATIENT TABLE ----------------
st.subheader("📋 Live Patient Feed (Wait Time in Minutes)")

def highlight(row):
    if row["Triage"] == 1:
        return ['background-color: #ff4d4d']*len(row)
    elif row["Triage"] <= 3:
        return ['background-color: #ffb84d']*len(row)
    else:
        return ['background-color: #4CAF50']*len(row)

st.dataframe(
    st.session_state.patients.style.apply(highlight, axis=1),
    width="stretch"
)

# ---------------- INPATIENT vs OUTPATIENT ----------------
st.subheader("🏥 Patient Flow Analysis")

col1, col2, col3 = st.columns(3)

inpatients = len(st.session_state.patients)
outpatients = len(st.session_state.discharged) if "discharged" in st.session_state else 0
recent_discharged = st.session_state.last_discharged if "last_discharged" in st.session_state else 0

col1.metric("🛏️ Current Inpatients", inpatients)
col2.metric("📤 Total Discharged (Cumulative)", outpatients)
col3.metric("🔄 Discharged This Cycle", recent_discharged)

# -------- INSIGHT --------
st.markdown("### 📊 Discharge Insight")

if inpatients > 0:
    st.info(
        "Patients are discharged gradually to maintain ER capacity. "
        "Around 10% of patients are discharged each cycle based on treatment completion."
    )

    st.write(
        "⏱️ **Understanding Flow:** Patients with higher wait times are more likely to be discharged, "
        "ensuring continuous patient movement and availability of beds."
    )

# -------- VIEW DISCHARGED PATIENTS (OPTIONAL) --------
if "discharged" in st.session_state and not st.session_state.discharged.empty:
    with st.expander("📄 View Recently Discharged Patients"):
        st.dataframe(st.session_state.discharged.tail(10), width="stretch")

# ---------------- DEPARTMENT LOAD ----------------
st.subheader("🏥 Department Load Analysis")

if not st.session_state.patients.empty:

    dept_load = st.session_state.patients["Department"].value_counts()

    st.bar_chart(dept_load)

    overloaded = dept_load.idxmax()
    st.warning(f"⚠️ Most Loaded Department: {overloaded}")

# ---------------- WEATHER ----------------
st.subheader("🌦️ Weather Impact & Admission Spike Trend")

API_KEY = "e111746cf0d91193bf5098883b66a983"
CITY = "Coimbatore"

try:
    response = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric",
        timeout=5
    )
    data = response.json()

    # SAFETY CHECK
    if "main" not in data:
        st.warning("Weather data unavailable")
    else:
        temp = data["main"]["temp"]
        condition = data["weather"][0]["main"]

        st.write(f"📍 {CITY} | 🌡️ {temp}°C | 🌥️ {condition}")

        # -------- WEATHER SCORE --------
        weather_score = 0
        if temp > 35:
            weather_score += 2
        if condition.lower() in ["rain", "storm"]:
            weather_score += 2

        st.metric("🌦️ Weather Impact Score", weather_score)

        # -------- MULTIPLIER --------
        weather_multiplier = 1
        if weather_score >= 2:
            weather_multiplier = 2
        elif weather_score == 1:
            weather_multiplier = 1.5

        # -------- MULTIPLIER INSIGHT 🔥 --------
        if weather_multiplier == 1:
            st.success(f"🟢 Normal Conditions | Multiplier: x1")
            st.write("Patient inflow is stable. No unusual impact from weather.")

        elif weather_multiplier == 1.5:
            st.warning(f"🟠 Moderate Impact | Multiplier: x1.5")
            st.write("Slight increase in patient inflow due to weather conditions (e.g., heat). Expect moderate workload.")

        elif weather_multiplier == 2:
            st.error(f"🔴 High Surge Alert | Multiplier: x2")
            st.write("Severe weather conditions detected. Patient inflow has doubled and may strain hospital resources.")

        # -------- CAUSE → EFFECT INSIGHT 🔥 --------
        st.markdown("### 📊 Operational Insight")

        if weather_score >= 2:
            st.markdown(
                "🚨 **Cause:** Extreme weather (high temperature or storm)\n\n"
                "📈 **Effect:** Sudden spike in emergency cases such as accidents, heat strokes, and critical conditions.\n\n"
                "🏥 **Impact:** ER occupancy and wait times are expected to increase significantly."
            )

        elif weather_score == 1:
            st.markdown(
                "⚠️ **Cause:** Moderate weather impact (e.g., heat)\n\n"
                "📈 **Effect:** Increase in moderate cases like fatigue or dehydration.\n\n"
                "🏥 **Impact:** Slight rise in patient inflow and workload."
            )

        else:
            st.markdown(
                "✅ **Cause:** Stable weather conditions\n\n"
                "📈 **Effect:** Normal patient flow.\n\n"
                "🏥 **Impact:** No additional strain on hospital operations."
            )

        # -------- STORE WEATHER HISTORY --------
        st.session_state.weather_history = pd.concat([
            st.session_state.weather_history,
            pd.DataFrame({
                "Time": [datetime.now()],
                "WeatherScore": [weather_score]
            })
        ], ignore_index=True)

        # -------- COMBINED TREND --------
        if (
            not st.session_state.weather_history.empty
            and not st.session_state.history.empty
        ):

            weather_df = st.session_state.weather_history.copy()
            admission_df = st.session_state.history.copy()

            weather_df["Time"] = pd.to_datetime(weather_df["Time"])
            admission_df["Time"] = pd.to_datetime(admission_df["Time"])

            weather_df = weather_df.sort_values("Time")
            admission_df = admission_df.sort_values("Time")

            combined = pd.merge_asof(
                weather_df,
                admission_df,
                on="Time",
                direction="nearest"
            )

            # -------- DISPLAY --------
            if len(combined) < 3:
                st.info("Collecting data... trend will appear shortly ⏳")
            else:
                combined = combined.set_index("Time")
                combined = combined[["WeatherScore", "Admissions"]]

                combined.columns = ["Weather Score", "Admissions"]

                st.subheader("📈 Weather vs Admissions Trend")
                st.line_chart(combined, width="stretch")

                # -------- SPIKE INSIGHT --------
                w = combined["Weather Score"].tail(3).mean()
                a = combined["Admissions"].tail(3).mean()

                if w >= 2 and a >= 3:
                    st.sidebar.markdown(
                        '<div class="alert-red">🚨 Weather Driving ER Surge</div>',
                        unsafe_allow_html=True
                    )
                elif w > 0:
                    st.sidebar.markdown(
                        '<div class="alert-yellow">⚠️ Weather Impact Moderate</div>',
                        unsafe_allow_html=True
                    )

except Exception as e:
    st.warning("Weather unavailable")

# ---------------- DOWNLOAD ----------------
st.download_button(
    "📥 Export Data",
    st.session_state.patients.to_csv(index=False),
    "patients.csv"
)

# ---------------- AUTO REFRESH ----------------
time.sleep(5)
st.rerun()
