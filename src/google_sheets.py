

import pandas as pd
import streamlit as st
import json
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_selected_sheets_data(sheet_id=None, sheet_names=None):
	"""
	Extrae los datos de las hojas especificadas del Google Sheet, columnas A-J, y filtra filas donde A no esté vacío.
	Devuelve un diccionario {nombre_hoja: DataFrame}
	"""
	if sheet_names is None:
		sheet_names = ['Mazatlan', 'Ensenada', 'San quintin']
	SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
	if sheet_id is None:
		sheet_id = '1LzdnA6unlUqqEhE_sLGUyHpdzrrU7LmEmhV65fIjJ1g'
	# Usar credenciales desde st.secrets
	google_creds = dict(st.secrets["google"])
	# Guardar como archivo temporal JSON
	with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmp:
		json.dump(google_creds, tmp)
		tmp.flush()
		creds = service_account.Credentials.from_service_account_file(tmp.name, scopes=SCOPES)
	service = build('sheets', 'v4', credentials=creds)
	data_dict = {}
	for title in sheet_names:
		try:
			range_name = f"{title}!A:J"
			result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
			values = result.get('values', [])
			if not values or len(values) < 2:
				print(f"[INFO] Hoja '{title}' vacía o sin datos.")
				continue
			df = pd.DataFrame(values[1:], columns=values[0])
			# Filtrar filas donde la columna A no esté vacía SOLO si la columna existe y es string
			if df.shape[0] > 0 and len(df.columns) > 0:
				col0 = df.columns[0]
				if col0 in df.columns:
					serie = df[col0]
					if hasattr(serie, 'str'):
						df = df[serie.astype(str).str.strip() != '']
					else:
						df = df[serie != '']
			if df.shape[0] > 0 and len(df.columns) > 0:
				# Convertir fechas a datetime y pago_total_estimado a decimal
				import decimal
				from datetime import datetime
				for col in df.columns:
					if 'fecha' in col:
						def try_parse_fecha(val):
							if pd.isna(val) or val == '':
								return pd.NaT
							for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"):
								try:
									return datetime.strptime(val, fmt)
								except Exception:
									continue
							try:
								return pd.to_datetime(val, errors='coerce', dayfirst=True)
							except Exception:
								return pd.NaT
						df[col] = df[col].apply(try_parse_fecha)
					if col == 'pago_total_estimado':
						def to_decimal(val):
							import re
							if pd.isna(val):
								return decimal.Decimal('0.00')
							val = str(val).replace('$','').replace(',','').strip()
							val = re.sub(r'[^0-9.]', '', val)
							try:
								return decimal.Decimal(val)
							except Exception:
								return decimal.Decimal('0.00')
						df[col] = df[col].apply(to_decimal)
				data_dict[title] = df
			else:
				print(f"[INFO] Hoja '{title}' sin filas válidas tras filtrar vacíos.")
		except Exception as e:
			print(f"[ERROR] Hoja '{title}': {e}")
	return data_dict
