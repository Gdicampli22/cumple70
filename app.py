import datetime
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# CONFIGURACIÓN GENERAL Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="70° Cumpleaños de Mamá — Centro de Comando",
    page_icon="🎂",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { background-color: #faf9f6; }
    .emotional-banner {
        background: linear-gradient(135deg, #fff0f3 0%, #ffe3e9 100%);
        border: 1px solid #ffccd5;
        padding: 22px;
        border-radius: 14px;
        text-align: center;
        color: #800f2f;
        margin-bottom: 20px;
    }
    .badge-ok { background: #d8f3dc; color: #1b4332; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    .badge-warn { background: #ffe5d9; color: #9d0208; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    .badge-info { background: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

DB_FILE = "mom_birthday.db"

# ==========================================
# GESTIÓN DE BASE DE DATOS SQLITE
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS categories (name TEXT PRIMARY KEY)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, phone TEXT, rol TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, tipo TEXT, categoria TEXT, responsable TEXT,
            prioridad TEXT, limite TEXT, estado TEXT, avance INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT, categoria TEXT, cantidad INTEGER, unidad TEXT,
            responsable TEXT, limite TEXT, estimado REAL, real REAL, estado TEXT, lugar TEXT
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT)")

    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        default_settings = {
            "event_name": "70° Cumpleaños de Mamá",
            "event_date": "2026-10-17",
            "total_budget": "1500000",
            "currency": "$",
            "alert_days_threshold": "3",
            "budget_alert_threshold": "85",
            "last_email_sent": "2020-01-01",
            "emotional_message": "Faltan {days} días para celebrar los 70 años de mamá con toda la familia.",
        }
        for k, v in default_settings.items():
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))

        cats = [
            "Torta y Dulces", "Comida y Catering", "Bebidas y Barra", 
            "Decoración y Ambientación", "Música y Sonido", "Fotografía y Video", 
            "Salón y Espacio", "Invitaciones y Souvenirs", "Regalos Especiales", 
            "Logística y Organización"
        ]
        for c in cats:
            cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (c,))

        people = [
            ("Gastón", "gaston.dicampli@gmail.com", "", "PM"),
            ("Marina", "marina@gmail.com", "", "Participante"),
            ("Flavia", "flavia@gmail.com", "", "PM"),
            ("Dayana", "dayana@gmail.com", "", "Participante"),
            ("Leandro", "leandro@gmail.com", "", "Participante"),
            ("Sabina", "sabi@gmail.com", "", "Participante"),
            ("Uma", "uma@gmail.com", "", "Participante"),
        ]
        cursor.executemany("INSERT INTO people (name, email, phone, rol) VALUES (?, ?, ?, ?)", people)

        tasks = [
            ("Reservar salón principal", "Trámite / Reserva", "Salón y Espacio", "Gastón", "🔴 Crítica", "2026-09-10", "Completada", 100),
            ("Comprar vinos y espumantes", "Compra / Insumo", "Bebidas y Barra", "Flavia", "🔴 Crítica", "2026-09-12", "Pendiente", 0),
            ("Encargar torta temática", "Contratación / Proveedor", "Torta y Dulces", "Marina", "🟠 Alta", "2026-09-18", "En progreso", 40),
            ("Contratar fotógrafo", "Contratación / Proveedor", "Fotografía y Video", "Leandro", "🟡 Media", "2026-09-25", "Pendiente", 0),
        ]
        cursor.executemany("""INSERT INTO tasks (name, tipo, categoria, responsable, prioridad, limite, estado, avance) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", tasks)

        purchases = [
            ("Cajas de Vino Malbec x6", "Bebidas y Barra", 5, "Cajas", "Flavia", "2026-09-12", 80000, 76000, "Comprado", "Vinoteca"),
            ("Torta artesanal 3 pisos", "Torta y Dulces", 1, "Unidad", "Marina", "2026-10-15", 95000, 0, "Reservado", "Pastelería"),
        ]
        cursor.executemany("""INSERT INTO purchases (producto, categoria, cantidad, unidad, responsable, limite, estimado, real, estado, lugar) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", purchases)

        cursor.execute("INSERT INTO activity_log (message) VALUES (?)", ("Base de datos inicializada con el equipo oficial.",))

    conn.commit()
    conn.close()

init_db()

# ==========================================
# FUNCIONES AUXILIARES (DB y Fechas)
# ==========================================
def get_settings():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM settings", conn)
    conn.close()
    return dict(zip(df["key"], df["value"]))

def save_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

def get_people():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM people", conn)
    conn.close()
    return df.to_dict(orient="records")

def get_tasks():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM tasks", conn)
    conn.close()
    return df.to_dict(orient="records")

def get_purchases():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql("SELECT * FROM purchases", conn)
    conn.close()
    return df.to_dict(orient="records")

def get_activity_log():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT message FROM activity_log ORDER BY id DESC LIMIT 10")
    res = [row[0] for row in cursor.fetchall()]
    conn.close()
    return res

def log_activity(msg):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO activity_log (message) VALUES (?)", (msg,))
    conn.commit()
    conn.close()

settings = get_settings()
event_date = datetime.date.fromisoformat(settings["event_date"])
today = datetime.date.today()
delta_days = (event_date - today).days

def calcular_tiempo_restante(limite_str):
    try:
        limite = datetime.date.fromisoformat(str(limite_str)[:10])
        diff = (limite - today).days
        if diff < 0: return f"🔴 Vencida hace {abs(diff)} d"
        elif diff == 0: return "🟡 Vence hoy"
        elif diff <= 2: return f"🟠 Vence en {diff} d"
        else: return f"🟢 Faltan {diff} d"
    except: return "⚪ Sin fecha válida"

# ==========================================
# MOTOR DE CORREOS
# ==========================================
def enviar_correo(destinatario, asunto, cuerpo_html):
    try:
        if not hasattr(st, "secrets") or "smtp" not in st.secrets:
            return False, "No se configuraron las credenciales SMTP en los Secrets."
            
        smtp_server = st.secrets["smtp"]["server"]
        smtp_port = st.secrets["smtp"]["port"]
        smtp_user = st.secrets["smtp"]["user"]
        smtp_pass = st.secrets["smtp"]["password"]

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo_html, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True, ""
    except Exception as e:
        return False, str(e)

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
st.sidebar.markdown(f"# 🎂 {settings['event_name']}")
st.sidebar.markdown(f"**📅 Fecha:** {event_date.strftime('%d/%m/%Y')}")
st.sidebar.markdown(f"⏳ **Faltan {delta_days} días**")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Menú Principal",
    [
        "🏠 Dashboard General",
        "🚨 Centro de Control",
        "📋 Gestión de Tareas",
        "🛒 Control de Compras",
        "💰 Control de Presupuesto",
        "👥 Personas (ABM)",
        "📅 Calendario y Cronograma",
        "📊 Reportes y Ranking",
        "📧 Comunicaciones (Emails)",
        "⚙️ Configuración",
    ]
)

# ==========================================
# 1. DASHBOARD GENERAL
# ==========================================
if menu == "🏠 Dashboard General":
    msg = settings.get("emotional_message", "Faltan {days} días para celebrar los 70 de mamá.").format(days=delta_days)
    st.markdown(f"""
        <div class="emotional-banner">
            <h2 style="margin:0; font-family: serif;">❤️ {msg}</h2>
            <p style="margin:6px 0 0 0; font-size: 15px;">Centro de comando colaborativo del equipo.</p>
        </div>
    """, unsafe_allow_html=True)

    tasks = get_tasks()
    purchases = get_purchases()

    total_t = len(tasks)
    done_t = len([t for t in tasks if t["estado"] == "Completada"])
    pct_t = int((done_t / total_t) * 100) if total_t > 0 else 0

    atrasadas = [t for t in tasks if t["estado"] not in ["Completada", "Cancelada"] and "Vencida" in calcular_tiempo_restante(t["limite"])]

    total_p = len(purchases)
    done_p = len([p for p in purchases if p["estado"] == "Comprado"])
    spent = sum([p["real"] for p in purchases])
    total_b = float(settings["total_budget"])
    pct_b = int((spent / total_b) * 100) if total_b > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avance General", f"{pct_t}%", f"{done_t}/{total_t} completadas")
    c2.metric("Tareas Atrasadas", len(atrasadas), delta="Riesgo" if atrasadas else "Al día", delta_color="inverse" if atrasadas else "normal")
    c3.metric("Compras Realizadas", f"{done_p}/{total_p}", f"{int(done_p/total_p*100) if total_p else 0}%")
    c4.metric("Presupuesto Ejecutado", f"{settings['currency']}{spent:,.0f}", f"{pct_b}% consumido")

    st.markdown("---")
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.subheader("⚡ Tareas con Atención Requerida")
        alert_tasks = [t for t in tasks if t["estado"] not in ["Completada", "Cancelada"] and any(x in calcular_tiempo_restante(t["limite"]) for x in ["Vencida", "Vence hoy", "Vence en"])]
        if alert_tasks:
            for t in alert_tasks:
                estado_tiempo = calcular_tiempo_restante(t["limite"])
                st.markdown(f"""
                    <div style="background:white; border-left: 4px solid #ef4444; padding:10px 14px; border-radius:8px; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05)">
                        <b>{t['name']}</b> ({t['tipo']})<br>
                        <small>👤 {t['responsable']} | 📅 Límite: {t['limite']} | {estado_tiempo}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.success("🎉 ¡Excelente! No hay tareas atrasadas ni urgentes hoy.")

    with col_right:
        st.subheader("🛒 Resumen de Gastos por Categoría")
        if purchases:
            df_p = pd.DataFrame(purchases)
            fig_p = px.pie(df_p, names="categoria", values="real", hole=0.45, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_p.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=240)
            st.plotly_chart(fig_p, use_container_width=True)

# ==========================================
# 2. CENTRO DE CONTROL
# ==========================================
elif menu == "🚨 Centro de Control":
    st.subheader("🚨 Centro de Control y Gestión de Riesgos")
    tasks = get_tasks()
    overdue = [t for t in tasks if t["estado"] not in ["Completada", "Cancelada"] and "Vencida" in calcular_tiempo_restante(t["limite"])]
    near = [t for t in tasks if t["estado"] not in ["Completada", "Cancelada"] and any(x in calcular_tiempo_restante(t["limite"]) for x in ["Vence hoy", "Vence en"])]
    no_resp = [t for t in tasks if not t["responsable"] or t["responsable"] == "Sin asignar"]

    risk_score = min(100, (len(overdue) * 25) + (len(near) * 10) + (len(no_resp) * 15))

    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        st.markdown(f"### Índice de Riesgo: **{risk_score}/100**")
        if risk_score <= 25: st.success("🟢 PROYECTO SALUDABLE: Bajo control.")
        elif risk_score <= 60: st.warning("🟡 REQUIERE ATENCIÓN: Hay alertas abiertas.")
        else: st.error("🔴 ESTADO CRÍTICO: Múltiples tareas atrasadas.")

    with col_r2:
        st.write(f"• **{len(overdue)}** tareas actualmente vencidas.\n• **{len(near)}** tareas próximas a vencer.\n• **{len(no_resp)}** tareas sin responsable.")

# ==========================================
# 3. GESTIÓN DE TAREAS
# ==========================================
elif menu == "📋 Gestión de Tareas":
    st.subheader("📋 Gestión de Tareas")

    people_list = get_people()
    personas_disponibles = [p["name"] for p in people_list] + ["Sin asignar"]
    categorias_disponibles = get_categories()
    tipos_disponibles = ["Coordinación", "Compra / Insumo", "Contratación / Proveedor", "Trámite / Reserva", "Preparación"]
    estados_disponibles = ["Pendiente", "En progreso", "Bloqueada", "Completada", "Cancelada"]
    prioridades_disponibles = ["🔴 Crítica", "🟠 Alta", "🟡 Media", "🟢 Baja"]

    with st.expander("➕ Crear Nueva Tarea"):
        with st.form("form_nueva_tarea", clear_on_submit=True):
            f_nombre = st.text_input("Nombre de la Tarea *")
            c1, c2 = st.columns(2)
            f_tipo = c1.selectbox("Tipo de Tarea", tipos_disponibles)
            f_cat = c2.selectbox("Categoría", categorias_disponibles)
            c3, c4, c5 = st.columns(3)
            f_resp = c3.selectbox("Responsable", personas_disponibles)
            f_prio = c4.selectbox("Prioridad", prioridades_disponibles)
            f_limite = c5.date_input("Fecha Límite", value=datetime.date(2026, 9, 20))

            if st.form_submit_button("Guardar Tarea"):
                if f_nombre.strip():
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("""INSERT INTO tasks (name, tipo, categoria, responsable, prioridad, limite, estado, avance) 
                                      VALUES (?, ?, ?, ?, ?, ?, 'Pendiente', 0)""", 
                                   (f_nombre.strip(), f_tipo, f_cat, f_resp, f_prio, str(f_limite)))
                    conn.commit()
                    conn.close()
                    log_activity(f"Se creó la tarea '{f_nombre.strip()}'")
                    st.success("Tarea creada correctamente.")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio.")

    tasks = get_tasks()
    if tasks:
        df_tasks = pd.DataFrame(tasks)
        df_tasks["limite"] = pd.to_datetime(df_tasks["limite"]).dt.date
        df_tasks["tiempo_restante"] = df_tasks["limite"].apply(lambda x: calcular_tiempo_restante(str(x)))

        column_config = {
            "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "name": st.column_config.TextColumn("Nombre de la Tarea", required=True),
            "tipo": st.column_config.SelectboxColumn("Tipo", options=tipos_disponibles, required=True),
            "categoria": st.column_config.SelectboxColumn("Categoría", options=categorias_disponibles, required=True),
            "responsable": st.column_config.SelectboxColumn("Responsable", options=personas_disponibles, required=True),
            "prioridad": st.column_config.SelectboxColumn("Prioridad", options=prioridades_disponibles, required=True),
            "limite": st.column_config.DateColumn("Fecha Límite", required=True),
            "tiempo_restante": st.column_config.TextColumn("Tiempo Restante", disabled=True),
            "estado": st.column_config.SelectboxColumn("Estado", options=estados_disponibles, required=True),
            "avance": st.column_config.ProgressColumn("% Avance", min_value=0, max_value=100, format="%d%%"),
        }

        cols_order = ["id", "name", "tipo", "categoria", "responsable", "prioridad", "limite", "tiempo_restante", "estado", "avance"]
        edited_df = st.data_editor(df_tasks[cols_order], column_config=column_config, use_container_width=True, num_rows="dynamic", key="editor_tareas_db")

        if st.button("💾 Guardar Cambios en la Base de Datos"):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks")
            for _, row in edited_df.iterrows():
                cursor.execute("""INSERT INTO tasks (id, name, tipo, categoria, responsable, prioridad, limite, estado, avance) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                               (row["id"], row["name"], row["tipo"], row["categoria"], row["responsable"], row["prioridad"], str(row["limite"]), row["estado"], int(row["avance"]) if pd.notna(row["avance"]) else 0))
            conn.commit()
            conn.close()
            log_activity("Se actualizaron las tareas desde la tabla interactiva.")
            st.success("¡Base de datos SQLite actualizada con éxito!")
            st.rerun()

# ==========================================
# 4. CONTROL DE COMPRAS
# ==========================================
elif menu == "🛒 Control de Compras":
    st.subheader("🛒 Gestión de Compras y Proveedores")

    people_list = get_people()
    with st.expander("➕ Registrar Nueva Compra"):
        with st.form("form_nueva_compra_db", clear_on_submit=True):
            c1, c2 = st.columns(2)
            p_nombre = c1.text_input("Producto / Ítem *")
            p_cat = c2.selectbox("Categoría", get_categories())
            c3, c4, c5 = st.columns(3)
            p_cant = c3.number_input("Cantidad", min_value=1, value=1)
            p_unidad = c4.text_input("Unidad", value="Unidad")
            p_resp = c5.selectbox("Responsable", [p["name"] for p in people_list])
            c6, c7, c8 = st.columns(3)
            p_est = c6.number_input("Precio Estimado ($)", min_value=0, value=10000)
            p_real = c7.number_input("Precio Real ($)", min_value=0, value=0)
            p_estado = c8.selectbox("Estado", ["Pendiente", "Reservado", "Comprado", "Cancelado"])
            p_lugar = st.text_input("Lugar de Compra")

            if st.form_submit_button("Guardar Compra"):
                if p_nombre.strip():
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("""INSERT INTO purchases (producto, categoria, cantidad, unidad, responsable, limite, estimado, real, estado, lugar) 
                                      VALUES (?, ?, ?, ?, ?, '2026-10-10', ?, ?, ?, ?)""", 
                                   (p_nombre.strip(), p_cat, p_cant, p_unidad, p_resp, p_est, p_real, p_estado, p_lugar))
                    conn.commit()
                    conn.close()
                    st.success("Compra guardada.")
                    st.rerun()

    purchases = get_purchases()
    if purchases:
        df_p = pd.DataFrame(purchases)
        df_p["desvio"] = df_p.apply(lambda row: row["real"] - row["estimado"] if row["estado"] == "Comprado" else 0, axis=1)

        column_config_p = {
            "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "producto": st.column_config.TextColumn("Producto", required=True),
            "categoria": st.column_config.SelectboxColumn("Categoría", options=get_categories(), required=True),
            "estimado": st.column_config.NumberColumn("Estimado ($)", format="$%d"),
            "real": st.column_config.NumberColumn("Real ($)", format="$%d"),
            "desvio": st.column_config.NumberColumn("Diferencia ($)", disabled=True, format="$%d"),
            "estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "Reservado", "Comprado", "Cancelado"], required=True),
        }

        edited_p = st.data_editor(df_p, column_config=column_config_p, use_container_width=True, num_rows="dynamic", key="editor_compras_db")
        if st.button("💾 Guardar Cambios en Compras"):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM purchases")
            for _, row in edited_p.iterrows():
                cursor.execute("""INSERT INTO purchases (id, producto, categoria, cantidad, unidad, responsable, limite, estimado, real, estado, lugar) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                               (row["id"], row["producto"], row["categoria"], row["cantidad"], row["unidad"], row["responsable"], row.get("limite", "2026-10-10"), row["estimado"], row["real"], row["estado"], row.get("lugar", "")))
            conn.commit()
            conn.close()
            st.success("Compras guardadas en base de datos.")
            st.rerun()

# ==========================================
# 5. CONTROL DE PRESUPUESTO
# ==========================================
elif menu == "💰 Control de Presupuesto":
    st.subheader("💰 Control Financiero y Presupuestario")
    purchases = get_purchases()
    tot_b = float(settings["total_budget"])
    tot_real = sum([p["real"] for p in purchases])
    tot_est = sum([p["estimado"] for p in purchases])
    saldo = tot_b - tot_real

    k1, k2, k3, k4 = st.columns(4)
    curr = settings["currency"]
    k1.metric("Presupuesto Total", f"{curr}{tot_b:,.0f}")
    k2.metric("Total Estimado", f"{curr}{tot_est:,.0f}")
    k3.metric("Total Gastado Real", f"{curr}{tot_real:,.0f}")
    k4.metric("Saldo Remanente", f"{curr}{saldo:,.0f}")

    pct_usado = min(1.0, tot_real / tot_b) if tot_b > 0 else 0
    st.progress(pct_usado, text=f"Porcentaje de presupuesto consumido: {int(pct_usado*100)}%")

# ==========================================
# 6. PERSONAS (ABM)
# ==========================================
elif menu == "👥 Personas (ABM)":
    st.subheader("👥 Equipo de Organización (ABM)")
    tab_list, tab_add, tab_edit = st.tabs(["📋 Directorio", "➕ Nueva Persona", "✏️ Editar / Eliminar"])

    with tab_list:
        people = get_people()
        tasks = get_tasks()
        for p in people:
            p_tasks = [t for t in tasks if t["responsable"] == p["name"]]
            completadas = len([t for t in p_tasks if t["estado"] == "Completada"])
            st.markdown(f"""
                <div style="background:white; padding:16px; border-radius:10px; border:1px solid #e5e7eb; margin-bottom:10px;">
                    <h4 style="margin:0;">👤 {p['name']} <span style="font-size:13px; color:#6b7280;">({p['rol']})</span></h4>
                    <p style="margin:4px 0;">📧 {p['email']} | 📱 {p.get('phone','-')}</p>
                    <span class="badge-info">Tareas asignadas: {len(p_tasks)}</span> &nbsp;
                    <span class="badge-ok">Completadas: {completadas}</span>
                </div>
            """, unsafe_allow_html=True)

    with tab_add:
        with st.form("form_alta_p", clear_on_submit=True):
            n_nom = st.text_input("Nombre y Apellido *")
            n_email = st.text_input("Email")
            n_tel = st.text_input("Teléfono")
            n_rol = st.selectbox("Rol en la Organización", ["PM", "Participante", "Colaborador Externo"])
            if st.form_submit_button("Guardar Persona"):
                if n_nom.strip():
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO people (name, email, phone, rol) VALUES (?, ?, ?, ?)", (n_nom.strip(), n_email, n_tel, n_rol))
                    conn.commit()
                    conn.close()
                    st.success("Persona agregada.")
                    st.rerun()

    with tab_edit:
        people = get_people()
        if people:
            sel_p = st.selectbox("Seleccionar persona", [p["name"] for p in people])
            p_obj = next((p for p in people if p["name"] == sel_p), None)
            if p_obj:
                with st.form("form_edit_p"):
                    e_nom = st.text_input("Nombre", value=p_obj["name"])
                    e_email = st.text_input("Email", value=p_obj["email"])
                    e_tel = st.text_input("Teléfono", value=p_obj.get("phone", ""))
                    e_rol = st.selectbox("Rol", ["PM", "Participante", "Colaborador Externo"], index=0 if p_obj.get("rol") == "PM" else 1)
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Actualizar"):
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE people SET name=?, email=?, phone=?, rol=? WHERE id=?", (e_nom, e_email, e_tel, e_rol, p_obj["id"]))
                        conn.commit()
                        conn.close()
                        st.success("Actualizado.")
                        st.rerun()
                    if c2.form_submit_button("🗑️ Eliminar"):
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM people WHERE id=?", (p_obj["id"],))
                        conn.commit()
                        conn.close()
                        st.warning("Eliminado.")
                        st.rerun()

# ==========================================
# 7. CALENDARIO Y CRONOGRAMA
# ==========================================
elif menu == "📅 Calendario y Cronograma":
    st.subheader("📅 Cronograma de Tareas")
    tasks = get_tasks()
    tasks_with_dates = []
    for t in tasks:
        try:
            lim = datetime.date.fromisoformat(str(t["limite"])[:10])
            tasks_with_dates.append(dict(Tarea=t["name"], Inicio=str(lim - datetime.timedelta(days=3)), Fin=str(lim), Categoria=t["categoria"]))
        except: pass

    if tasks_with_dates:
        df_timeline = pd.DataFrame(tasks_with_dates)
        fig_g = px.timeline(df_timeline, x_start="Inicio", x_end="Fin", y="Tarea", color="Categoria")
        fig_g.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_g, use_container_width=True)

# ==========================================
# 8. REPORTES Y RANKING
# ==========================================
elif menu == "📊 Reportes y Ranking":
    st.subheader("📊 Reportes Analíticos y Ranking de Productividad")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        df_t = pd.DataFrame(get_tasks())
        if not df_t.empty:
            fig_s = px.pie(df_t, names="estado", title="Distribución de Tareas por Estado")
            st.plotly_chart(fig_s, use_container_width=True)

    with col_r2:
        st.markdown("#### 🏆 Ranking de Productividad del Equipo")
        people = get_people()
        ranking_data = []
        for p in people:
            p_tasks = [t for t in get_tasks() if t["responsable"] == p["name"]]
            completadas = len([t for t in p_tasks if t["estado"] == "Completada"])
            total_asignadas = len(p_tasks)
            ranking_data.append({"Usuario": p["name"], "Rol": p["rol"], "Completadas": completadas, "Asignadas": total_asignadas})
        
        df_rank = pd.DataFrame(ranking_data)
        if not df_rank.empty:
            df_rank = df_rank.sort_values(by=["Completadas", "Asignadas"], ascending=False)
            st.dataframe(df_rank, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📝 Historial de Actividad Reciente")
    for l in get_activity_log(): st.markdown(f"• {l}")

# ==========================================
# 9. COMUNICACIONES (EMAILS)
# ==========================================
elif menu == "📧 Comunicaciones (Emails)":
    st.subheader("📧 Centro de Comunicaciones")
    st.write("Envío de resúmenes ejecutivos para PMs y recordatorios de tareas para los participantes.")
    
    try:
        last_sent = datetime.date.fromisoformat(settings.get("last_email_sent", "2020-01-01"))
        dias_desde_envio = (today - last_sent).days
    except:
        dias_desde_envio = 999
        
    if dias_desde_envio >= int(settings.get("alert_days_threshold", 3)):
        st.error(f"🚨 **¡Atención!** Han pasado {dias_desde_envio} días desde el último envío. Es momento de recordar al equipo.")
    else:
        st.success(f"🟢 Los correos están al día. Último envío hace {dias_desde_envio} días.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📨 Correos a Participantes")
        st.caption("Envía a cada miembro un correo con sus tareas pendientes y tiempos restantes.")
        if st.button("Enviar Recordatorios a Participantes"):
            with st.spinner("Enviando correos..."):
                people = get_people()
                tasks = get_tasks()
                errores, enviados = 0, 0
                
                for p in people:
                    user_tasks = [t for t in tasks if t["responsable"] == p["name"] and t["estado"] not in ["Completada", "Cancelada"]]
                    if user_tasks and p["email"]:
                        html_tasks = "".join([f"<li><b>{t['name']}</b> (Límite: {t['limite']} - {calcular_tiempo_restante(t['limite'])})</li>" for t in user_tasks])
                        cuerpo = f"""
                        <html><body style="font-family: Arial; color: #333;">
                            <h2 style="color: #800f2f;">¡Hola {p['name']}! 🎂</h2>
                            <p>Faltan <b>{delta_days} días</b> para el evento. Aquí tienes tus tareas pendientes:</p>
                            <ul>{html_tasks}</ul>
                        </body></html>"""
                        ok, error_msg = enviar_correo(p["email"], "Recordatorio de Tareas - Cumpleaños Mamá", cuerpo)
                        if ok: enviados += 1
                        else: errores += 1
                
                if errores == 0 and enviados > 0:
                    st.success(f"✅ Se enviaron {enviados} recordatorios.")
                    save_setting("last_email_sent", str(today))
                else: st.warning(f"Se enviaron {enviados} correos, pero fallaron {errores}. Revisa la configuración SMTP.")

    with col2:
        st.markdown("### 📊 Reporte Ejecutivo (PMs)")
        st.caption("Envía a Gastón y Flavia un resumen gerencial del proyecto.")
        if st.button("Enviar Reporte a PMs"):
            with st.spinner("Generando reporte..."):
                people = get_people()
                tasks = get_tasks()
                purchases = get_purchases()
                pms = [p for p in people if p["rol"] == "PM" and p["email"]]
                
                atrasadas = len([t for t in tasks if t["estado"] not in ["Completada", "Cancelada"] and "Vencida" in calcular_tiempo_restante(t["limite"])])
                gastado = sum([p["real"] for p in purchases])
                completadas = len([t for t in tasks if t["estado"] == "Completada"])
                
                cuerpo_pm = f"""
                <html><body style="font-family: Arial; color: #333;">
                    <h2 style="color: #0369a1;">Reporte Ejecutivo: {settings['event_name']}</h2>
                    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 300px;">
                        <tr><td><b>Tareas Completadas</b></td><td>{completadas}/{len(tasks)}</td></tr>
                        <tr><td><b>Tareas Atrasadas</b></td><td style="color:red;"><b>{atrasadas}</b></td></tr>
                        <tr><td><b>Gastado</b></td><td>{settings['currency']}{gastado:,.0f}</td></tr>
                    </table>
                </body></html>"""
                
                errores, enviados = 0, 0
                for pm in pms:
                    ok, error = enviar_correo(pm["email"], f"Reporte de Estado - {settings['event_name']}", cuerpo_pm)
                    if ok: enviados += 1
                    else: errores += 1
                
                if errores == 0 and enviados > 0: st.success(f"✅ Se enviaron {enviados} reportes a PMs.")
                else: st.warning("Hubo errores de conexión SMTP. Revisa los Secrets.")

# ==========================================
# 10. CONFIGURACIÓN PERSONALIZABLE
# ==========================================
elif menu == "⚙️ Configuración":
    st.subheader("⚙️ Configuración General y Textos Personalizables")
    st.info("Para que los correos funcionen, recuerda crear el archivo `.streamlit/secrets.toml` localmente o en Streamlit Cloud.")
    
    with st.form("form_settings_db"):
        s_name = st.text_input("Nombre del Evento", value=settings["event_name"])
        s_date = st.date_input("Fecha", value=event_date)
        s_budget = st.number_input("Presupuesto Total", value=int(float(settings["total_budget"])))
        s_msg = st.text_area("Mensaje Emocional Personalizado (usa {days} para días restantes)", value=settings.get("emotional_message", ""))

        if st.form_submit_button("Guardar Cambios y Textos"):
            save_setting("event_name", s_name)
            save_setting("event_date", str(s_date))
            save_setting("total_budget", s_budget)
            save_setting("emotional_message", s_msg)
            st.success("Configuración y textos personalizados guardados con éxito.")
            st.rerun()

    st.markdown("---")
    st.subheader("🏷️ Administración de Categorías")
    cat_col1, cat_col2 = st.columns([2, 1])

    with cat_col1:
        nueva_cat = st.text_input("Nueva Categoría")
        if st.button("➕ Agregar Categoría"):
            cats = get_categories()
            if nueva_cat.strip() and nueva_cat.strip() not in cats:
                conn = sqlite3.connect(DB_FILE)
                conn.cursor().execute("INSERT INTO categories (name) VALUES (?)", (nueva_cat.strip(),))
                conn.commit()
                conn.close()
                st.success(f"Categoría '{nueva_cat}' agregada.")
                st.rerun()

    with cat_col2:
        cat_a_borrar = st.selectbox("Eliminar Categoría", get_categories())
        if st.button("🗑️ Eliminar"):
            conn = sqlite3.connect(DB_FILE)
            conn.cursor().execute("DELETE FROM categories WHERE name=?", (cat_a_borrar,))
            conn.commit()
            conn.close()
            st.warning(f"Categoría eliminada.")
            st.rerun()