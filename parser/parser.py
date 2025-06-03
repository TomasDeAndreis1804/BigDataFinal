import boto3
import os
import csv
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse
import json
import io

s3 = boto3.client('s3')

def app(event, context):
    print("==== Evento recibido por Lambda ====")
    print(json.dumps(event, indent=2))

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])

        if not key.startswith('headlines/raw/') or not key.endswith('.html'):
            print(f"Ignorando archivo no válido para procesamiento: {key}")
            continue

        print(f"Procesando archivo S3: bucket={bucket}, key={key}")

        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            print(f"Archivo HTML extraído correctamente: {key}")
        except Exception as e:
            print(f"Error al leer el archivo desde S3: {str(e)}")
            continue

        soup = BeautifulSoup(content, 'html.parser')
        nombre_archivo = os.path.basename(key)

        # ✅ Detectar el periódico por el nombre del archivo
        if 'publimetro' in nombre_archivo:
            periodico = 'publimetro'
        elif 'eltiempo' in nombre_archivo:
            periodico = 'eltiempo'
        else:
            periodico = 'desconocido'

        noticias = []

        for article in soup.find_all('article'):
            titular_tag = article.find(['h2', 'h3'])
            enlace_tag = article.find('a', href=True)

            if titular_tag and enlace_tag:
                titular = titular_tag.get_text(strip=True)
                enlace = enlace_tag['href']
                if not enlace.startswith('http'):
                    if periodico == 'publimetro':
                        enlace = f'https://www.publimetro.co{enlace}'
                    elif periodico == 'eltiempo':
                        enlace = f'https://www.eltiempo.com{enlace}'

                categoria = ''
                parts = enlace.split('/')
                if len(parts) > 3:
                    categoria = parts[3]

                noticias.append({
                    'categoria': categoria,
                    'titular': titular,
                    'enlace': enlace
                })

        if not noticias:
            print("No se encontraron artículos válidos en <article>. Se intenta fallback...")
            for heading in soup.find_all(['h2', 'h3']):
                a_tag = heading.find('a', href=True)
                if a_tag:
                    titular = heading.get_text(strip=True)
                    enlace = a_tag['href']
                    if not enlace.startswith('http'):
                        if periodico == 'publimetro':
                            enlace = f'https://www.publimetro.co{enlace}'
                        elif periodico == 'eltiempo':
                            enlace = f'https://www.eltiempo.com{enlace}'

                    categoria = ''
                    parts = enlace.split('/')
                    if len(parts) > 3:
                        categoria = parts[3]

                    noticias.append({
                        'categoria': categoria,
                        'titular': titular,
                        'enlace': enlace
                    })

        print(f"Total de noticias extraídas: {len(noticias)} del periódico {periodico}")

        fecha = datetime.utcnow()
        year = fecha.strftime('%Y')
        month = fecha.strftime('%m')
        day = fecha.strftime('%d')
        hour = fecha.strftime('%H')
        minute = fecha.strftime('%M')

        # ✅ Archivo separado por periódico y minuto
        csv_key = f"headlines/final/periodico={periodico}/year={year}/month={month}/day={day}/noticias_{hour}-{minute}.csv"
        print(f"Guardando CSV en: {csv_key}")

        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=['categoria', 'titular', 'enlace'])
        writer.writeheader()
        for noticia in noticias:
            writer.writerow(noticia)

        try:
            s3.put_object(Bucket=bucket, Key=csv_key, Body=csv_buffer.getvalue())
            print("Archivo CSV subido exitosamente a S3.")
        except Exception as e:
            print(f"Error al subir el CSV a S3: {str(e)}")

    return {
        "statusCode": 200,
        "body": f"Procesamiento completado para {periodico}."
    }
