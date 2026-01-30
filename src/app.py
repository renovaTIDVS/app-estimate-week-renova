
import streamlit as st
import pytz



import google_sheets
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import streamlit as st


st.set_page_config(page_title="Dashboard Google Sheets", layout="wide")




st.title("Ingresos Estimados")

# Obtener los datos de todas las hojas
data_dict = google_sheets.get_selected_sheets_data()

if not data_dict:
	st.warning("No se encontraron ingresos estimados en las hojas.")
	st.stop()

# Unir todos los DataFrames en uno solo y agregar columna de sucursal
df_list = []
for sucursal, df in data_dict.items():
	df = df.copy()
	df['sucursal'] = sucursal
	df_list.append(df)
df_all = pd.concat(df_list, ignore_index=True)

# Normalizar nombres de columnas
df_all.columns = [c.lower().strip() for c in df_all.columns]

# Buscar columna de fecha
fecha_col = [c for c in df_all.columns if 'fecha' in c][0]
tipo_col = 'tipo' if 'tipo' in df_all.columns else None
venta_col = 'pago_total_estimado' if 'pago_total_estimado' in df_all.columns else None



tz = pytz.timezone("America/Mazatlan")
# Día actual y los próximos 7 días (8 días en total)
now_tz = datetime.now(tz)
today = now_tz.date()
start_date = today
end_date = today + timedelta(days=7)
# Convertir columna de fecha a datetime y luego a zona horaria
df_all[fecha_col] = pd.to_datetime(df_all[fecha_col], errors='coerce')
df_all[fecha_col] = df_all[fecha_col].dt.tz_localize(tz, ambiguous='NaT', nonexistent='NaT').dt.date
df_7d = df_all[(df_all[fecha_col] >= start_date) & (df_all[fecha_col] <= end_date)]

if df_7d.empty:
	st.warning("No hay estimaciones para los próximos 7 días.")
	st.dataframe(df_all)
	st.stop()
# Selects y tabla de detalle en columnas (tipo debajo de sucursal y filtro de fecha)
st.subheader("Detalle")
col1, col2 = st.columns([1, 4])

with col1:
	sucursales = ['Todas'] + sorted(df_7d['sucursal'].unique())
	sucursal_sel = st.selectbox("Sucursal", sucursales, key="sucursal_select")
	tipos = ['Todos']
	if tipo_col:
		tipos += sorted(df_7d[tipo_col].dropna().unique())
	tipo_sel = st.selectbox("Tipo", tipos, key="tipo_select")
	# Filtro de fecha (solo próximos 7 días) como calendario
	fechas_7d = pd.date_range(start=start_date, end=end_date)
	fechas_validas = [f.date() for f in fechas_7d]
	fecha_sel = st.date_input(
		"Filtrar por fecha",
		value=None,
		min_value=fechas_validas[0],
		max_value=fechas_validas[-1],
		key="fecha_select"
	)
	# Si el usuario no selecciona fecha, mostrar todos
	if isinstance(fecha_sel, list) or fecha_sel is None:
		fecha_sel = None
	# Permitir deseleccionar la fecha (opcional)
	if 'fecha_clear' not in st.session_state:
		st.session_state['fecha_clear'] = False
	if st.session_state['fecha_clear']:
		fecha_sel = None
with col2:
	# Aplicar filtros
	df_filt = df_7d.copy()
	if sucursal_sel != 'Todas':
		df_filt = df_filt[df_filt['sucursal'] == sucursal_sel]
	if tipo_col and tipo_sel != 'Todos':
		df_filt = df_filt[df_filt[tipo_col] == tipo_sel]
	# Filtrar por fecha si se selecciona
	if fecha_sel:
		df_filt = df_filt[df_filt[fecha_col] == fecha_sel]
	st.dataframe(df_filt)



if venta_col:
	# Asegurar que la columna de ventas es numérica
	df_7d[venta_col] = pd.to_numeric(df_7d[venta_col], errors='coerce')
	df_filt[venta_col] = pd.to_numeric(df_filt[venta_col], errors='coerce')

	fechas_7d = pd.date_range(start=start_date, end=end_date)
	fechas_index = fechas_7d.date
	fechas_labels = [f.strftime('%d-%b') for f in fechas_7d]

	# --- Gráfico 1: Ventas por sucursal y día (filtrado) ---
	df_sucursal = df_filt[[fecha_col, 'sucursal', venta_col]].copy()
	df_sucursal[fecha_col] = pd.to_datetime(df_sucursal[fecha_col])
	df_sucursal['fecha_str'] = df_sucursal[fecha_col].dt.strftime('%d-%b')
	# Asegurar que se muestran los 7 días aunque no haya datos para todos
	sucursales_unicas = df_sucursal['sucursal'].unique()
	fechas_unicas = fechas_labels
	import itertools
	idx = pd.MultiIndex.from_product([sucursales_unicas, fechas_unicas], names=['sucursal', 'fecha_str'])
	df_sucursal_grouped = df_sucursal.groupby(['sucursal', 'fecha_str'])[venta_col].sum().reindex(idx, fill_value=0).reset_index()
	# Si hay filtro de fecha, mostrar solo esa fecha en el gráfico
	if fecha_sel:
		fecha_str = fecha_sel.strftime('%d-%b')
		df_sucursal_grouped = df_sucursal_grouped[df_sucursal_grouped['fecha_str'] == fecha_str]
		chart1 = alt.Chart(df_sucursal_grouped).mark_bar().encode(
			x=alt.X('sucursal:N', title='Sucursal'),
			y=alt.Y(f'{venta_col}:Q', title='Ventas estimadas'),
			color=alt.Color('sucursal:N', title='Sucursal'),
			tooltip=['sucursal', f'{venta_col}:Q']
		).properties(
			width=700, height=400, title=f'Ventas estimadas por sucursal ({fecha_str})'
		)
	else:
		chart1 = alt.Chart(df_sucursal_grouped).mark_bar().encode(
			x=alt.X('fecha_str:O', title='Fecha', sort=fechas_labels, axis=alt.Axis(labelAngle=0)),
			y=alt.Y(f'{venta_col}:Q', title='Ventas estimadas'),
			color=alt.Color('sucursal:N', title='Sucursal'),
			tooltip=['sucursal', 'fecha_str', f'{venta_col}:Q']
		).properties(
			width=700, height=400, title='Ventas estimadas por sucursal'
		)
	st.altair_chart(chart1, use_container_width=True)

	# --- Gráfico 2: Ventas por tipo y día (si existe columna tipo) ---

	if tipo_col:
		df_tipo = df_filt[[fecha_col, tipo_col, venta_col]].copy()
		df_tipo[fecha_col] = pd.to_datetime(df_tipo[fecha_col])
		df_tipo['fecha_str'] = df_tipo[fecha_col].dt.strftime('%d-%b')
		tipos_unicos = df_tipo[tipo_col].unique()
		fechas_unicas = fechas_labels
		import itertools
		idx = pd.MultiIndex.from_product([tipos_unicos, fechas_unicas], names=[tipo_col, 'fecha_str'])
		df_tipo_grouped = df_tipo.groupby([tipo_col, 'fecha_str'])[venta_col].sum().reindex(idx, fill_value=0).reset_index()
		# Si hay filtro de fecha, mostrar solo esa fecha en el gráfico
		if fecha_sel:
			fecha_str = fecha_sel.strftime('%d-%b')
			df_tipo_grouped = df_tipo_grouped[df_tipo_grouped['fecha_str'] == fecha_str]
			chart2 = alt.Chart(df_tipo_grouped).mark_bar().encode(
				x=alt.X(f'{tipo_col}:N', title='Tipo'),
				y=alt.Y(f'{venta_col}:Q', title='Ventas estimadas'),
				color=alt.Color(f'{tipo_col}:N', title='Tipo'),
				tooltip=[f'{tipo_col}', f'{venta_col}:Q']
			).properties(
				width=700, height=400, title=f'Ventas estimadas por tipo ({fecha_str})'
			)
		else:
			chart2 = alt.Chart(df_tipo_grouped).mark_bar().encode(
				x=alt.X('fecha_str:O', title='Fecha', sort=fechas_labels, axis=alt.Axis(labelAngle=0)),
				y=alt.Y(f'{venta_col}:Q', title='Ventas estimadas'),
				color=alt.Color(f'{tipo_col}:N', title='Tipo'),
				tooltip=[f'{tipo_col}', 'fecha_str', f'{venta_col}:Q']
			).properties(
				width=700, height=400, title='Ventas estimadas por tipo (dental/optica)'
			)
		st.altair_chart(chart2, use_container_width=True)

	# --- Gráfico 3: Ventas totales por día --- (eliminado)
else:
	st.warning("No se encontró la columna de ventas estimadas ('pago_total_estimado').")
